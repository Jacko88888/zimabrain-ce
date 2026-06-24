import urllib.request
import subprocess
import re

DASHBOARD_REPORT_URL = "http://host.docker.internal:8514/zimabrain-report"
DASHBOARD_REPORT = ""
DASHBOARD_STATUS = "Dashboard evidence not loaded yet."

def fetch_dashboard_report():
    req = urllib.request.Request(
        DASHBOARD_REPORT_URL,
        headers={"User-Agent": "ZimaBrain-CE-Flask"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode("utf-8", errors="replace").strip()


def parse_dashboard_alerts(report_text):
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


def parse_dashboard_disks(report_text):
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


def parse_dashboard_exited_containers(report_text):
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


def severity_dot(text):
    if text.startswith("YELLOW:"):
        return "🟡 " + text
    if text.startswith("RED:"):
        return "🔴 " + text
    if text.startswith("INFO:"):
        return "ℹ️ " + text
    return text




def parse_dashboard_container_count(report_text):
    """
    Parse visual dashboard container count such as:
    - Containers 44/50
    - CONTAINERS 3/4
    - containers: 4/4 running
    This is dashboard summary evidence, separate from named exited-container rows.
    """
    text = str(report_text or "")
    patterns = [
        r"\bcontainers?\b\s*[:\-]?\s*(\d+)\s*/\s*(\d+)",
        r"\bCONTAINERS?\b\s*[:\-]?\s*(\d+)\s*/\s*(\d+)",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        running = int(m.group(1))
        total = int(m.group(2))
        if total > 0 and 0 <= running <= total:
            return {
                "running": running,
                "total": total,
                "not_running": total - running,
                "source": "visual_dashboard_container_count",
            }

    return {
        "running": None,
        "total": None,
        "not_running": None,
        "source": "not_parsed",
    }


def normalize_dashboard_evidence(alerts, disks, exited):
    real_alerts = []
    info_alerts = []
    container_alerts = []

    for alert in alerts:
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

    for d in disks:
        issues = []
        if d.get("crc") not in ["0", "-", "N/A", "", None]:
            issues.append(f"CRC {d.get('crc')}")
        if d.get("pending") not in ["0", "-", "N/A", "", None]:
            issues.append(f"pending {d.get('pending')}")
        if d.get("realloc") not in ["0", "-", "N/A", "", None]:
            issues.append(f"reallocated {d.get('realloc')}")
        if str(d.get("health", "")).upper() not in ["PASSED", "OK"]:
            issues.append(f"health {d.get('health')}")

        item = dict(d)
        item["issues"] = issues

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
        "exited_containers": exited,
    }


def run_host_command(command, timeout=12):
    try:
        return subprocess.check_output(
            ["nsenter", "-t", "1", "-m", "-u", "-n", "-i", "--", "sh", "-lc", command],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        ).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()
    except Exception as e:
        return f"ERROR: {e}"


def collect_same_report_evidence():
    return {
        "failed_units": run_host_command("systemctl --failed --no-pager --no-legend 2>/dev/null || true"),
        "lsblk": run_host_command("lsblk -o NAME,PKNAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS 2>/dev/null || true"),
        "mounts": run_host_command("findmnt -P -o SOURCE,TARGET,FSTYPE,OPTIONS 2>/dev/null | grep -Ei 'mergerfs|snapraid|/DATA|/media' | head -120 || true"),
        "docker_ps": run_host_command("docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>/dev/null | head -120 || true"),
        "docker_access": run_host_command(
            "for c in $(docker ps -q 2>/dev/null); do "
            "docker inspect --format '{{.Name}}|{{range .Mounts}}{{.Source}}->{{.Destination}}:{{.RW}};{{end}}|{{range $p,$v := .NetworkSettings.Ports}}{{$p}}=>{{range $v}}{{.HostIp}}:{{.HostPort}},{{end}};{{end}}' $c; "
            "done 2>/dev/null | head -200 || true",
            timeout=20,
        ),
        "nvidia": run_host_command("nvidia-smi -L 2>&1 || true"),
        "zfw_status": run_host_command("systemctl is-active zfw-ui.service 2>/dev/null || true"),
        "zfw_files": run_host_command("ls -l /var/lib/extensions/zfw.raw /DATA/zfw/zfw /DATA/zfw/rules.json 2>/dev/null || true"),
        "zfw_chains": run_host_command("iptables -S ZFW-IN 2>/dev/null || true; iptables -S ZFW-IN6 2>/dev/null || true; iptables -S DOCKER-USER 2>/dev/null || true"),
    }


def evaluate_critical_same_report(evidence):
    findings = []
    failed = evidence.get("failed_units", "")
    lsblk_text = evidence.get("lsblk", "")
    mounts = evidence.get("mounts", "")
    docker_ps = evidence.get("docker_ps", "")
    docker_access = evidence.get("docker_access", "")
    nvidia = evidence.get("nvidia", "")

    low_failed = failed.lower()
    low_mounts = mounts.lower()
    low_ps = docker_ps.lower()
    low_access = docker_access.lower()
    low_nvidia = nvidia.lower()

    if failed.strip():
        findings.append({
            "level": "YELLOW",
            "title": "Failed systemd unit detected",
            "detail": failed.splitlines()[0],
            "why": "A failed host unit can indicate a broken scheduled task, service, or maintenance layer.",
            "next": "Inspect the exact failed unit before changing anything.",
        })

    if "snapraid-sync.service" in low_failed and "failed" in low_failed:
        level = "RED" if ("mergerfs" in low_mounts or "snapraid" in low_mounts) else "YELLOW"
        findings.append({
            "level": level,
            "title": "DATA PROTECTION MAY BE DOWN",
            "detail": "snapraid-sync.service is failed in the same host report.",
            "why": "If a mergerfs/SnapRAID pool depends on this sync, parity protection is not completing.",
            "next": "Check journalctl -u snapraid-sync and verify SnapRAID config/parity before trusting protection.",
        })

    # Holger rule: data + parity partitions on same physical disk.
    sr_rows = []
    for raw in lsblk_text.splitlines():
        line = raw.strip()
        if "SR-DATA" in line or "SR-PARITY" in line:
            sr_rows.append(line)

    if sr_rows:
        physical_roots = set()
        has_data = False
        has_parity = False

        for line in sr_rows:
            parts = line.split()
            if not parts:
                continue
            name = parts[0].replace("└─", "").replace("├─", "")
            root = name
            if name.startswith("sd") and len(name) > 3:
                root = name[:3]
            if "SR-DATA" in line:
                has_data = True
            if "SR-PARITY" in line:
                has_parity = True
            physical_roots.add(root)

        if has_data and has_parity and len(physical_roots) == 1:
            findings.append({
                "level": "RED",
                "title": "SnapRAID parity has no physical fault tolerance",
                "detail": "Data and parity labels appear on the same physical disk.",
                "why": "If that disk dies, both data and parity die together.",
                "next": "Move parity to a separate physical disk before treating the pool as protected.",
            })

    # Exposed full data access rule.
    for raw in docker_access.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue

        name = line.split("|", 1)[0].lstrip("/")
        line_low = line.lower()

        # Strict Holger rule:
        # flag only full host /DATA mounted back as /DATA read-write,
        # not normal app folders like /DATA/AppData/app -> /data.
        has_full_data_rw = (
            "/DATA->/DATA:True" in line
            or "/DATA->/DATA:true" in line
            or "/DATA->/DATA:rw" in line
            or "/host/DATA->/DATA:True" in line
            or "/host/DATA->/DATA:true" in line
            or "/host/DATA->/DATA:rw" in line
        )

        publishes_lan = (
            "0.0.0.0:" in line_low
            or ":::" in line_low
            or "192.168." in line_low
            or "10." in line_low
        )

        if has_full_data_rw and publishes_lan:
            findings.append({
                "level": "RED",
                "title": "Container has full /DATA write access and published ports",
                "detail": name,
                "why": "A no-auth web/VNC/desktop service here could expose all user data to the network.",
                "next": "Verify authentication and restrict/firewall the published ports before trusting it.",
            })

    # exFAT warning.
    exfat_rows = [line.strip() for line in lsblk_text.splitlines() if " exfat " in f" {line.lower()} "]
    if exfat_rows:
        findings.append({
            "level": "YELLOW",
            "title": "exFAT storage detected",
            "detail": "; ".join(exfat_rows[:3]),
            "why": "exFAT has no POSIX permissions and no journaling, so it is weaker for NAS workload safety.",
            "next": "Use exFAT only when portability is required, and avoid treating it like a robust NAS filesystem.",
        })

    # GPU runtime warning.
    ai_running = ("ollama" in low_ps or "open-webui" in low_ps or "pdf-ai" in low_ps)
    gpu_bad = (
        "failed" in low_nvidia
        or "not found" in low_nvidia
        or "couldn't communicate" in low_nvidia
        or "no devices were found" in low_nvidia
        or "error" in low_nvidia
    )

    if ai_running and gpu_bad:
        findings.append({
            "level": "YELLOW",
            "title": "GPU acceleration may not be active",
            "detail": nvidia.splitlines()[0] if nvidia.strip() else "nvidia-smi returned no GPU.",
            "why": "AI containers may be running CPU-only even though GPU workloads are expected.",
            "next": "Verify nvidia-smi and container GPU runtime before assuming Ollama/Open WebUI is GPU accelerated.",
        })

    return findings


def dashboard_bundle():
    global DASHBOARD_REPORT, DASHBOARD_STATUS

    if not DASHBOARD_REPORT.strip():
        try:
            DASHBOARD_REPORT = fetch_dashboard_report()
            DASHBOARD_STATUS = f"Dashboard evidence loaded: {len(DASHBOARD_REPORT):,} characters."
        except Exception as e:
            DASHBOARD_STATUS = f"Dashboard evidence unavailable: {e}"

    alerts = parse_dashboard_alerts(DASHBOARD_REPORT)
    disks = parse_dashboard_disks(DASHBOARD_REPORT)
    exited = parse_dashboard_exited_containers(DASHBOARD_REPORT)
    container_count = parse_dashboard_container_count(DASHBOARD_REPORT)
    normalized = normalize_dashboard_evidence(alerts, disks, exited)
    same_report_evidence = collect_same_report_evidence()
    critical_findings = evaluate_critical_same_report(same_report_evidence)

    return {
        "report": DASHBOARD_REPORT,
        "status": DASHBOARD_STATUS,
        "alerts": alerts,
        "disks": disks,
        "exited": exited,
        "container_count": container_count,
        "normalized": normalized,
        "same_report_evidence": same_report_evidence,
        "critical_findings": critical_findings,
    }


def run_host_shell(command, timeout=12):
    try:
        return subprocess.check_output(
            ["nsenter", "-t", "1", "-m", "-u", "-n", "-i", "--", "sh", "-lc", command],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        ).strip()
    except subprocess.CalledProcessError as e:
        return (e.output or "").strip()
    except Exception as e:
        return f"ERROR: {e}"


def parse_lsblk_pairs(text):
    rows = []
    for line in text.splitlines():
        item = {}
        for key, value in re.findall(r'(\w+)="([^"]*)"', line):
            item[key] = value
        if item:
            rows.append(item)
    return rows


def collect_critical_verifier():
    findings = []
    facts = []

    failed_units = run_host_shell("systemctl --failed --no-pager --no-legend 2>/dev/null || true")
    lsblk_text = run_host_shell("lsblk -P -o NAME,PKNAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS 2>/dev/null || true")
    mounts_text = run_host_shell("findmnt -o SOURCE,TARGET,FSTYPE,OPTIONS 2>/dev/null | grep -Ei 'mergerfs|snapraid|/DATA|/media' | head -250 || true")
    docker_ps = run_host_shell("docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true", timeout=15)
    docker_inspect = run_host_shell(
        "for id in $(docker ps -q 2>/dev/null); do docker inspect --format '{{.Name}}|{{range .Mounts}}{{.Source}}>{{.Destination}}>{{.RW}};{{end}}|{{json .NetworkSettings.Ports}}' \"$id\"; done 2>/dev/null || true",
        timeout=25,
    )
    docker_user = run_host_shell("iptables -S DOCKER-USER 2>/dev/null || true")
    gpu_text = run_host_shell("docker info 2>/dev/null | grep -i -A4 'Runtimes' || true; echo '---NVIDIA---'; nvidia-smi -L 2>&1 || true", timeout=12)

    failed_lower = failed_units.lower()
    mounts_lower = mounts_text.lower()
    docker_lower = docker_ps.lower()
    gpu_lower = gpu_text.lower()

    if failed_units.strip():
        facts.append("systemctl --failed returned one or more failed units.")
        for line in failed_units.splitlines():
            if line.strip():
                if "snapraid-sync.service" in line:
                    findings.append({
                        "level": "RED",
                        "title": "DATA PROTECTION IS DOWN",
                        "evidence": "systemctl --failed shows snapraid-sync.service failed.",
                        "why": "SnapRAID sync is not completing, so parity protection is not current.",
                        "next": "Check journalctl -u snapraid-sync and fix the SnapRAID config/parity before relying on the pool.",
                    })
                else:
                    findings.append({
                        "level": "YELLOW",
                        "title": "Failed systemd unit detected",
                        "evidence": line.strip(),
                        "why": "A failed host unit can indicate a broken scheduled task or system helper.",
                        "next": "Inspect only this failed unit before changing unrelated services.",
                    })

    mergerfs_mounted = "mergerfs" in mounts_lower
    if mergerfs_mounted:
        facts.append("A mergerfs mount is present in findmnt output.")

    if "snapraid-sync.service" in failed_lower and mergerfs_mounted:
        findings.append({
            "level": "RED",
            "title": "MergerFS pool present while SnapRAID sync is failed",
            "evidence": "findmnt shows mergerfs and systemctl --failed shows snapraid-sync.service failed.",
            "why": "The pool may look usable, but parity protection is not completing.",
            "next": "Fix SnapRAID sync first, then verify snapraid status/sync/scrub.",
        })

    rows = parse_lsblk_pairs(lsblk_text)
    sr_data = []
    sr_parity = []

    for r in rows:
        label = r.get("LABEL", "")
        fstype = r.get("FSTYPE", "")
        name = r.get("NAME", "")
        pkname = r.get("PKNAME", "") or name
        size = r.get("SIZE", "")

        if label.upper().startswith("SR-DATA"):
            sr_data.append((name, pkname, label))
        if "PARITY" in label.upper():
            sr_parity.append((name, pkname, label))

        if fstype.lower() == "exfat":
            findings.append({
                "level": "YELLOW",
                "title": "exFAT disk detected",
                "evidence": f"{name} label={label} size={size} fstype=exfat.",
                "why": "exFAT has no POSIX permissions and no journaling, so it is fragile under NAS workload.",
                "next": "Use it only with clear intent, and verify backups before depending on it.",
            })

    if sr_data and sr_parity:
        data_pk = {x[1] for x in sr_data}
        parity_pk = {x[1] for x in sr_parity}
        overlap = sorted(data_pk.intersection(parity_pk))
        if overlap:
            findings.append({
                "level": "RED",
                "title": "SnapRAID parity is on the same physical disk as data",
                "evidence": f"Data labels {sr_data} and parity labels {sr_parity} share physical disk(s): {', '.join(overlap)}.",
                "why": "If that physical disk fails, data and parity are lost together.",
                "next": "Move parity to a separate physical disk before treating the pool as protected.",
            })

    docker_user_open = "-A DOCKER-USER -j RETURN" in docker_user or "RETURN" in docker_user

    for line in docker_inspect.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue

        name, mounts, ports = parts
        cname = name.lstrip("/")

        has_data_rw = ">/DATA>true" in mounts or ">/host/DATA>true" in mounts
        has_ports = '"HostPort"' in ports and ports not in ["{}", "null"]

        if has_data_rw and has_ports:
            level = "RED" if docker_user_open else "YELLOW"
            findings.append({
                "level": level,
                "title": "Published container has full read-write /DATA access",
                "evidence": f"{cname} has /DATA rw and published ports: {ports[:240]}",
                "why": "If the service has no authentication or weak authentication, LAN access can become full data access.",
                "next": "Verify authentication and firewall exposure for this container before exposing it further.",
            })

    if ("ollama" in docker_lower or "open-webui" in docker_lower) and (
        "failed" in gpu_lower
        or "not found" in gpu_lower
        or "couldn't communicate" in gpu_lower
        or "no devices were found" in gpu_lower
    ):
        findings.append({
            "level": "YELLOW",
            "title": "GPU acceleration may not be active",
            "evidence": "ollama/open-webui is running, but nvidia-smi did not return a usable GPU list.",
            "why": "AI containers may be running CPU-only even if GPU runtime appears configured.",
            "next": "Verify nvidia-smi on host and inside the intended AI container before assuming GPU acceleration.",
        })

    if not facts:
        facts.append("Critical verifier collected host evidence but found no high-confidence structural facts.")

    red_count = len([f for f in findings if f["level"] == "RED"])
    yellow_count = len([f for f in findings if f["level"] == "YELLOW"])

    return {
        "findings": findings,
        "facts": facts,
        "red_count": red_count,
        "yellow_count": yellow_count,
    }


def critical_to_text(critical):
    lines = []
    findings = critical.get("findings", [])

    if not findings:
        lines.append("- No RED/YELLOW same-report critical findings were detected by the current verifier layer.")
        return lines

    for item in findings:
        icon = "🔴" if item["level"] == "RED" else "🟡"
        lines.append(f"- {icon} {item['level']}: {item['title']}")
        lines.append(f"  Evidence: {item['evidence']}")
        lines.append(f"  Why it matters: {item['why']}")
        lines.append(f"  Next safest step: {item['next']}")

    return lines


def simplify_mount_line(line):
    # Preferred format from: findmnt -P -o SOURCE,TARGET,FSTYPE,OPTIONS
    pairs = dict(re.findall(r'([A-Z]+)="([^"]*)"', line))

    if pairs:
        source = pairs.get("SOURCE", "")
        target = pairs.get("TARGET", "")
        fstype = pairs.get("FSTYPE", "")
        opts = pairs.get("OPTIONS", "")
        mode = "ro" if opts.startswith("ro") or ",ro" in opts else "rw"

        label = f"{source} -> {target}"
        if fstype:
            label += f" [{fstype}]"
        label += f" {mode}"
        return label.strip()

    # Fallback for older raw findmnt tree output.
    cleaned = line.replace("│", " ").replace("├─", " ").replace("└─", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned
