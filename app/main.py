import os
import base64
import subprocess
import urllib.request
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components


APP_NAME = "ZimaBrain CE"
APP_SUBTITLE = "Local Zima Knowledge Assistant"
APP_DESCRIPTOR = "Verifier-first diagnostic tool for ZimaOS"
APP_VERSION = "v1.0.6-public-beta"
ANALYZER_VERSION = "analyzer-2026.06.05-v1"
RULESET_VERSION = "ruleset-2026.06.06-v11"

BASE_DIR = "/data"
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


SAFE_COMMANDS = {
    "System Layer": [
        "hostname",
        "cat /etc/os-release",
        "uname -a",
        "uptime",
        "free -h",
        "df -h /DATA || df -h",
    ],
    "Storage / Mount Layer": [
        "lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS",
        "findmnt -rn -o TARGET,SOURCE,FSTYPE,OPTIONS | grep -v '/docker/overlay2' | grep -v '/merged'",
        "find /media -maxdepth 2 -mindepth 1 -type d 2>/dev/null | sort || true",
    ],
    "Focused Storage/App Bind Check": [
        """echo '--- ACTIVE /media MOUNTS ---'
findmnt -rn -o TARGET,SOURCE,FSTYPE | grep '^/media' || true

echo
echo '--- VISIBLE /media FOLDERS ---'
find /media -maxdepth 2 -mindepth 1 -type d 2>/dev/null | sort || true

echo
echo '--- DOCKER CONTAINER MOUNTS USING /media OR /DATA ---'
for c in $(docker ps -a --format '{{.Names}}' 2>/dev/null); do
  echo
  echo "### CONTAINER: $c"
  docker inspect "$c" --format '{{range .Mounts}}{{println .Type "|" .Source "|" .Destination "|" .RW}}{{end}}' 2>/dev/null | grep -E '/media|/DATA|/var/lib/casaos_data|/mnt' || echo 'no /media or /DATA bind mounts found'
done

echo
echo '--- DOCKER CONTAINER PORTS / STATUS ---'
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
""",
    ],
    "Docker / App Layer": [
        "docker ps -a --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'",
        "docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}'",
        "docker volume ls",
        "docker network ls",
        "docker system df",
    ],
    "AI / GPU Layer": [
        "docker ps -a --format 'table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}' | grep -i -E 'ollama|open-webui|pdf-ai|zima-rag|brain' || true",
        "nvidia-smi || true",
        "docker info 2>/dev/null | grep -i -E 'runtimes|nvidia' || true",
    ],
    "Native sysext Layer": [
        "systemd-sysext status || true",
        "systemctl --failed || true",
        "systemctl list-timers --all || true",
    ],
    "Network / Exposure Layer": [
        "ip -br addr",
        "ip route",
        "ss -tulpn | head -n 160",
        "iptables -S INPUT 2>/dev/null || true",
        "iptables -S DOCKER-USER 2>/dev/null || true",
    ],
    "ZVM / Virtualisation Layer": [
        "virsh list --all 2>/dev/null || true",
        "ip -br addr | grep -E 'virbr|vnet|tap|br-' || true",
    ],
}


def run_host_command(command: str) -> str:
    nsenter_cmd = [
        "nsenter",
        "-t",
        "1",
        "-m",
        "-u",
        "-i",
        "-n",
        "-p",
        "--",
        "sh",
        "-lc",
        command,
    ]

    try:
        result = subprocess.run(
            nsenter_cmd,
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()

        if output and error:
            return output + "\n\n[stderr]\n" + error
        if error:
            return "[stderr]\n" + error
        return output
    except Exception as exc:
        return f"ERROR running host command: {exc}"


def quick_status(command: str) -> str:
    output = run_host_command(command)
    return output.strip() if output.strip() else "No output"



DASHBOARD_REPORT_URL = "http://host.docker.internal:8514/zimabrain-report"

def load_dashboard_layer():
    try:
        req = urllib.request.Request(
            DASHBOARD_REPORT_URL,
            headers={"User-Agent": "ZimaBrain-CE-Dashboard-Layer"},
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            text = response.read().decode("utf-8", errors="replace")
        return text.strip(), ""
    except Exception as e:
        return "", f"Dashboard layer unavailable: {e}"

def collect_report() -> tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = os.path.join(REPORTS_DIR, f"zimabrain-ce-report-{timestamp}.txt")

    lines = []
    lines.append("===== ZIMABRAIN CE VERIFIED REPORT =====")
    lines.append(str(datetime.now()))
    lines.append("")
    lines.append(f"App Version: {APP_VERSION}")
    lines.append(f"Analyzer Version: {ANALYZER_VERSION}")
    lines.append(f"Ruleset Version: {RULESET_VERSION}")
    lines.append("Report source: Local ZimaOS device")
    lines.append("Mode: read-only analyzer")
    lines.append("Method: analyze first > verify second > explain third > repair last")
    lines.append("")

    for section, commands in SAFE_COMMANDS.items():
        lines.append(f"===== {section.upper()} =====")
        for command in commands:
            lines.append("")
            lines.append(f"$ {command}")
            lines.append(run_host_command(command))
            lines.append("")
        lines.append("")

    report_text = "\n".join(lines)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_path, report_text


def parse_active_media_mounts(report_text: str):
    mounts = []
    in_mounts = False

    for raw in report_text.splitlines():
        line = raw.strip()

        if line == "--- ACTIVE /media MOUNTS ---":
            in_mounts = True
            continue

        if line.startswith("--- ") and "ACTIVE /media MOUNTS" not in line:
            in_mounts = False

        if not in_mounts:
            continue

        if not line.startswith("/media"):
            continue

        parts = line.split()
        if len(parts) >= 3:
            mounts.append({"target": parts[0], "source": parts[1], "fstype": parts[2]})

    return mounts


def parse_block_devices(report_text: str):
    devices = []
    capture = False

    for raw in report_text.splitlines():
        line = raw.rstrip()

        if "$ lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS" in line:
            capture = True
            continue

        if capture and line.startswith("$ "):
            break

        if not capture:
            continue

        stripped = line.strip()
        if not stripped or stripped.startswith("NAME "):
            continue

        clean = stripped.replace("├─", "").replace("└─", "").strip()
        roots = ("sda", "sdb", "sdc", "sdd", "sde", "sdf", "sdg", "nvme", "mmcblk")

        if clean.startswith(roots):
            parts = clean.split()
            name = parts[0] if len(parts) > 0 else ""
            size = parts[1] if len(parts) > 1 else ""
            fstype = "unknown"
            mount_hint = "detected, mount path not identified in this parsed line"

            for fs in ["btrfs", "ext4", "ntfs", "iso9660", "vfat", "squashfs", "xfs"]:
                if f" {fs} " in f" {clean} ":
                    fstype = fs
                    break

            if "/media/" in clean:
                mount_hint = clean[clean.find("/media/"):]
            elif "/DATA" in clean:
                mount_hint = clean[clean.find("/DATA"):]

            devices.append(
                {
                    "name": name,
                    "size": size,
                    "fstype": fstype,
                    "mount": mount_hint,
                }
            )

    return devices


def parse_container_storage_mounts(report_text: str):
    rows = []
    current_container = None

    for raw in report_text.splitlines():
        line = raw.strip()

        if line.startswith("### CONTAINER:"):
            current_container = line.replace("### CONTAINER:", "").strip()
            continue

        if not current_container or "|" not in line:
            continue

        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 4:
            continue

        mount_type = parts[0]
        source = parts[1]
        destination = parts[2]
        rw = parts[3]

        watched = ["/media", "/DATA", "/var/lib/casaos_data", "/mnt"]
        if not any(source.startswith(x) for x in watched):
            continue

        risk = "check"

        if "/docker/volumes/" in source:
            risk = "Docker internal volume path, do not manually edit"
        elif source.startswith("/media/"):
            risk = "media bind, verify active mount"
        elif source.startswith("/DATA/.media/"):
            risk = "ZimaOS media mirror, verify matching /media mount"
        elif source.startswith("/var/lib/casaos_data/.media/"):
            risk = "CasaOS/ZimaOS media mirror, verify matching /media mount"
        elif source.startswith("/DATA/AppData/"):
            risk = "normal persistent app config"
        elif source.startswith("/DATA/"):
            risk = "DATA bind, generally persistent"
        elif source.startswith("/mnt/"):
            risk = "mnt bind, verify source"

        rows.append(
            {
                "container": current_container,
                "type": mount_type,
                "source": source,
                "destination": destination,
                "rw": rw,
                "risk": risk,
            }
        )

    return rows


def make_block_device_table(devices):
    if not devices:
        return [
            "No block-device table was parsed from the report.",
            "Run the safe analyzer again so the Storage / Mount Layer includes lsblk output.",
        ]

    out = []
    out.append(f"Parsed {len(devices)} block-device lines from lsblk.")
    out.append("")
    out.append("| Device | Size | Filesystem | Mount status / hint |")
    out.append("|---|---|---|---|")

    for d in devices[:30]:
        out.append(f"| `{d['name']}` | {d['size']} | {d['fstype']} | `{d['mount']}` |")

    if len(devices) > 30:
        out.append("")
        out.append(f"Only showing first 30 entries out of {len(devices)} total.")

    return out


def make_storage_bind_table(rows):
    if not rows:
        return [
            "No Docker storage bind table was found in the current report.",
            "Run the safe analyzer again and analyse the report.",
        ]

    important = []
    normal = []

    for row in rows:
        source = row["source"]
        if (
            source.startswith("/media/")
            or source.startswith("/DATA/.media/")
            or source.startswith("/var/lib/casaos_data/.media/")
            or "/docker/volumes/" in source
        ):
            important.append(row)
        else:
            normal.append(row)

    ordered = important + normal

    out = []
    out.append(f"Parsed {len(rows)} Docker storage-related mounts from the report.")
    out.append("")
    out.append("| Container | Source path | Destination | RW | Risk |")
    out.append("|---|---|---|---|---|")

    for row in ordered[:35]:
        out.append(
            f"| {row['container']} | `{row['source']}` | `{row['destination']}` | {row['rw']} | {row['risk']} |"
        )

    if len(ordered) > 35:
        out.append("")
        out.append(f"Only showing first 35 entries out of {len(ordered)} total.")

    return out



def normalize_question(question: str) -> str:
    q = question.lower().strip()

    disk_words = [
        "check my disks", "check disks", "show disks", "show my disks",
        "list disks", "list my disks", "what disks", "what drives",
        "check my drives", "storage devices", "block devices",
        "disk health", "drive health", "how to check my disks",
        "how to check disks", "how do i check my disks",
    ]

    docker_storage_words = [
        "which docker apps", "which apps", "storage paths",
        "using storage", "look risky", "bind mounts", "app paths",
        "mapped paths", "where is my app data", "app storage",
    ]

    storage_folder_words = [
        "_1", "unexpected folder", "ghost folder", "missing files",
        "lost files", "empty folder", "storage folder", "media folder",
        "wrong path", "old path",
    ]

    raid_pool_words = [
        "raid", "array", "pool", "snapraid", "mergerfs",
        "parity", "storage combination", "supported storage",
    ]

    ssh_network_words = [
        "ssh", "remote access", "cloudflare", "tunnel", "port",
        "network", "firewall", "expose",
    ]

    extra = []

    if any(w in q for w in disk_words):
        extra.append(" disk not detected storage devices block devices show disks list disks")

    if any(w in q for w in docker_storage_words):
        extra.append(" which app which container storage paths using storage look risky bind")

    if any(w in q for w in storage_folder_words):
        extra.append(" storage folder media mount _1 unexpected ghost")

    if any(w in q for w in raid_pool_words):
        extra.append(" raid snapraid mergerfs parity pool storage combination")

    if any(w in q for w in ssh_network_words):
        extra.append(" network exposure ssh firewall port")

    if extra:
        return question + " " + " ".join(extra)

    return question


def disk_base_name(device_name: str) -> str:
    device_name = device_name.strip()
    if not device_name:
        return ""
    if device_name.startswith("nvme") and "p" in device_name:
        return device_name.rsplit("p", 1)[0]
    while device_name and device_name[-1].isdigit():
        device_name = device_name[:-1]
    return device_name


def container_has_published_ports(report_text: str, container_name: str) -> bool:
    for line in report_text.splitlines():
        if container_name in line and ("0.0.0.0:" in line or ":::" in line):
            return True
    return False


def build_hard_findings(report_text: str, storage_rows):
    text = report_text.lower()
    findings = []

    if "snapraid-sync.service" in text and "failed" in text:
        findings.append(
            "🔴 RED: DATA PROTECTION MAY BE DOWN. Evidence: snapraid-sync.service appears failed in the report. "
            "If this system depends on SnapRAID parity, sync is not completing and protection should not be trusted until checked."
        )

    sr_data_bases = set()
    sr_parity_bases = set()

    for raw in report_text.splitlines():
        low = raw.lower()
        if "sr-data" not in low and "sr-parity" not in low:
            continue

        parts = raw.replace("├─", "").replace("└─", "").strip().split()
        if not parts:
            continue

        dev = parts[0]
        base = disk_base_name(dev)

        if "sr-data" in low:
            sr_data_bases.add(base)
        if "sr-parity" in low:
            sr_parity_bases.add(base)

    same_disk = sr_data_bases.intersection(sr_parity_bases)
    if same_disk:
        findings.append(
            "🔴 RED: SNAPRAID PARITY AND DATA APPEAR TO SHARE THE SAME PHYSICAL DISK. "
            f"Evidence: data/parity labels were parsed on the same base disk(s): {', '.join(sorted(same_disk))}. "
            "If that physical disk dies, data and parity can die together."
        )

    for row in storage_rows:
        src = row.get("source", "")
        dst = row.get("destination", "")
        rw = str(row.get("rw", "")).lower()
        container = row.get("container", "")

        full_data_bind = src == "/DATA" and dst == "/DATA" and "true" in rw
        if full_data_bind:
            if container_has_published_ports(report_text, container):
                findings.append(
                    f"🔴 RED: CONTAINER {container} HAS FULL READ-WRITE /DATA ACCESS AND PUBLISHED PORTS. "
                    "Evidence: Docker mount shows /DATA -> /DATA rw, and Docker ports are published. "
                    "Verify authentication or firewall this container before trusting LAN exposure."
                )
            else:
                findings.append(
                    f"🟡 YELLOW: CONTAINER {container} HAS FULL READ-WRITE /DATA ACCESS. "
                    "Evidence: Docker mount shows /DATA -> /DATA rw. Verify this is intended."
                )

    if "exfat" in text:
        findings.append(
            "🟡 YELLOW: exFAT filesystem detected. Evidence: report contains exFAT. "
            "exFAT can be useful for removable disks, but it has no POSIX permissions and no journaling, so it is fragile for NAS-style workloads."
        )

    nvidia_runtime = "nvidia" in text and ("runtime" in text or "runtimes" in text)

    nvidia_section_lines = []
    capture_nvidia = False

    for raw in report_text.splitlines():
        line = raw.strip()
        low = line.lower()

        if "$ nvidia-smi" in low or line.startswith("NVIDIA-SMI"):
            capture_nvidia = True

        if capture_nvidia:
            nvidia_section_lines.append(line)

        if capture_nvidia and line.startswith("===== ") and "nvidia" not in low:
            break

    nvidia_section = "\n".join(nvidia_section_lines).lower()

    nvidia_ok = (
        "nvidia-smi" in nvidia_section
        and "driver version" in nvidia_section
        and "cuda version" in nvidia_section
    )

    nvidia_failed = (
        "nvidia-smi" in nvidia_section
        and not nvidia_ok
        and (
            "failed" in nvidia_section
            or "not found" in nvidia_section
            or "couldn't communicate" in nvidia_section
            or "could not communicate" in nvidia_section
            or "not-detected" in nvidia_section
            or "no devices were found" in nvidia_section
        )
    )

    if nvidia_runtime and nvidia_failed:
        findings.append(
            "🟡 YELLOW: NVIDIA runtime appears present but GPU acceleration is not verified. "
            "Evidence: NVIDIA runtime text exists, but the NVIDIA-SMI section indicates failure/not detected."
        )

    return findings


def next_step_from_hard_findings(hard_findings):
    joined = "\n".join(hard_findings).lower()

    if "snapraid-sync.service" in joined:
        return "Check the failed SnapRAID service before trusting parity protection. Start with the snapraid-sync service journal and do not run repair/sync until the pool config, data disks, and parity disk are verified."

    if "snapraid parity and data" in joined or "same physical disk" in joined:
        return "Verify the SnapRAID disk layout. Parity should not protect data that lives on the same physical disk. Confirm the physical disk mapping before treating the pool as protected."

    if "full read-write /data access" in joined and "published ports" in joined:
        return "Confirm authentication and firewall exposure for the container with /DATA mounted read-write. If authentication is not confirmed, firewall or stop the exposed service before using it on the LAN."

    if "exfat filesystem detected" in joined:
        return "Confirm whether the exFAT disks are only removable/transfer disks. Avoid relying on exFAT for NAS workloads without understanding the lack of POSIX permissions and journaling."

    if "nvidia runtime appears present" in joined:
        return "Check why nvidia-smi is failing before assuming GPU acceleration is active. Treat Ollama/Open WebUI or other GPU workloads as CPU-only until NVIDIA driver access is verified."

    return "Review the RED/YELLOW findings above first. Fix the highest-severity item before changing storage, Docker mounts, firewall rules, or repair settings."


def make_active_mount_table(active_mounts):
    clean_mounts = []

    for m in active_mounts:
        target = m.get("target", "")
        source = m.get("source", "")
        fstype = m.get("fstype", "")

        if "/docker/overlay2/" in target:
            continue
        if "/docker/volumes/" in target:
            continue
        if "/merged" in target:
            continue
        if fstype == "overlay":
            continue

        clean_target = target.replace("\\x20", " ")
        clean_source = source.replace("\\x20", " ")

        clean_mounts.append(
            {
                "target": clean_target,
                "source": clean_source,
                "fstype": fstype,
            }
        )

    if not clean_mounts:
        return [
            "No real active /media mounts were parsed from the report after excluding Docker overlay mounts.",
            "Run the safe analyzer again and check the Storage / Mount Layer."
        ]

    out = []
    out.append(f"Parsed {len(clean_mounts)} real active /media mounts from findmnt.")
    out.append("")
    out.append("| Active mount path | Source device | Filesystem |")
    out.append("|---|---|---|")

    for m in clean_mounts[:40]:
        out.append(f"| `{m['target']}` | `{m['source']}` | {m['fstype']} |")

    if len(clean_mounts) > 40:
        out.append("")
        out.append(f"Only showing first 40 active mounts out of {len(clean_mounts)} total.")

    return out


def is_attention_question(q):
    return (
        "what needs attention" in q
        or "what is wrong" in q
        or "system warning" in q
        or "warnings" in q
        or "risk" in q
        or "risks" in q
        or "health check" in q
        or "check system" in q
    )


def is_red_finding(finding):
    return finding.strip().startswith("🔴 RED") or finding.strip().startswith("RED")



def format_severity_dot(text: str) -> str:
    if text.startswith("YELLOW:"):
        return "🟡 " + text
    if text.startswith("RED:"):
        return "🔴 " + text
    if text.startswith("INFO:"):
        return "ℹ️ " + text
    return text

def parse_dashboard_alerts(report_text: str):
    alerts = []
    in_alerts = False

    for raw in report_text.splitlines():
        line = raw.strip()

        if line == "===== RAW DASHBOARD ALERTS =====":
            in_alerts = True
            continue

        if in_alerts and line.startswith("====="):
            break

        if in_alerts and line.startswith("WARN:"):
            alerts.append(line.replace("WARN:", "YELLOW:", 1).strip())
        elif in_alerts and line.startswith("CRITICAL:"):
            alerts.append(line.replace("CRITICAL:", "RED:", 1).strip())
        elif in_alerts and line.startswith("OK:"):
            alerts.append(line.replace("OK:", "INFO:", 1).strip())

    return alerts


def parse_dashboard_disks(report_text: str):
    disks = []
    in_disks = False

    for raw in report_text.splitlines():
        line = raw.strip()

        if line == "===== DISKS / SMART SUMMARY =====":
            in_disks = True
            continue

        if in_disks and line.startswith("====="):
            break

        if not in_disks or "|" not in line or line.startswith("Device ") or line.startswith("---"):
            continue

        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 10:
            disks.append({
                "device": parts[0],
                "model": parts[1],
                "size": parts[2],
                "mount": parts[3],
                "health": parts[4],
                "temp": parts[5],
                "realloc": parts[6],
                "pending": parts[7],
                "crc": parts[8],
                "power_on": parts[9],
            })

    return disks


def parse_dashboard_exited_containers(report_text: str):
    exited = []
    in_containers = False

    for raw in report_text.splitlines():
        line = raw.strip()

        if line == "===== CONTAINERS =====":
            in_containers = True
            continue

        if in_containers and line.startswith("====="):
            break

        if not in_containers or "|" not in line or line.startswith("Name ") or line.startswith("---"):
            continue

        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 3 and parts[1].lower() == "exited":
            exited.append({
                "name": parts[0],
                "status": parts[1],
                "image": parts[2],
            })

    return exited


def normalize_dashboard_evidence(dashboard_alerts, dashboard_disks, exited_containers):
    real_alerts = []
    info_alerts = []
    container_alerts = []

    for alert in dashboard_alerts:
        low = alert.lower()

        if "n/a" in low:
            if alert.startswith("YELLOW:"):
                alert = alert.replace("YELLOW:", "INFO:", 1)
            info_alerts.append(alert + " (SMART value unavailable, not confirmed failure)")
        elif "container exited" in low:
            container_alerts.append(alert)
        else:
            real_alerts.append(alert)

    disk_attention = []
    disk_ok = []

    for d in dashboard_disks:
        issues = []

        if d.get("crc") not in ["0", "-", "N/A", "", None]:
            issues.append(f"CRC {d.get('crc')}")
        if d.get("pending") not in ["0", "-", "N/A", "", None]:
            issues.append(f"pending {d.get('pending')}")
        if d.get("realloc") not in ["0", "-", "N/A", "", None]:
            issues.append(f"reallocated {d.get('realloc')}")
        if str(d.get("health", "")).upper() not in ["PASSED", "OK"]:
            issues.append(f"health {d.get('health')}")

        item = {
            "device": d.get("device"),
            "model": d.get("model"),
            "size": d.get("size"),
            "mount": d.get("mount"),
            "health": d.get("health"),
            "temp": d.get("temp"),
            "issues": issues,
        }

        if issues:
            disk_attention.append(item)
        else:
            disk_ok.append(item)

    return {
        "real_alerts": real_alerts,
        "info_alerts": info_alerts,
        "container_alerts": container_alerts,
        "disk_attention": disk_attention,
        "disk_ok": disk_ok,
        "exited_containers": exited_containers,
    }


def analyse_report(report_text: str, question: str = "") -> str:
    text = report_text.lower()
    q = question.lower()

    findings = []
    warnings = []
    avoid = []
    direct_answer = []

    storage_rows = parse_container_storage_mounts(report_text)
    active_mounts = parse_active_media_mounts(report_text)
    block_devices = parse_block_devices(report_text)
    hard_findings = build_hard_findings(report_text, storage_rows)
    dashboard_alerts = parse_dashboard_alerts(report_text)
    dashboard_disks = parse_dashboard_disks(report_text)
    exited_containers = parse_dashboard_exited_containers(report_text)
    normalized_dashboard = normalize_dashboard_evidence(dashboard_alerts, dashboard_disks, exited_containers)

    if "zimaos" in text:
        findings.append("ℹ️ ZimaOS host identity is present in the verified report.")

    if "zimaos v1.6" in text or "version=\"v1.6" in text:
        findings.append("ℹ️ ZimaOS 1.6.x detected. Apply 1.6.x storage and mount-path checks before assuming older behaviour.")
    elif "zimaos v1.5" in text or "version=\"v1.5" in text:
        findings.append("ℹ️ ZimaOS 1.5.x detected. Do not apply 1.6.x-specific storage folder assumptions unless the report shows matching evidence.")
    if "version=\"v1.6.1\"" in text or "pretty_name=\"zimaos v1.6.1\"" in text:
        findings.append("ZimaOS v1.6.1 is verified.")
    if "docker ps" in text or "docker system df" in text:
        findings.append("Docker layer was collected.")
    if "nvidia rtx" in text:
        findings.append("NVIDIA GPU is detected.")
    if "mergerfs-snapraid" in text:
        findings.append("mergerfs-snapraid sysext is present/merged in the native extension layer.")
    if "systemd-sysext" in text or "sysext" in text:
        findings.append("Native sysext layer was collected.")
    if block_devices:
        findings.append(f"Block device list was collected: {len(block_devices)} device lines parsed from lsblk.")
    if active_mounts:
        findings.append(f"Active /media mount list was collected: {len(active_mounts)} active media mounts detected.")
    if storage_rows:
        findings.append(f"Docker storage bind list was collected: {len(storage_rows)} storage-related mounts parsed.")

    if "failed failed" in text or "zima-cron-fix.service" in text:
        warnings.append("One or more failed systemd units may be present. Check the failed units section before repair.")
    if "docker-user" in text and "-a docker-user -j return" in text:
        warnings.append("DOCKER-USER chain returns immediately, so Docker-published ports are not being filtered there.")
    if "input accept" in text or "-p input accept" in text:
        warnings.append("Host INPUT policy appears open/ACCEPT.")
    if "/media/hdd-storage" in text and "/media/hdd-storage-/dev/sdb" in text:
        warnings.append("Multiple HDD storage-style paths exist. Storage paths must be verified before changing app bind mounts.")
    if "/docker/overlay2" in text:
        warnings.append("Report contains Docker overlay paths. These should be ignored for storage diagnosis.")

    drive_question = (
        "cannot add drive" in q
        or "cannot add drives" in q
        or "add drives" in q
        or "add drive" in q
        or "add storage" in q
        or "storage ui" in q
        or "disk not detected" in q
        or "drive not detected" in q
        or "drives not found" in q
        or "no devices found" in q
        or "cannot see disk" in q
        or "cannot see drive" in q
        or "check my disks" in q
        or "check disks" in q
        or "show disks" in q
        or "show my disks" in q
        or "list disks" in q
        or "list my disks" in q
        or "what disks" in q
        or "what drives" in q
        or "storage devices" in q
        or "block devices" in q
        or "disk health" in q
    )

    bind_question = (
        "bind" in q
        or "which app" in q
        or "which container" in q
        or "storage path" in q
        or "storage paths" in q
        or "using storage" in q
        or "look risky" in q
        or "apps are using storage" in q
    )

    storage_question = (
        "_1" in q
        or "unexpected" in q
        or "storage folder" in q
        or "ghost" in q
        or "mount" in q
        or "media" in q
    )

    combination_question = (
        "supported storage" in q
        or "storage combination" in q
        or "combination options" in q
        or "raid" in q
        or "snapraid" in q
        or "mergerfs" in q
        or "parity" in q
        or "pool" in q
    )

    mount_list_question = (
        "which disks are mounted" in q
        or "what disks are mounted" in q
        or "show mounted disks" in q
        or "list mounted disks" in q
        or "mounted disks" in q
        or "mounted drives" in q
        or "active mounts" in q
        or "show mounts" in q
        or "list mounts" in q
    )

    attention_question = is_attention_question(q)

    dashboard_alert_question = (
        "dashboard alert" in q
        or "dashboard alerts" in q
        or "show alerts" in q
        or "show me alerts" in q
        or "any alerts" in q
        or "alerts" in q
    )

    crc_question = "crc" in q or "sda crc" in q

    usage_question = (
        "filesystem usage" in q
        or "usage 100" in q
        or "sdd" in q and "100" in q
    )

    exited_question = (
        "exited container" in q
        or "exited containers" in q
        or "containers not running" in q
        or "which containers are exited" in q
        or "which containers not running" in q
        or "not running" in q
    )

    disk_health_question = (
        "which disks are healthy" in q
        or "which disks need attention" in q
        or "disk health" in q
        or "drives healthy" in q
    )

    if dashboard_alert_question:
        direct_answer.append("This is a dashboard alert question.")
        direct_answer.append("The answer comes from the Cube Dashboard Layer evidence after the Evidence Normalizer Layer has cleaned it.")
        direct_answer.append("")

        direct_answer.append("Real alerts:")
        if normalized_dashboard["real_alerts"]:
            for alert in normalized_dashboard["real_alerts"]:
                direct_answer.append(f"- {format_severity_dot(alert)}")
        else:
            direct_answer.append("- No real hardware/storage alerts were parsed.")

        direct_answer.append("")
        direct_answer.append("Container/service alerts:")
        if normalized_dashboard["container_alerts"]:
            for alert in normalized_dashboard["container_alerts"]:
                direct_answer.append(f"- {format_severity_dot(alert)}")
        else:
            direct_answer.append("- No exited container alerts were parsed.")

        direct_answer.append("")
        direct_answer.append("Info only / unsupported metrics:")
        if normalized_dashboard["info_alerts"]:
            for alert in normalized_dashboard["info_alerts"]:
                direct_answer.append(f"- {format_severity_dot(alert)}")
        else:
            direct_answer.append("- No unsupported/N/A SMART metrics were parsed.")

        direct_answer.append("")
        direct_answer.append("Priority order: real disk/storage alerts first, then exited containers, then informational unsupported metrics.")

    if crc_question:
        direct_answer.append("This is a disk CRC warning question.")
        crc_alerts = [
            a for a in dashboard_alerts
            if "crc" in a.lower()
            and "n/a" not in a.lower()
            and not a.lower().endswith("crc errors 0")
        ]
        if crc_alerts:
            direct_answer.append("CRC-related dashboard evidence:")
            for alert in crc_alerts:
                direct_answer.append(f"- {format_severity_dot(alert)}")
        for d in dashboard_disks:
            if d["device"] == "sda":
                direct_answer.append(f"sda evidence: health={d['health']}, temp={d['temp']}°C, realloc={d['realloc']}, pending={d['pending']}, crc={d['crc']}, power_on={d['power_on']}.")
        direct_answer.append("What it means: CRC errors usually point to a link/connection path issue such as cable, port, backplane, controller, or power stability, not automatically a failed disk.")

    if usage_question:
        direct_answer.append("This is a filesystem usage warning question.")
        usage_alerts = [a for a in dashboard_alerts if "filesystem usage" in a.lower() or "sdd" in a.lower()]
        if usage_alerts:
            direct_answer.append("Usage-related dashboard evidence:")
            for alert in usage_alerts:
                direct_answer.append(f"- {format_severity_dot(alert)}")
        for d in dashboard_disks:
            if d["device"] == "sdd":
                direct_answer.append(f"sdd evidence: model={d['model']}, size={d['size']}, mount={d['mount']}, health={d['health']}, temp={d['temp']}.")
        direct_answer.append("What it means: the dashboard sees sdd mounted and full/near-full. Because this appears to be a USB/flash style device, confirm the exact mount before deleting anything.")

    if exited_question:
        direct_answer.append("This is a container state question.")
        direct_answer.append("Exited containers parsed from the dashboard layer:")
        if exited_containers:
            for c in exited_containers:
                direct_answer.append(f"- {c['name']} ({c['image']})")
        else:
            direct_answer.append("- No exited containers were parsed from the dashboard layer.")

    if disk_health_question:
        direct_answer.append("This is a disk health summary question.")
        direct_answer.append("Disk health from the Cube Dashboard Layer:")
        if dashboard_disks:
            for d in dashboard_disks:
                attention = []
                if d["crc"] not in ["0", "-", "N/A"]:
                    attention.append(f"CRC {d['crc']}")
                if d["pending"] not in ["0", "-", "N/A"]:
                    attention.append(f"pending {d['pending']}")
                if d["realloc"] not in ["0", "-", "N/A"]:
                    attention.append(f"reallocated {d['realloc']}")
                status = "needs attention: " + ", ".join(attention) if attention else "looks OK from available SMART fields"
                direct_answer.append(f"- {d['device']}: {d['health']}, {d['temp']}°C, {status}")
        else:
            direct_answer.append("- No dashboard disk summary was parsed.")


    if drive_question:
        direct_answer.append("This is a disk / drive visibility question.")
        direct_answer.append("The first thing to confirm is whether ZimaOS/Linux can see the disk at all.")
        direct_answer.append("")
        direct_answer.append("How to read the table:")
        direct_answer.append("- Device = Linux disk or partition name, such as sda, sdb, nvme0n1, or nvme0n1p1.")
        direct_answer.append("- Size = capacity detected by Linux.")
        direct_answer.append("- Filesystem = detected format, such as btrfs, ext4, vfat, squashfs, or unknown.")
        direct_answer.append("- Mount hint = where the disk/partition appears to be mounted, if the analyzer could identify it from this line.")
        direct_answer.append("")
        direct_answer.append("Block devices found in the verified report:")
        direct_answer.extend(make_block_device_table(block_devices))
        direct_answer.append("")
        direct_answer.append("What this means:")
        direct_answer.append("- If the drive you expect is listed here, Linux can see it.")
        direct_answer.append("- If the drive you expect is not listed here, ZimaOS Storage cannot add it yet because the OS is not seeing the device.")
        direct_answer.append("- If a drive is listed but the mount hint is not shown, the disk/partition is detected but its mount state needs confirmation with findmnt.")
        direct_answer.append("- If a drive is listed with a /media path, it is mounted and should normally be usable as a storage path.")
        direct_answer.append("- If a RAID/HBA controller is involved and disks are missing from this table, check controller firmware/kernel logs before blaming the ZimaOS Storage UI.")

        warnings.append("Do not wipe, format, or create arrays until the exact disk identity is verified.")
        warnings.append("Do not assume a visible /media folder means the disk is mounted. Confirm with findmnt.")

    if bind_question and not exited_question:
        direct_answer.append("This is a Docker storage bind-mount verification question.")
        direct_answer.append("The answer comes from Docker inspect output in the verified report.")
        direct_answer.append("")
        direct_answer.append("Docker apps/storage paths found:")
        direct_answer.extend(make_storage_bind_table(storage_rows))

        warnings.append("Any container using /media, /DATA/.media, or /var/lib/casaos_data/.media depends on stable ZimaOS mount paths.")
        warnings.append("Docker internal volume paths under /media/.../docker/volumes should not be edited manually.")
        warnings.append("Do not change container bind mounts until the active source mount is confirmed with findmnt.")

    if combination_question:
        direct_answer.append("Supported storage options must be separated by layer: official ZimaOS storage, Docker app storage, and native sysext/community storage.")
        direct_answer.append("Official ZimaOS storage can use normal mounted disks and ZimaOS-managed storage paths.")
        direct_answer.append("Docker apps should bind only to verified active mount paths, not old or duplicate-looking /media folders.")
        direct_answer.append("Holger-style mergerfs + SnapRAID is a native extension approach through systemd-sysext, not a normal Docker app and not a modification of the read-only ZimaOS base.")
        direct_answer.append("For a parity-style pool, verify data disks, parity disk size, filesystem type, pool config, timers, sync state, and scrub state before recommending actions.")

        warnings.append("Do not mix storage methods without knowing which layer owns the data path.")
        warnings.append("Do not assume mergerfs/SnapRAID is configured correctly just because the sysext is present.")
        warnings.append("Do not run SnapRAID sync/repair until all data disks and parity disk are verified.")

    if mount_list_question:
        direct_answer.append("This is a mounted disk / active mount question.")
        direct_answer.append("The answer should come from findmnt, not from visible folders alone.")
        direct_answer.append("")
        direct_answer.append("Active /media mounts found in the verified report:")
        direct_answer.extend(make_active_mount_table(active_mounts))
        direct_answer.append("")
        direct_answer.append("How to interpret this:")
        direct_answer.append("- If a path appears in this table, it is an active mount.")
        direct_answer.append("- If a folder exists under /media but does not appear in this table, treat it as only a folder until verified.")
        direct_answer.append("- Docker apps should bind to active mount paths, not stale or duplicate-looking folders.")

        warnings.append("Do not delete or remap /media folders unless findmnt confirms what is actually mounted.")

    if storage_question and not mount_list_question:
        direct_answer.append("This is a storage/mount-path verification issue, not something to repair blindly.")
        direct_answer.append("Compare visible folders under /media with active mounts from findmnt.")
        direct_answer.append("A folder existing under /media does not prove it is an active disk mount.")
        direct_answer.append("If an app still points to an old /media path while the disk is mounted under a new path, the app can appear to lose its files.")

        warnings.append("Do not delete old-looking /media folders until findmnt confirms they are not active mounts.")


    network_question = (
        "ssh" in q
        or "remote access" in q
        or "cloudflare" in q
        or "tunnel" in q
        or "firewall" in q
        or "open port" in q
        or "ports" in q
        or "network" in q
    )

    if network_question:
        direct_answer.append("This is a network / remote access question.")
        direct_answer.append("The analyzer collected interfaces, routes, listening ports, and basic firewall chains.")
        direct_answer.append("Use the Network / Exposure layer to verify what is listening before exposing anything.")
        direct_answer.append("For SSH specifically, check whether an SSH service is listening in the ports section before assuming SSH is enabled.")

        warnings.append("Do not expose SSH or admin services publicly without confirming firewall, VPN, or tunnel protection.")
        warnings.append("Do not assume a port is safe just because the app is working locally.")


    red_findings = [item for item in hard_findings if is_red_finding(item)]
    top_findings = hard_findings if attention_question else red_findings
    other_system_findings = [item for item in hard_findings if item not in top_findings]

    if top_findings:
        direct_answer.insert(0, "")
        for item in reversed(top_findings):
            direct_answer.insert(0, item)
        direct_answer.insert(0, "Severity findings from this same report:")

    if not direct_answer:
        direct_answer.append("This report was analysed using deterministic verifier rules.")
        direct_answer.append("Ask a targeted question such as: show my disks, check Docker storage paths, cannot add drives, or explain storage folders.")

    avoid.extend(
        [
            "Do not run docker system prune.",
            "Do not remove containers in bulk.",
            "Do not delete /media folders until findmnt verifies whether they are active mounts.",
            "Do not change Docker bind mounts until the exact source path is verified.",
            "Do not repair SnapRAID/mergerfs until pool config, parity disk, and data disks are verified.",
        ]
    )

    output = []
    output.append("### Verified Diagnosis")
    output.append("")
    output.append("#### Direct answer / severity")
    for item in direct_answer:
        output.append(item if item.startswith("|") or item == "" else f"- {item}")

    output.append("")
    output.append("#### Verified facts")
    if findings:
        for item in findings:
            output.append(f"- {item}")
    else:
        output.append("- No strong verified facts were extracted. Run the safe analyzer first.")

    output.append("")
    output.append("#### Warnings")
    if warnings:
        for item in warnings:
            output.append(f"- {item}")
    else:
        output.append("- No deterministic warnings detected from the current report.")

    if other_system_findings:
        output.append("")
        output.append("#### Other system warnings")
        for item in other_system_findings:
            output.append(f"- {item}")

    output.append("")
    output.append("#### What not to touch")
    for item in avoid:
        output.append(f"- {item}")

    output.append("")
    output.append("#### Next safest step")
    if exited_question:
        output.append("- Inspect only the affected exited container logs/status. Do not remove containers in bulk.")
    elif drive_question:
        output.append("- If the expected drive is not listed in the block-device table, collect controller/kernel evidence next: lspci, lsblk, findmnt, and recent dmesg storage errors.")
    elif bind_question:
        output.append("- Review the table above. Any important app using /media or .media paths should be checked against active mounts before changing storage.")
    elif mount_list_question:
        output.append("- Compare the active mount table against any Docker app bind paths before changing storage paths or deleting old-looking /media folders.")
    elif storage_question:
        output.append("- Compare active findmnt paths against Docker bind paths before deleting or changing folders.")
    elif combination_question:
        output.append("- Verify the exact storage method before mixing ZimaOS storage, Docker binds, and sysext/community pooling.")
    elif network_question:
        output.append("- Check the listening ports section for SSH before enabling or exposing anything. If port 22 or an SSH service is not visible, SSH is not verified as active from this report.")
    elif dashboard_alert_question:
        output.append("- Check the real hardware/storage alerts first: sda CRC errors and sdd filesystem usage 100%. Then review exited containers separately.")
    elif crc_question:
        output.append("- Confirm whether the sda CRC count is increasing over time. If it increases, check cable, port, backplane, controller path, and power before blaming the disk.")
    elif usage_question:
        output.append("- Verify the active sdd mount and what data is on it before deleting anything. Confirm whether it is the intended USB/flash device.")
    elif exited_question:
        output.append("- Inspect only the affected exited container logs/status. Do not remove containers in bulk.")
    elif disk_health_question:
        output.append("- Treat N/A SMART values as unavailable data, not automatic failure. Focus first on real values such as sda CRC errors and full filesystems.")
    elif top_findings:
        output.append(f"- {next_step_from_hard_findings(top_findings)}")
    else:
        output.append("- Ask a targeted question such as: show my disks, check Docker storage paths, cannot add drives, or explain storage folders.")

    output.append("")
    output.append("#### Forum-ready summary")
    output.append("Based on the verified report, this should be handled by checking the actual layer involved first. Do not make storage, Docker, or repair changes until the relevant disk, mount, container, or sysext state is confirmed.")

    return "\n".join(output)



def load_logo_data_uri():
    logo_path = "/app/assets/zimabrain-ce-logo.png"
    try:
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/svg+xml;base64,{encoded}"
    except Exception:
        return ""

st.set_page_config(page_title="ZimaBrain CE", layout="wide")

st.markdown(
    """
<style>
.stApp { background: #080b10; color: #e8edf2; }
[data-testid="stSidebar"] { background: #111722; border-right: 1px solid #263241; }
.brand-row { display:flex; align-items:center; gap:18px; margin-bottom:4px; }
.app-logo { width:82px; height:82px; border-radius:22px; }
.main-title { font-size: 46px; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 0; }
.subtitle { color: #9aa8b5; font-size: 16px; margin-top: -6px; margin-bottom: 6px; }
.descriptor { color: #cbd5e1; font-size: 14px; margin-bottom: 18px; }
.rule-box { background: linear-gradient(90deg, #111827, #162033); border: 1px solid #2c3b4d; border-radius: 14px; padding: 16px 20px; margin-bottom: 18px; font-weight: 600; color: #dbeafe; }
.card { background: #111722; border: 1px solid #263241; border-radius: 16px; padding: 16px; min-height: 110px; }
.card-title { color: #93c5fd; font-size: 14px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
.card-value { font-size: 20px; font-weight: 800; color: #f8fafc; }
.card-small { font-size: 13px; color: #a7b4c2; margin-top: 6px; line-height: 1.4; }
.layer-chip { display: inline-block; background: #172033; border: 1px solid #304156; color: #dbeafe; border-radius: 999px; padding: 6px 10px; margin: 3px; font-size: 13px; }
.version-badge { display:inline-block; background:#1e293b; border:1px solid #334155; border-radius:999px; padding:6px 12px; margin-bottom:14px; color:#93c5fd; font-weight:700; }
textarea { font-family: monospace !important; }
</style>
""",
    unsafe_allow_html=True,
)

logo_uri = load_logo_data_uri()
if logo_uri:
    st.markdown(
        f"""
<div class="brand-row">
  <img src="{logo_uri}" class="app-logo">
  <div>
    <div class="main-title">{APP_NAME}</div>
    <div class="subtitle">{APP_SUBTITLE}</div>
    <div class="descriptor">{APP_DESCRIPTOR}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(f'<div class="main-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{APP_SUBTITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="descriptor">{APP_DESCRIPTOR}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="version-badge">App {APP_VERSION} · {ANALYZER_VERSION} · {RULESET_VERSION} · Local verifier</div>', unsafe_allow_html=True)
st.markdown('<div class="rule-box">Analyze first → Verifier second → Explainer third → Repair guide last</div>', unsafe_allow_html=True)

host = quick_status("hostname")
os_line = quick_status("grep '^PRETTY_NAME=' /etc/os-release | sed 's/PRETTY_NAME=//; s/\"//g'")
kernel = quick_status("uname -r")
docker_status = quick_status("docker version --format '{{.Server.Version}}' 2>/dev/null || echo unavailable")
failed_units = quick_status("systemctl --failed --no-legend 2>/dev/null | wc -l || echo unknown")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f'<div class="card"><div class="card-title">Host</div><div class="card-value">{host}</div><div class="card-small">{os_line}<br>Kernel {kernel}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="card"><div class="card-title">Docker</div><div class="card-value">v{docker_status}</div><div class="card-small">Read-only inspection</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="card"><div class="card-title">Answer Engine</div><div class="card-value">Verifier</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="card"><div class="card-title">System State</div><div class="card-value">Local</div><div class="card-small">Failed units: {failed_units}<br>Runs on this ZimaOS only</div></div>', unsafe_allow_html=True)

st.markdown("### ZimaOS / ZimaBrain Layers")
st.markdown(
    """
<span class="layer-chip">System</span>
<span class="layer-chip">Storage / Mounts</span>
<span class="layer-chip">Docker / Apps</span>
<span class="layer-chip">Storage Bind Evidence</span>
<span class="layer-chip">Drive Detection</span>
<span class="layer-chip">Network / Exposure</span>
<span class="layer-chip">GPU</span>
<span class="layer-chip">sysext Native Modules</span>
<span class="layer-chip">ZVM / libvirt</span>
<span class="layer-chip">xpkg / Package Extension</span>
<span class="layer-chip">Backup</span>
<span class="layer-chip">Secure File Sharing</span>
<span class="layer-chip">Firmware / Regression Sentinel</span>
<span class="layer-chip">Pool Maintenance</span>
<span class="layer-chip">Cube Dashboard Visual</span>
<span class="layer-chip">Dashboard Evidence Loader</span>
<span class="layer-chip">Evidence Normalizer</span>
<span class="layer-chip">Question Router</span>
<span class="layer-chip">Verified Answer Builder</span>
<span class="layer-chip">Brain Session / Review</span>
""",
    unsafe_allow_html=True,
)


def build_session_export(history):
    lines = []
    lines.append("# ZimaBrain CE Brain Session")
    lines.append("")
    lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if not history:
        lines.append("No questions asked yet.")
        return "\n".join(lines)

    for idx, item in enumerate(history, 1):
        lines.append(f"## {idx}. {item.get('question', '')}")
        lines.append("")
        lines.append(f"Time: {item.get('time', '')}")
        lines.append("")
        lines.append(item.get("answer", ""))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)

if "report_text" not in st.session_state:
    st.session_state.report_text = ""
if "report_path" not in st.session_state:
    st.session_state.report_path = ""
if "answer" not in st.session_state:
    st.session_state.answer = ""
if "qa_history" not in st.session_state:
    st.session_state.qa_history = []
if "dashboard_report" not in st.session_state:
    st.session_state.dashboard_report = ""
if "dashboard_status" not in st.session_state:
    st.session_state.dashboard_status = ""
if "show_full_session" not in st.session_state:
    st.session_state.show_full_session = False

with st.sidebar:
    st.markdown("### Brain Session")

    if st.button("Clear Brain Session", use_container_width=True):
        st.session_state.qa_history = []
        st.session_state.answer = ""
        st.session_state.show_full_session = False
        st.rerun()

    if st.button("Open Full Session View", use_container_width=True):
        st.session_state.show_full_session = True
        st.rerun()

    if st.session_state.qa_history:
        st.download_button(
            "Download Brain Session",
            data=build_session_export(st.session_state.qa_history),
            file_name=f"zimabrain-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    if st.session_state.qa_history:
        for idx, item in enumerate(reversed(st.session_state.qa_history), 1):
            preview = item["question"]
            if len(preview) > 46:
                preview = preview[:46] + "..."
            with st.expander(f"{idx}. {preview}", expanded=(idx == 1)):
                st.caption(item["time"])
                answer_preview = item["answer"]
                if len(answer_preview) > 900:
                    answer_preview = answer_preview[:900] + "\n\n... open Full Session View for complete answer ..."
                st.markdown(answer_preview)
    else:
        st.caption("No questions asked yet.")


if st.session_state.show_full_session:
    st.markdown("## Brain Session Full View")

    if st.button("Close Full Session View", use_container_width=True):
        st.session_state.show_full_session = False
        st.rerun()

    if st.session_state.qa_history:
        st.download_button(
            "Download Full Brain Session",
            data=build_session_export(st.session_state.qa_history),
            file_name=f"zimabrain-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.markdown(build_session_export(st.session_state.qa_history))
    else:
        st.info("No questions asked yet.")

    st.divider()


st.markdown("### Cube Dashboard View")

st.caption("Live dashboard is optional. Over Zima Client, keep it closed unless needed.")

show_cube_dashboard = st.checkbox("Show live Cube Dashboard visual", value=False)

if show_cube_dashboard:
    components.html(
        """
        <div style="border:1px solid rgba(120,140,180,0.22); border-radius:14px; overflow:hidden; margin-bottom:14px; background:#050814;">
          <iframe id="cube-dash-frame" style="width:100%; height:650px; border:0; background:#050814;"></iframe>
        </div>
        <script>
        (function() {
          let host = window.location.hostname;
          let proto = window.location.protocol;
          try {
            host = window.parent.location.hostname || host;
            proto = window.parent.location.protocol || proto;
          } catch (e) {}
          document.getElementById("cube-dash-frame").src = proto + "//" + host + ":8514";
        })();
        </script>
        """,
        height=680,
    )
else:
    st.info("Live Cube Dashboard visual is hidden to keep Zima Client stable. Dashboard evidence can still be loaded below for Brain answers.")
st.markdown("### Local Diagnostic Report")
if st.button("Run safe analyzer", use_container_width=True):
    report_path, report_text = collect_report()
    st.session_state.report_path = report_path
    st.session_state.report_text = report_text
    st.session_state.answer = ""
    st.success(f"Report created: {report_path}")

if st.session_state.report_path:
    st.code(st.session_state.report_path)

st.text_area(
    "Analyzer output",
    st.session_state.report_text,
    height=430,
)

st.markdown("### Cube Dashboard Layer")

if st.button("Load Dashboard Layer", use_container_width=True):
    dash_text, dash_error = load_dashboard_layer()
    if dash_error:
        st.session_state.dashboard_status = dash_error
        st.session_state.dashboard_report = ""
        st.warning(dash_error)
    else:
        st.session_state.dashboard_report = dash_text
        st.session_state.dashboard_status = "Dashboard layer loaded into ZimaBrain evidence."
        st.success(st.session_state.dashboard_status)

if st.session_state.dashboard_status:
    st.caption(st.session_state.dashboard_status)

if st.session_state.dashboard_report.strip():
    st.success(f"Dashboard evidence loaded: {len(st.session_state.dashboard_report):,} characters. Hidden from UI to keep Zima Client stable.")
else:
    st.caption("Dashboard evidence not loaded yet.")

st.markdown("### Ask ZimaBrain CE")

question = st.text_area(
    "Question",
    "Cannot add drives for storage",
    height=120,
)

if st.button("Analyse Report", use_container_width=True):
    if not st.session_state.report_text.strip():
        st.warning("Run the safe analyzer first.")
    else:
        combined_report = st.session_state.report_text

        if st.session_state.dashboard_report.strip():
            combined_report += "\n\n===== ZIMABRAIN DASHBOARD LAYER =====\n"
            combined_report += st.session_state.dashboard_report

        normalized_question = normalize_question(question)
        st.session_state.answer = analyse_report(combined_report, normalized_question)
        st.session_state.qa_history.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": normalized_question,
            "answer": st.session_state.answer,
        })

if st.session_state.answer:
    st.markdown("### Verified Diagnosis")
    st.text_area(
        "Answer",
        st.session_state.answer,
        height=620,
    )
    st.download_button(
        "Download Current Answer",
        data=st.session_state.answer,
        file_name=f"zimabrain-answer-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md",
        mime="text/markdown",
        use_container_width=True,
    )

st.divider()
st.caption("ZimaBrain CE follows the Holger method: do not fight the base OS, verify the layer, keep state under /DATA, and repair only after evidence.")
