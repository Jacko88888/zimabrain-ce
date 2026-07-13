import urllib.request
import subprocess
import re

DASHBOARD_REPORT_URL = ""  # old external 8514 dashboard disabled
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


def classify_exited_container(name, image=""):
    name_l = str(name or "").lower()
    image_l = str(image or "").lower()

    completed_markers = [
        "migration", "migrations", "migrate", "init", "setup", "bootstrap",
        "oneshot", "one-shot", "job", "worker-once"
    ]
    duplicate_markers = [
        "fixed", "old", "backup", "bak", "test", "trial", "copy", "full"
    ]
    service_stack_markers = [
        "mailcow", "postfix", "dovecot", "mysql", "mariadb", "postgres",
        "redis", "nginx", "traefik", "immich", "nextcloud", "plex",
        "jellyfin", "qbittorrent"
    ]

    if any(x in name_l for x in completed_markers):
        return {
            "class": "on_demand_completed",
            "severity": "INFO",
            "reason": "Name looks like a one-shot setup/migration container. Exited may be expected.",
        }

    if any(x in name_l for x in duplicate_markers):
        return {
            "class": "manual_or_duplicate",
            "severity": "INFO",
            "reason": "Name looks like a test, fixed, full, old, backup, or duplicate container. Exited may be intentional.",
        }

    if any(x in name_l or x in image_l for x in service_stack_markers):
        return {
            "class": "service_stack_stopped",
            "severity": "YELLOW",
            "reason": "Name/image looks like an application service. Confirm whether it should be running.",
        }

    return {
        "class": "unknown_exited",
        "severity": "YELLOW",
        "reason": "Exited container was detected, but ZimaBrain cannot tell if it is intentional from name/image alone.",
    }


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
            cls = classify_exited_container(parts[0], parts[2])
            exited.append({
                "name": parts[0],
                "status": parts[1],
                "image": parts[2],
                "class": cls["class"],
                "severity": cls["severity"],
                "reason": cls["reason"],
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


def dashboard_alert_source(alert):
    text = str(alert or "")
    low = text.lower()

    source = "dashboard_alert"
    obj = "unknown"
    condition = "unparsed"

    disk_match = re.search(r'(/dev/[a-z]+[0-9]*|/dev/nvme[0-9]+n[0-9]+|nvme[0-9]+n[0-9]+|sd[a-z][0-9]*)', text, re.IGNORECASE)
    if disk_match:
        source = "disk"
        obj = disk_match.group(1)

    container_match = re.search(r'container\s+(?:exited|stopped|unhealthy)?\s*[:\-]?\s*([A-Za-z0-9_.-]+)', text, re.IGNORECASE)
    if container_match:
        source = "container"
        obj = container_match.group(1)

    service_match = re.search(r'([A-Za-z0-9_.@-]+\.(?:service|timer|mount|socket))', text)
    if service_match:
        source = "service"
        obj = service_match.group(1)

    if "crc" in low:
        condition = "CRC warning"
    elif "pending" in low:
        condition = "pending sectors"
    elif "realloc" in low or "reallocated" in low:
        condition = "reallocated sectors"
    elif "n/a" in low:
        condition = "value unavailable"
    elif "exited" in low or "stopped" in low:
        condition = "not running"
    elif "failed" in low:
        condition = "failed"
    elif "temperature" in low or "temp" in low:
        condition = "temperature"

    return {
        "text": text,
        "source": source,
        "object": obj,
        "condition": condition,
        "parsed": obj != "unknown" or condition != "unparsed",
    }


def normalize_dashboard_evidence(alerts, disks, exited):
    real_alerts = []
    info_alerts = []
    container_alerts = []
    real_alert_details = []
    info_alert_details = []
    container_alert_details = []
    unparsed_alerts = []

    for alert in alerts:
        meta = dashboard_alert_source(alert)
        low = alert.lower()
        if "n/a" in low:
            if alert.startswith("YELLOW:"):
                alert = alert.replace("YELLOW:", "INFO:", 1)
            enriched = alert + " (SMART value unavailable, not confirmed failure)"
            info_alerts.append(enriched)
            meta["text"] = enriched
            info_alert_details.append(meta)
        elif "container exited" in low:
            container_alerts.append(alert)
            container_alert_details.append(meta)
        else:
            real_alerts.append(alert)
            real_alert_details.append(meta)

        if not meta.get("parsed"):
            unparsed_alerts.append(alert)

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
        "real_alert_details": real_alert_details,
        "info_alert_details": info_alert_details,
        "container_alert_details": container_alert_details,
        "unparsed_alerts": unparsed_alerts,
        "unparsed_alert_count": len(unparsed_alerts),
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
        "failed_units": run_host_command("systemctl --failed --plain --no-pager --no-legend 2>/dev/null || true"),
        "lsblk": run_host_command("lsblk -o NAME,PKNAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS 2>/dev/null || true"),
        "mounts": run_host_command("findmnt -P -o SOURCE,TARGET,FSTYPE,OPTIONS 2>/dev/null | grep -Ei 'mergerfs|snapraid|/DATA|/media|\\.media' | grep -v '/docker/overlay2/' | head -160 || true"),
        "media_paths": run_host_command("ls -ld /DATA /DATA/AppData /media /DATA/.media /var/lib/casaos_data/.media 2>/dev/null || true; echo ---MEDIA_ROOTS---; find /media -maxdepth 1 -mindepth 1 -type d -printf '%M %u %g %p\\n' 2>/dev/null | head -80", timeout=12),
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
        "auditd": run_host_command("systemctl is-active auditd.service 2>/dev/null || true; systemctl status auditd.service --no-pager 2>/dev/null | head -80; echo ---AUDIT_PATHS---; ls -ld /var/log/audit 2>/dev/null || true; ls -l /var/log/audit/audit.log 2>/dev/null || true", timeout=12),
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

    auditd = evidence.get("auditd", "")
    low_auditd = auditd.lower()
    audit_lines = [x.strip() for x in auditd.splitlines() if x.strip()]
    audit_path_lines = [x for x in audit_lines if "/var/log/audit" in x]

    if "auditd.service" in low_auditd and ("failed" in low_auditd or "inactive" in low_auditd or "permission denied" in low_auditd):
        expected_dir = any("drwx------" in x and "root root" in x and "/var/log/audit" in x for x in audit_path_lines)
        expected_log = any("-rw-------" in x and "root root" in x and "audit.log" in x for x in audit_path_lines)
        bad_owner_or_mode = bool(audit_path_lines) and not (expected_dir and expected_log)

        if bad_owner_or_mode or "permission denied" in low_auditd:
            findings.append({
                "level": "YELLOW",
                "title": "auditd may be failing from audit log ownership or permissions",
                "detail": "\n".join(audit_path_lines[:4]) or auditd[:300],
                "why": "auditd normally needs /var/log/audit owned by root:root with restrictive permissions. Wrong ownership or mode can stop audit logging.",
                "next": "Verify /var/log/audit and audit.log ownership/mode before restarting auditd or changing audit rules.",
            })
        else:
            findings.append({
                "level": "YELLOW",
                "title": "auditd service issue detected",
                "detail": auditd[:300],
                "why": "auditd is not active or has failure evidence, but ownership/permission root cause was not confirmed from this report.",
                "next": "Collect auditd status, journal, and /var/log/audit ownership/mode before repair.",
            })

    media_paths = evidence.get("media_paths", "")
    media_lines = [x.strip() for x in mounts.splitlines() if x.strip()]
    path_lines = [x.strip() for x in media_paths.splitlines() if x.strip()]
    odd_media_targets = [x for x in media_lines if "/media/" in x and "-/dev/" in x]
    readonly_media = [x for x in media_lines if 'TARGET="/media/' in x and 'OPTIONS="ro,' in x]
    readonly_non_iso = [x for x in readonly_media if 'FSTYPE="iso9660"' not in x]
    appdata_line = next((x for x in path_lines if " /DATA/AppData -> " in x or "/DATA/AppData ->" in x), "")
    has_data_media = any("/DATA/.media" in x for x in path_lines)
    has_casa_media = any("/var/lib/casaos_data/.media" in x for x in path_lines)

    if odd_media_targets:
        findings.append({
            "level": "YELLOW",
            "title": "Files/AppData media mount naming issue detected",
            "detail": "\n".join(odd_media_targets[:4]),
            "why": "A media target contains an embedded device path such as -/dev/sdb. This can confuse Files app paths, AppData paths, and Docker bind paths.",
            "next": "Verify local-storage metadata and current mount names before moving AppData or editing containers.",
        })

    if readonly_non_iso:
        findings.append({
            "level": "YELLOW",
            "title": "Writable media path appears mounted read-only",
            "detail": "\n".join(readonly_non_iso[:4]),
            "why": "A non-ISO media mount is read-only. Apps may show files but fail to write, delete, upload, or update AppData.",
            "next": "Confirm filesystem health and mount options before changing permissions.",
        })

    if readonly_media and not readonly_non_iso:
        findings.append({
            "level": "INFO",
            "title": "Read-only ISO/media mount detected",
            "detail": "\n".join(readonly_media[:3]),
            "why": "Read-only iso9660 media is expected for installer/ISO-style mounts and should not be treated as a storage failure.",
            "next": "Ignore this unless the user expected the device to be writable storage.",
        })

    if appdata_line:
        findings.append({
            "level": "INFO",
            "title": "AppData symlink target detected",
            "detail": appdata_line,
            "why": "ZimaOS AppData is redirected through a symlink. App issues should verify both /DATA/AppData and the real target path.",
            "next": "Check the symlink target mount before diagnosing AppData, Files, or container volume issues.",
        })

    if not has_data_media or not has_casa_media:
        findings.append({
            "level": "YELLOW",
            "title": "ZimaOS media mirror path missing",
            "detail": media_paths[:300],
            "why": "ZimaOS normally exposes storage through /media, /DATA/.media, and /var/lib/casaos_data/.media. Missing mirror paths can cause Files app or app path confusion.",
            "next": "Verify ZimaOS local-storage state before treating this as an app problem.",
        })

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




def extract_failed_unit_name(line):
    clean = line.replace("●", " ").strip()
    for token in clean.split():
        token = token.strip()
        if re.search(r'\.(service|timer|mount|socket)$', token):
            return token
    return clean.split()[0] if clean else ""


def shell_quote(value):
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def parse_systemctl_show(text):
    props = {}
    for raw in text.splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            props[key.strip()] = value.strip()
    return props


def execstart_paths(execstart):
    paths = []
    for match in re.findall(r'(?<![\w.-])/(?:[A-Za-z0-9._@:+-]+/?)+', execstart or ""):
        p = match.rstrip(" ;,}")
        if p and p not in paths:
            paths.append(p)
    return paths


def docker_exec_tokens(execstart):
    text = execstart or ""
    m = re.search(r'argv\[\]=([^}]*)', text)
    raw = m.group(1) if m else text
    return [x.strip(" ;'\\\"") for x in raw.split() if x.strip(" ;'\\\"")]


def detect_docker_name_mismatch(execstart):
    tokens = docker_exec_tokens(execstart)
    if not tokens or not any(t.endswith("/docker") or t == "docker" for t in tokens):
        return None

    docker_verbs = {"start", "restart", "stop", "exec", "logs", "inspect"}
    target = ""

    for i, t in enumerate(tokens):
        if t in docker_verbs and i + 1 < len(tokens):
            target = tokens[i + 1]
            break

    if not target or target.startswith("-"):
        return None

    names = run_host_shell("docker ps -a --format '{{.Names}}' 2>/dev/null || true", timeout=12).splitlines()
    names = [n.strip() for n in names if n.strip()]

    if target in names:
        return None

    matches = [n for n in names if target.lower() in n.lower() or n.lower() in target.lower()]
    if matches:
        return {"old_name": target, "possible_names": matches[:5]}

    return {"old_name": target, "possible_names": []}


def related_service_name(unit):
    if not unit:
        return ""
    if unit.endswith("-watchdog.service"):
        return unit.replace("-watchdog.service", ".service")
    if unit.endswith("-delay.service"):
        return unit.replace("-delay.service", ".service")
    return ""


def related_service_state(unit):
    related = related_service_name(unit)
    if not related:
        return None

    out = run_host_shell(
        "systemctl show "
        + shell_quote(related)
        + " -p Id -p LoadState -p ActiveState -p SubState --no-pager 2>/dev/null || true",
        timeout=8,
    )
    props = parse_systemctl_show(out)
    if not props.get("Id"):
        return None

    return {
        "unit": related,
        "active": props.get("ActiveState", ""),
        "sub": props.get("SubState", ""),
        "load": props.get("LoadState", ""),
    }


def path_state(path):
    out = run_host_shell(f"test -e {shell_quote(path)} && echo EXISTS || echo MISSING", timeout=5)
    return "EXISTS" if "EXISTS" in out else "MISSING"


def build_failed_unit_finding(line):
    unit = extract_failed_unit_name(line)
    raw_line = line.strip()

    if "snapraid-sync.service" in raw_line:
        return {
            "level": "RED",
            "title": "DATA PROTECTION IS DOWN",
            "evidence": "systemctl --failed shows snapraid-sync.service failed.",
            "detail": "systemctl --failed shows snapraid-sync.service failed.",
            "why": "SnapRAID sync is not completing, so parity protection is not current.",
            "next": "Check journalctl -u snapraid-sync and fix the SnapRAID config/parity before relying on the pool.",
        }

    show = ""
    props = {}
    if unit:
        show = run_host_shell(
            "systemctl show "
            + shell_quote(unit)
            + " -p Id -p LoadState -p ActiveState -p SubState -p Result -p FragmentPath "
              "-p ExecMainStatus -p ExecMainCode -p ActiveEnterTimestamp -p InactiveEnterTimestamp -p StateChangeTimestamp -p ExecStart -p ExecStartPre -p ExecStartPost --no-pager 2>/dev/null || true",
            timeout=10,
        )
        props = parse_systemctl_show(show)

    fragment = props.get("FragmentPath", "")
    execstart = props.get("ExecStart", "")
    active = props.get("ActiveState", "")
    sub = props.get("SubState", "")
    result = props.get("Result", "")
    status = props.get("ExecMainStatus", "")
    state_change = props.get("StateChangeTimestamp", "")
    active_enter = props.get("ActiveEnterTimestamp", "")

    checked_paths = []
    missing_paths = []

    for p in ([fragment] if fragment else []) + execstart_paths(execstart):
        if not p or p in checked_paths:
            continue
        checked_paths.append(p)
        if path_state(p) == "MISSING":
            missing_paths.append(p)

    evidence_parts = [raw_line]
    if unit:
        evidence_parts.append(f"unit={unit}")
    if active or sub or result:
        evidence_parts.append(f"state={active}/{sub}, result={result}, exit={status}")
    if state_change:
        evidence_parts.append(f"failed_since={state_change}")
    elif active_enter:
        evidence_parts.append(f"active_since={active_enter}")
    if fragment:
        evidence_parts.append(f"unit_file={fragment}")
    if execstart:
        evidence_parts.append(f"exec={execstart}")
    if checked_paths:
        evidence_parts.append("checked_paths=" + ", ".join(checked_paths))
    if missing_paths:
        evidence_parts.append("missing_paths=" + ", ".join(missing_paths))

    title = "Failed systemd unit detected"
    why = "A failed host unit can indicate a broken scheduled task or system helper."
    next_step = "Inspect only this failed unit before changing unrelated services."

    docker_mismatch = detect_docker_name_mismatch(execstart)
    related_state = related_service_state(unit)

    missing_os_paths = [
        p for p in missing_paths
        if p.startswith(("/usr/libexec/", "/usr/lib/systemd/", "/usr/bin/", "/usr/sbin/", "/lib/systemd/"))
    ]
    missing_data_paths = [p for p in missing_paths if p.startswith("/DATA/")]

    if missing_os_paths:
        title = "Possible ZimaOS packaging regression"
        why = "The failed unit references an OS-managed helper or executable that is missing from the host image."
        next_step = "Verify the ZimaOS version and failed unit evidence before treating this as local configuration damage."
    elif missing_data_paths:
        title = "Failed systemd unit references missing local AppData/DATA path"
        why = "The unit points to a local /DATA path that is not present on the host."
        next_step = "Verify whether the path was removed, moved, or belongs to an obsolete local service before changing anything."
    elif missing_paths:
        title = "Failed systemd unit references missing file/path"
        why = "The unit points to a file or path that is not present on the host."
        next_step = "Verify the missing path and whether the unit is obsolete before changing services."
    elif docker_mismatch:
        title = "Failed systemd unit may reference old Docker container name"
        evidence_parts.append("docker_reference=" + docker_mismatch["old_name"])
        if docker_mismatch.get("possible_names"):
            evidence_parts.append("possible_current_container=" + ", ".join(docker_mismatch["possible_names"]))
        why = "The unit appears to call Docker with a container name that does not exist, while a similar current container name may exist."
        next_step = "Verify the service file container name against docker ps -a before restarting or editing the unit."
    elif related_state and related_state.get("active") == "active":
        title = "Failed watchdog/helper unit, but related service is running"
        evidence_parts.append(
            "related_service="
            + related_state["unit"]
            + " "
            + related_state.get("active", "")
            + "/"
            + related_state.get("sub", "")
        )
        why = "The failed unit appears to be a helper/watchdog, while the main related service is currently active."
        next_step = "Verify whether the helper failure is historical before restarting the main service."
    elif unit and "cron" in (unit + " " + execstart).lower():
        cron_ps = run_host_shell("ps -ef | grep -E '[c]rond|[c]ron' || true", timeout=8)
        if cron_ps.strip():
            title = "Failed systemd unit, but related cron process is running"
            evidence_parts.append("related_process=cron/crond process currently exists")
            why = "This may be a historical failed helper or duplicate cron unit rather than a current cron outage."
            next_step = "Verify whether this old cron-fix unit is still required before changing or disabling it."

    evidence = " | ".join(evidence_parts)

    return {
        "level": "YELLOW",
        "title": title,
        "evidence": evidence,
        "detail": evidence,
        "why": why,
        "next": next_step,
    }


def collect_critical_verifier():
    findings = []
    facts = []

    failed_units = run_host_shell("systemctl --failed --plain --no-pager --no-legend 2>/dev/null || true")
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
                findings.append(build_failed_unit_finding(line))

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
