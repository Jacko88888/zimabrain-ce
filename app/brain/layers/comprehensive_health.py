import os
import re

from brain import health_memory
from brain.layers import host_hardware_metrics
from brain.layers import trend_alerts


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


def _lines(value):
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def _unique(values):
    result = []
    seen = set()
    for value in values:
        value = " ".join(str(value or "").split())
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _docker_states(text):
    rows = []
    for line in _lines(text):
        parts = line.split("|", 6)
        if len(parts) < 5:
            continue
        try:
            restart_count = int(parts[4] or 0)
        except ValueError:
            restart_count = 0
        rows.append({
            "name": parts[0].lstrip("/"),
            "image": parts[1],
            "state": parts[2].lower(),
            "health": parts[3].lower(),
            "restart_count": restart_count,
        })
    return rows


def _failed_units(text):
    result = []
    for line in _lines(text):
        low = line.lower()
        if "0 loaded units listed" in low or "no units listed" in low:
            continue
        result.append(line)
    return result


def _port_counts(text):
    counts = {
        "lan_open": 0,
        "localhost_only": 0,
        "closed_or_unknown": 0,
    }
    for line in _lines(text):
        if line.startswith("HOST_LAN_IP="):
            continue
        if "|localhost=open|" in line and "|lan=open|" in line:
            counts["lan_open"] += 1
        elif "|localhost=open|" in line and "|lan=closed|" in line:
            counts["localhost_only"] += 1
        else:
            counts["closed_or_unknown"] += 1
    return counts


def _timeline():
    if not os.path.exists(TREND_DB_PATH):
        return None, [], [], [], {}, {}

    try:
        scan = health_memory.latest_scan(TREND_DB_PATH)
        if not scan:
            return None, [], [], [], {}, {}

        events = health_memory.latest_events(TREND_DB_PATH, limit=500)
        actionable = [event for event in events if trend_alerts._actionable(event)]
        historical = [
            event for event in events
            if event.get("classification") == "historical_stable"
        ]
        recovered = [
            event for event in events
            if event.get("classification") == "recovered"
        ]
        drift = health_memory.configuration_drift_history(
            TREND_DB_PATH, limit=10
        )
        updates = health_memory.system_update_history(
            TREND_DB_PATH, limit=10
        )
        return scan, actionable, historical, recovered, drift, updates
    except Exception:
        return None, [], [], [], {}, {}


def answer(bundle):
    evidence = bundle.get("same_report_evidence", {}) or {}
    critical = bundle.get("critical_findings", []) or []
    host = host_hardware_metrics._summary(bundle)

    containers = _docker_states(evidence.get("docker_states", ""))
    running = [row for row in containers if row["state"] == "running"]
    exited = [row for row in containers if row["state"] == "exited"]
    restarting = [row for row in containers if row["state"] == "restarting"]
    unhealthy = [
        row for row in containers
        if row["state"] == "running" and row["health"] == "unhealthy"
    ]

    failed_units = _failed_units(evidence.get("failed_units", ""))
    mount_lines = _lines(evidence.get("mounts", ""))
    lsblk_lines = _lines(evidence.get("lsblk", ""))
    path_lines = _lines(evidence.get("path_state", ""))

    readonly_mounts = [
        line for line in mount_lines
        if (
            'OPTIONS="ro,' in line or 'OPTIONS="ro"' in line
        )
        and 'FSTYPE="iso9660"' not in line
        and (
            'TARGET="/DATA' in line
            or 'TARGET="/media/' in line
            or 'TARGET="/var/lib/casaos_data/.media' in line
        )
    ]
    missing_paths = [line for line in path_lines if "present=0" in line]

    smart_raw = str(evidence.get("smart", "") or "")
    nvme_raw = str(evidence.get("nvme_smart", "") or "")
    smart_devices = smart_raw.count("===== SMART ")
    nvme_devices = nvme_raw.count("===== NVME ")

    smart_failed = (
        "overall-health self-assessment test result: failed" in smart_raw.lower()
        or "smart health status: failed" in smart_raw.lower()
    )

    nvme_critical = []
    for line in _lines(nvme_raw):
        if "critical_warning" not in line.lower():
            continue
        match = re.search(r"critical_warning\s*[:=]\s*(\S+)", line, re.I)
        value = match.group(1).lower() if match else ""
        if value not in {"", "0", "0x0", "0x00", "false"}:
            nvme_critical.append(line)

    ports = _port_counts(evidence.get("port_reachability", ""))
    zfw = str(evidence.get("zfw_status", "") or "").strip()
    audit_lines = _lines(evidence.get("auditd", ""))
    audit_state = audit_lines[0] if audit_lines else "not captured"

    docker_security = _lines(evidence.get("docker_security", ""))
    privileged_count = sum(
        1 for line in docker_security if "Privileged=true" in line
    )
    docker_socket_count = sum(
        1 for line in docker_security if "DockerSock=" in line
    )

    scan, timeline_actionable, historical, recovered, drift, updates = _timeline()

    actionable = []

    for finding in critical:
        if finding.get("level") not in {"RED", "YELLOW"}:
            continue
        detail = finding.get("detail") or finding.get("evidence") or ""
        actionable.append(
            f"{finding.get('level')}: {finding.get('title', 'Local finding')} — {detail}"
        )

    restart_names = {row["name"] for row in restarting}
    failed_unit_names = {
        unit.lstrip("● ").split()[0]
        for unit in failed_units
        if unit.lstrip("● ").split()
    }

    for row in restarting:
        comparison = next(
            (
                event.get("message", "")
                for event in timeline_actionable
                if event.get("category") == "container"
                and event.get("entity_name") == row["name"]
                and event.get("metric") == "restart_count"
            ),
            "",
        )
        message = (
            f"{row['name']} is currently restarting; current captured restart "
            f"count: {row['restart_count']}."
        )
        if comparison:
            message += f" Latest stored comparison: {comparison}"
        actionable.append(message)

    for event in timeline_actionable:
        entity = event.get("entity_name", "")
        if entity in restart_names:
            continue
        if event.get("category") == "service" and entity in failed_unit_names:
            continue
        actionable.append(event.get("message", ""))

    for row in unhealthy:
        actionable.append(
            f"{row['name']} is running but currently reports unhealthy."
        )

    critical_text = " ".join(actionable).lower()
    for unit in failed_units:
        unit_name = unit.lstrip("● ").split()[0]
        if unit_name.lower() not in critical_text:
            actionable.append(f"Failed unit: {unit}")

    for line in readonly_mounts:
        actionable.append(f"Read-only writable-storage candidate: {line}")

    for line in missing_paths:
        actionable.append(f"Expected fixed path is missing: {line}")

    if smart_failed:
        actionable.append("A SMART overall-health failure marker was captured.")

    for line in nvme_critical:
        actionable.append(f"NVMe critical warning: {line}")

    if zfw and zfw != "active":
        actionable.append(f"Firewall status requires attention: ZFW is {zfw}.")

    actionable = _unique(actionable)

    red = any(finding.get("level") == "RED" for finding in critical)
    if smart_failed or nvme_critical:
        red = True

    if red:
        severity = "RED"
        conclusion = "one or more current high-risk conditions require immediate evidence-led review"
    elif actionable:
        severity = "YELLOW"
        conclusion = "the system is operating, but current conditions require attention"
    else:
        severity = "GREEN"
        conclusion = "no current actionable condition was detected in the captured evidence"

    current_drift = drift.get("current", {}) if isinstance(drift, dict) else {}
    drift_items = drift.get("drifts", []) if isinstance(drift, dict) else []
    current_scan_id = scan.get("id") if scan else None
    current_drift_attention = [
        item for item in drift_items
        if item.get("severity") == "attention"
        and item.get("to_scan") == current_scan_id
    ]

    update_current = updates.get("current", {}) if isinstance(updates, dict) else {}
    update_transitions = (
        updates.get("transitions", []) if isinstance(updates, dict) else []
    )

    lines = []
    lines.append(f"- Overall severity: {severity} — {conclusion}.")
    lines.append(
        f"- Current actionable findings: {len(actionable)}; "
        f"historical stable values: {len(historical)}; "
        f"recovered signals: {len(recovered)}."
    )
    lines.append("")

    lines.append("#### Current actionable findings")
    if actionable:
        for item in actionable[:25]:
            lines.append(f"- {item}")
        if len(actionable) > 25:
            lines.append(
                f"- {len(actionable) - 25} additional actionable item(s) remain "
                "stored in the local evidence."
            )
    else:
        lines.append("- None detected in the current report and latest comparison.")
    lines.append("")

    lines.append("#### CPU, load, Memory and Swap")
    lines.append(f"- CPU: {host['model']}")
    lines.append(f"- CPU usage snapshot: {host['cpu_usage']}")
    lines.append(f"- Load average 1/5/15 min: {host['load']}")
    lines.append(f"- Memory: {host['memory']}")
    lines.append(f"- Swap: {host['swap']}")
    lines.append(f"- Maximum captured temperature: {host['max_temp']}")
    lines.append(f"- Temperature interpretation: {host['temp_status']}")
    lines.append("")

    lines.append("#### Filesystems, mounts and storage")
    lines.append(f"- Filesystems/lsblk lines captured: {len(lsblk_lines)}")
    lines.append(f"- Relevant active mount lines captured: {len(mount_lines)}")
    lines.append(
        f"- Writable-storage mounts unexpectedly read-only: {len(readonly_mounts)}"
    )
    lines.append(f"- Expected fixed paths currently missing: {len(missing_paths)}")
    for line in readonly_mounts[:5]:
        lines.append(f"- Read-only evidence: {line}")
    for line in missing_paths[:5]:
        lines.append(f"- Missing-path evidence: {line}")
    lines.append("")

    lines.append("#### SMART and NVMe")
    lines.append(f"- SMART devices captured: {smart_devices}")
    lines.append(
        "- SMART overall-health failure marker: "
        + ("detected" if smart_failed else "not detected")
    )
    lines.append(f"- NVMe devices captured: {nvme_devices}")
    lines.append(f"- NVMe non-zero critical-warning lines: {len(nvme_critical)}")
    lines.append("")

    lines.append("#### Containers and restart loops")
    lines.append(f"- Containers inspected: {len(containers)}")
    lines.append(f"- Running: {len(running)}")
    lines.append(f"- Exited: {len(exited)}")
    lines.append(f"- Restarting: {len(restarting)}")
    lines.append(f"- Unhealthy: {len(unhealthy)}")
    if restarting:
        for row in restarting[:10]:
            lines.append(
                f"- Restart loop: {row['name']} — restart count "
                f"{row['restart_count']}."
            )
    lines.append(
        "- Exited containers are listed as inactive evidence; intent must be "
        "verified before treating every exited container as a fault."
    )
    lines.append("")

    lines.append("#### Services and Failed units")
    if failed_units:
        for unit in failed_units[:20]:
            lines.append(f"- {unit}")
    else:
        lines.append("- No failed host unit was captured.")
    lines.append("")

    lines.append("#### Network exposure, Firewall and audit posture")
    lines.append(f"- LAN-reachable published ports: {ports['lan_open']}")
    lines.append(f"- Localhost-only or LAN-blocked ports: {ports['localhost_only']}")
    lines.append(
        f"- Closed or unclassified reachability rows: "
        f"{ports['closed_or_unknown']}"
    )
    lines.append(f"- Firewall/ZFW status: {zfw or 'not captured'}")
    lines.append(f"- auditd status: {audit_state}")
    lines.append(f"- Privileged containers: {privileged_count}")
    lines.append(f"- Containers with Docker-socket access: {docker_socket_count}")
    lines.append(
        "- LAN reachability does not by itself prove or disprove public internet exposure."
    )
    lines.append("")

    lines.append("#### Configuration drift and update correlation")
    if current_drift:
        lines.append(
            "- Current posture: "
            f"{current_drift.get('paths_missing', 0)} missing path(s); "
            f"{current_drift.get('mounts_missing', 0)} missing mount(s); "
            f"{current_drift.get('lan_open_ports', 0)} LAN-open port(s); "
            f"{current_drift.get('privileged_containers', 0)} privileged "
            "container(s); "
            f"{current_drift.get('docker_socket_containers', 0)} Docker-socket "
            "container(s)."
        )
    else:
        lines.append("- No comparable configuration-drift baseline is available.")

    if current_drift_attention:
        for item in current_drift_attention[:10]:
            lines.append(f"- Drift requiring attention: {item.get('message', '')}")
    else:
        lines.append("- No new attention-level configuration drift was detected.")

    if update_current:
        lines.append(
            "- Current recorded update baseline: "
            f"release={update_current.get('os_version', 'not captured')}; "
            f"build={update_current.get('build_date', 'not captured')}; "
            f"kernel={update_current.get('kernel', 'not captured')}; "
            f"slot={update_current.get('rauc_booted_slot', 'not captured')}."
        )
    else:
        lines.append("- No update baseline is available.")

    if update_transitions:
        for item in update_transitions[:5]:
            lines.append(f"- Update transition: {item.get('message', '')}")
    else:
        lines.append(
            "- No recorded OS/build/kernel/RAUC transition currently proves "
            "update correlation."
        )
    lines.append("")

    lines.append("#### Historical and stable information")
    if historical:
        for event in historical[:20]:
            lines.append(f"- {event.get('message', '')}")
    else:
        lines.append("- No unchanged historical warning value was recorded.")
    lines.append("")

    lines.append("#### Honest limitations")
    lines.append("- CPU, load, temperature and process values are point-in-time snapshots.")
    lines.append(
        "- SMART/NVMe failure-marker checks do not replace full vendor diagnostics."
    )
    lines.append(
        "- Restarting-container state is verified, but its root cause requires "
        "the container's recent logs and configuration."
    )
    lines.append(
        "- Persistent exited containers may be intentionally stopped and are "
        "not automatically classified as current failures."
    )

    if restarting:
        first = restarting[0]["name"]
        next_step = (
            f"Inspect {first}'s recent logs and exit reason first, then inspect "
            "the confirmed failed host unit separately. Do not recreate containers "
            "or change mounts until those two causes are verified."
        )
    elif failed_units:
        next_step = (
            "Inspect the confirmed failed host unit and its recent journal first. "
            "Do not change unrelated containers, mounts, or disks."
        )
    elif actionable:
        next_step = (
            "Review the first current actionable finding and verify its exact "
            "evidence before changing configuration."
        )
    else:
        next_step = (
            "No immediate repair is indicated. Keep the current configuration "
            "and compare the next scan for new or worsening signals."
        )

    forum_summary = (
        f"ZimaBrain verified a whole-system assessment from current local evidence: "
        f"severity {severity}, {len(actionable)} actionable finding(s), "
        f"{len(historical)} stable historical value(s), {len(restarting)} "
        "restart loop(s), and "
        f"{len(failed_units)} failed host unit line(s)."
    )

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
        "trust_state": "VERIFIED",
        "trust_title": "✅ VERIFIED FROM CURRENT REPORT AND LOCAL HEALTH TIMELINE",
        "trust_detail": (
            "This whole-system assessment uses the current same-report host evidence "
            "and the latest local health comparison. Missing evidence is stated as a "
            "limitation rather than inferred."
        ),
    }
