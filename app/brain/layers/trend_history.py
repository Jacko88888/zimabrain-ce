import os

from brain import health_memory


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


def is_trend_question(question):
    q = (question or "").lower()
    return any(x in q for x in [
        "trend history", "trend snapshot", "trend snapshots",
        "snapshot history", "port and smart trend", "smart trend history",
        "port trend history", "what changed since the last scan",
        "what changed from last scan", "what changed since my previous scan",
        "compare last scan", "compare trend", "health timeline",
        "historical warning", "getting worse",
        "path drift", "mount drift", "security drift",
        "security posture changed", "security posture change",
        "network exposure changed", "network exposure change",
        "what ports changed", "appdata path changed",
    ])


def _group(events):
    grouped = {}
    for event in events:
        grouped.setdefault(event["classification"], []).append(event)
    return grouped


def _add_items(out, title, items, empty_text=None, limit=20):
    out.append(f"#### {title}")
    if items:
        for item in items[:limit]:
            out.append(f"- {item['message']}")
        if len(items) > limit:
            out.append(f"- {len(items) - limit} additional item(s) are stored in the local timeline.")
    elif empty_text:
        out.append(f"- {empty_text}")
    out.append("")


def _state_sequence(states):
    labels = {
        "running": "✔ Running",
        "exited": "✖ Exited",
        "restarting": "↻ Restarting",
        "dead": "✖ Dead",
        "paused": "Ⅱ Paused",
        "created": "○ Created",
    }
    return " → ".join(labels.get((state or "unknown").lower(), f"? {state}") for state in states)


def _service_state_sequence(states):
    labels = {
        "active/running": "✔ Active",
        "active/exited": "✔ Active",
        "failed/failed": "✖ Failed",
        "inactive/dead": "○ Inactive",
        "activating/start": "… Activating",
    }
    return " → ".join(
        labels.get((state or "unknown/unknown").lower(), f"? {state}")
        for state in states
    )


def _io_rate_sequence(rates):
    return " → ".join(
        f"● {float(rate):.1f} kB/s" if float(rate or 0) > 0
        else "○ Not observed"
        for rate in rates
    )


def answer(question, bundle):
    scan = health_memory.latest_scan(TREND_DB_PATH) if os.path.exists(TREND_DB_PATH) else None
    events = health_memory.latest_events(TREND_DB_PATH, limit=500) if scan else []
    scans = health_memory.recent_scans(TREND_DB_PATH, limit=8) if scan else []
    container_histories = health_memory.container_state_histories(
        TREND_DB_PATH, limit=10
    ) if scan else []
    io_histories = health_memory.disk_io_process_histories(
        TREND_DB_PATH, limit=10
    ) if scan else []
    update_history = health_memory.system_update_history(
        TREND_DB_PATH, limit=10
    ) if scan else {"current": {}, "transitions": []}
    drift_history = health_memory.configuration_drift_history(
        TREND_DB_PATH, limit=10
    ) if scan else {"current": {}, "drifts": [], "scan_count": 0}
    service_histories = health_memory.service_boot_histories(
        TREND_DB_PATH, limit=20
    ) if scan else []
    helper_correlations = health_memory.helper_service_correlations(
        TREND_DB_PATH, limit=20
    ) if scan else []
    grouped = _group(events)
    q = str(question or "").lower()
    disk_trend_focus = any(
        term in q
        for term in (
            "smart", "nvme", "crc", "media-error", "media error",
            "unsafe-shutdown", "unsafe shutdown", "disk counter",
            "drive counter",
        )
    )
    update_focus = (
        any(
            term in q
            for term in ("update", "updated", "upgrade", "zimaos")
        )
        and any(
            term in q
            for term in (
                "after", "changed", "change", "compare",
                "baseline", "since", "regression", "problem",
            )
        )
    )

    out = [
        "### ZimaBrain Answer", "", "## ❓ Question asked",
        f"### {question.strip()}", "", "#### Verification status",
    ]
    if scan and events:
        out.extend([
            "@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM LOCAL HEALTH TIMELINE",
            "- This answer compares individually identified local health signals.",
        ])
    else:
        out.extend([
            "@@VERIFY:NOT VERIFIED@@ ❌ NOT VERIFIED",
            "- No detailed health-memory scan exists yet.",
        ])
    out.extend([
        "- Active layer: Health Timeline and Local Memory Layer",
        "- Layer files: `app/brain/health_memory.py`, `app/brain/layers/trend_history.py`",
        "", "#### Direct answer / severity",
    ])

    if not scan or not events:
        out.extend([
            "- No detailed local timeline is available yet.", "",
            "#### Next safest step",
            "- Run one ZimaBrain scan, then ask this question again.", "",
            "#### Forum-ready summary",
            "ZimaBrain has not recorded a detailed local health timeline yet.",
        ])
        return "\n".join(out)

    worsening = grouped.get("worsening", [])
    new_issues = grouped.get("new_issue", [])
    persistent = grouped.get("persistent", [])
    recovered = grouped.get("recovered", [])
    historical = grouped.get("historical_stable", [])
    changed = grouped.get("changed", []) + grouped.get("counter_reset", [])

    disk_events = [
        event for event in events
        if event.get("category") in {"smart", "nvme"}
    ]
    increased_disk_events = [
        event for event in disk_events
        if event.get("classification") in {"worsening", "new_issue"}
    ]

    if increased_disk_events:
        disk_trend_assessment = (
            f"{len(increased_disk_events)} tracked SMART/NVMe signal(s) "
            "increased or became newly actionable in the latest scan."
        )
    elif disk_events:
        disk_trend_assessment = (
            "No tracked SMART/NVMe error counter increased in the latest "
            "comparison."
        )
    else:
        disk_trend_assessment = (
            "No comparable SMART/NVMe counter history was recorded."
        )

    if disk_trend_focus:
        out.extend([
            f"- Latest detailed scan: #{scan['id']} `{scan['created_at']}`",
            f"- SMART/NVMe trend assessment: {disk_trend_assessment}",
            "",
            "#### Relevant SMART/NVMe changes",
        ])

        relevant = [
            event for event in disk_events
            if event.get("classification") in {
                "worsening", "new_issue", "recovered", "counter_reset"
            }
        ]

        if relevant:
            for event in relevant[:20]:
                out.append(f"- {event['message']}")
        else:
            out.append(
                "- No new, worsening, recovered, or reset SMART/NVMe "
                "counter transition was recorded."
            )

        out.extend([
            "",
            "#### Next safest step",
            "- Act on a disk counter only when it increases, becomes newly "
            "actionable, or combines with current SMART/NVMe failure evidence.",
            "",
            "#### Forum-ready summary",
            f"SMART/NVMe timeline result: {disk_trend_assessment}",
        ])
        return "\n".join(out)

    if update_focus:
        current_release = update_history.get("current", {})
        transitions = update_history.get("transitions", [])

        if transitions:
            latest = transitions[0]
            issues = latest.get("issues", [])
            recoveries = latest.get("recoveries", [])

            if issues:
                assessment = (
                    f"A recorded system transition coincides with "
                    f"{len(issues)} new or worsening signal(s), but timing "
                    "alone does not prove the update caused them."
                )
            elif recoveries:
                assessment = (
                    "A recorded system transition coincides with recovery "
                    "signals and no captured new/worsening signal."
                )
            else:
                assessment = (
                    "A system transition was recorded without a captured "
                    "new, worsening, or recovered health signal."
                )
        else:
            assessment = (
                "No recorded ZimaOS version, build, kernel, or RAUC-slot "
                "transition is available, so an update regression cannot "
                "be established from the timeline."
            )

        out.extend([
            f"- Update comparison assessment: {assessment}",
            "",
            "#### ZimaOS update / regression timing",
        ])

        if current_release:
            out.append(
                "- Current recorded release: "
                f"ZimaOS {current_release.get('os_version', 'unknown')}; "
                f"build {current_release.get('build_date', 'unknown')}; "
                f"kernel {current_release.get('kernel', 'unknown')}; "
                f"slot {current_release.get('rauc_booted_slot', 'unknown')}."
            )

        if transitions:
            for transition in transitions[:5]:
                changes = "; ".join(
                    f"{item['label']}: "
                    f"{item['previous']} → {item['current']}"
                    for item in transition.get("changes", [])
                )
                out.append(
                    f"- Scan #{transition['scan_id']} "
                    f"`{transition['created_at']}`: {changes}"
                )

                for issue in transition.get("issues", [])[:5]:
                    out.append(
                        f"  New/worsening signal: {issue['message']}"
                    )

                for recovery in transition.get("recoveries", [])[:5]:
                    out.append(
                        f"  Recovery signal: {recovery['message']}"
                    )

                out.append(
                    f"  Important: "
                    f"{transition.get('causality_note', '')}"
                )
        else:
            out.append("- No comparable update transition was recorded.")

        out.extend([
            "",
            "#### Next safest step",
            "- Compare the first affected scan with the recorded release, "
            "kernel, slot, and exact new/worsening signals before "
            "attributing the problem to an update.",
            "",
            "#### Forum-ready summary",
            f"Update timeline result: {assessment}",
        ])
        return "\n".join(out)

    out.extend([
        f"- Latest detailed scan: #{scan['id']} `{scan['created_at']}`",
        f"- Individually tracked observations: {scan['observation_count']}",
        f"- Worsening signals: {len(worsening)}",
        f"- New issues: {len(new_issues)}",
        f"- Persistent issue states: {len(persistent)}",
        f"- Recovered signals: {len(recovered)}",
        f"- Historical values with no increase: {len(historical)}",
    ])
    if disk_trend_focus:
        out.append(
            f"- SMART/NVMe trend assessment: {disk_trend_assessment}"
        )
    out.append("")

    _add_items(out, "Worsening conditions", worsening,
               "No tracked counter increased since the previous scan.")
    _add_items(out, "New issues", new_issues,
               "No new issue state was detected.")
    _add_items(out, "Recovered or temporary interruptions", recovered,
               "No recovery transition was detected in this scan.")
    _add_items(out, "Historical and stable values", historical,
               "No unchanged non-zero historical counters were found.")
    _add_items(out, "Other verified changes", changed,
               "No other tracked value changed.")

    out.append("#### Persistent states")
    if persistent:
        for item in persistent[:20]:
            if item["category"] == "container" and item["metric"] == "state" and item.get("current_text") == "exited":
                out.append(f"- {item['entity_name']} remains exited. This is persistent inactivity, but it may be intentional.")
            else:
                out.append(f"- {item['message']}")
    else:
        out.append("- No issue remained active across consecutive scans.")
    out.append("")

    out.append(
        "#### Path, network and security drift — last 10 reports"
    )
    drift_current = drift_history.get("current", {})
    if drift_current:
        out.append(
            "- Current posture: "
            f"{drift_current.get('paths_tracked', 0)} fixed path(s) tracked; "
            f"{drift_current.get('paths_missing', 0)} missing path(s); "
            f"{drift_current.get('mounts_missing', 0)} missing mount(s); "
            f"{drift_current.get('lan_open_ports', 0)} LAN-open port(s); "
            f"{drift_current.get('privileged_containers', 0)} privileged "
            "container(s); "
            f"{drift_current.get('docker_socket_containers', 0)} container(s) "
            "with Docker-socket access; "
            f"ZFW {drift_current.get('zfw_state', 'unknown')}; "
            f"auditd {drift_current.get('auditd_state', 'unknown')}."
        )

    drift_items = drift_history.get("drifts", [])
    if drift_items:
        for item in drift_items[:30]:
            badge = {
                "attention": "⚠ Attention",
                "recovery": "✔ Recovery",
                "information": "ℹ Information",
            }.get(item["severity"], "ℹ Information")
            out.append(
                f"- {badge} — scan #{item['to_scan']} "
                f"`{item['created_at']}`: {item['message']}"
            )
            out.append(
                f"  Status: "
                f"{item['classification'].replace('_', ' ').title()}."
            )
    else:
        out.append(
            "- No comparable path, mount, network-exposure, firewall, audit, "
            "privilege, or Docker-socket drift was found."
        )
        if drift_history.get("scan_count", 0) < 2:
            out.append(
                "- One baseline scan exists; a second scan is required for "
                "drift comparison."
            )
    out.append("")

    out.append("#### ZimaOS update / regression timing")
    current_release = update_history.get("current", {})
    if current_release:
        out.append(
            "- Current recorded release: "
            f"ZimaOS {current_release.get('os_version', 'unknown')}; "
            f"build {current_release.get('build_date', 'unknown')}; "
            f"kernel {current_release.get('kernel', 'unknown')}; "
            f"slot {current_release.get('rauc_booted_slot', 'unknown')}."
        )

    transitions = update_history.get("transitions", [])
    if transitions:
        for transition in transitions[:10]:
            changes = "; ".join(
                f"{item['label']}: {item['previous']} → {item['current']}"
                for item in transition["changes"]
            )
            out.append(
                f"- Scan #{transition['scan_id']} "
                f"`{transition['created_at']}`: {changes}"
            )
            out.append(
                f"  Status: "
                f"{transition['classification'].replace('_', ' ').title()}. "
                f"{transition['assessment']}"
            )
            for issue in transition["issues"][:5]:
                out.append(
                    f"  New/worsening signal: {issue['message']}"
                )
            for recovery in transition["recoveries"][:5]:
                out.append(
                    f"  Recovery signal: {recovery['message']}"
                )
            out.append(f"  Important: {transition['causality_note']}")
    else:
        out.append(
            "- No recorded ZimaOS version, build, kernel, or RAUC-slot "
            "transition exists yet. Current values are retained as the baseline."
        )
    out.append("")

    out.append("#### Disk I/O process history — last 10 reports")
    if io_histories:
        for item in io_histories[:20]:
            out.append(
                f"- {item['entity_name']}: "
                f"{_io_rate_sequence(item['rates'])}"
            )
            out.append(
                f"  Status: "
                f"{item['classification'].replace('_', ' ').title()}. "
                f"{item['message']}"
            )
            if item["current_rate"] > 0:
                out.append(
                    f"  Current captured rate: "
                    f"{item['current_rate']:.2f} kB/s."
                )
    else:
        out.append(
            "- No interval-based per-process disk I/O has been recorded yet."
        )
    out.append("")

    out.append("#### Container history — last 10 reports")
    interesting_histories = [
        item for item in container_histories
        if item["classification"] != "stable"
    ]
    stable_histories = [
        item for item in container_histories
        if item["classification"] == "stable"
    ]
    if interesting_histories:
        for item in interesting_histories[:20]:
            out.append(
                f"- {item['entity_name']}: {_state_sequence(item['states'])}"
            )
            out.append(
                f"  Status: {item['classification'].replace('_', ' ').title()}. "
                f"{item['message']}"
            )
    else:
        out.append("- No container interruption was found in the available history.")
    if stable_histories:
        out.append(
            f"- {len(stable_histories)} container(s) remained running in every "
            "available report."
        )
    out.append("")

    out.append("#### Service history — last 20 distinct boots")
    service_issues = [
        item for item in service_histories
        if item["classification"] != "stable"
    ]
    stable_services = [
        item for item in service_histories
        if item["classification"] == "stable"
    ]
    if service_issues:
        for item in service_issues[:20]:
            out.append(
                f"- {item['entity_name']}: {_service_state_sequence(item['states'])}"
            )
            out.append(
                f"  Status: {item['classification'].replace('_', ' ').title()}. "
                f"{item['message']}"
            )
    else:
        out.append("- No failed service state was found in the recorded boot history.")
    if stable_services:
        out.append(
            f"- {len(stable_services)} service(s) had no failed state across the "
            "available distinct boots."
        )
    out.append("")

    out.append("#### Helper and primary-service correlation")
    helper_issues = [
        item for item in helper_correlations
        if item["classification"] != "stable_pair"
    ]
    if helper_issues:
        for item in helper_issues[:20]:
            out.append(f"- {item['message']}")
            out.append(
                f"  Status: {item['classification'].replace('_', ' ').title()}."
            )
    else:
        out.append(
            "- No failed watchdog/delay helper with a related primary service was "
            "found in the available boot history."
        )
    out.append("")

    out.append("#### Recent detailed scans")
    for item in scans:
        out.append(
            f"- #{item['id']} `{item['created_at']}` "
            f"version={item['app_version']} observations={item['observation_count']}"
        )
    out.extend([
        "", "#### Next safest step",
        "- Review worsening and new issues first. Historical values require action only if they increase or combine with current faults.",
        "", "#### Forum-ready summary",
        "ZimaBrain compared individually identified disk, NVMe, container, service, mount, network and performance signals against its previous local scan. Historical values are separated from worsening, persistent and recovered conditions.",
    ])
    return "\n".join(out)
