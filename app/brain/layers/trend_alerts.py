import os
import sqlite3

TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


def is_alert_question(question):
    q = (question or "").lower()
    return any(x in q for x in [
        "trend alert",
        "trend alerts",
        "any alerts",
        "do i have alerts",
        "do i have any alerts",
        "proactive alert",
        "proactive alerts",
        "alert me",
        "drift alert",
        "drift alerts",
        "port alert",
        "smart alert",
        "nvme alert",
        "what should alert",
        "anything changed dangerously",
    ])


def _read_rows(limit=2):
    if not os.path.exists(TREND_DB_PATH):
        return []

    with sqlite3.connect(TREND_DB_PATH, timeout=5) as con:
        con.row_factory = sqlite3.Row
        return list(con.execute("""
            SELECT
              id,
              created_at,
              app_version,
              running_containers,
              published_ports,
              lan_reachable_ports,
              localhost_only_ports,
              possible_blocked_ports,
              smart_warning_markers,
              nvme_warning_markers
            FROM trend_snapshots
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)))


def _delta(latest, previous, key):
    return int(latest[key]) - int(previous[key])


def _fmt_delta(value):
    if value > 0:
        return f"+{value}"
    return str(value)


def _analyse(latest, previous):
    alerts = []
    stable = []

    checks = [
        ("Published ports", "published_ports", "increase", "A new published port may expose another service."),
        ("LAN reachable ports", "lan_reachable_ports", "increase", "A new LAN reachable port may increase network exposure."),
        ("Possible blocked ports", "possible_blocked_ports", "increase", "A port that was reachable locally but not on LAN may indicate firewall, ZFW, bind, VLAN, or routing drift."),
        ("SMART warning markers", "smart_warning_markers", "increase", "More SMART warning markers may mean disk health risk or reduced SMART visibility."),
        ("NVMe warning markers", "nvme_warning_markers", "increase", "More NVMe warning markers may mean increasing NVMe risk or error count drift."),
        ("Running containers", "running_containers", "change", "Container count changed since the previous scan."),
    ]

    for label, key, mode, why in checks:
        d = _delta(latest, previous, key)

        if mode == "increase" and d > 0:
            alerts.append(f"{label}: {_fmt_delta(d)}. {why}")
        elif mode == "change" and d != 0:
            alerts.append(f"{label}: {_fmt_delta(d)}. {why}")
        else:
            stable.append(f"{label}: {_fmt_delta(d)}")

    return alerts, stable


def answer(question, bundle):
    rows = _read_rows(limit=2)

    out = []
    out.append("### ZimaBrain Answer")
    out.append("")
    out.append("## ❓ Question asked")
    out.append(f"### {question.strip()}")
    out.append("")
    out.append("#### Verification status")

    if len(rows) >= 2:
        out.append("@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM LOCAL TREND DATABASE")
        out.append("- This alert check compares the latest two SQLite trend snapshots.")
    elif len(rows) == 1:
        out.append("@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED")
        out.append("- Only one trend snapshot exists, so ZimaBrain cannot compare drift yet.")
    else:
        out.append("@@VERIFY:NOT VERIFIED@@ ❌ NOT VERIFIED")
        out.append("- No trend snapshots were found yet.")

    out.append("- Active layer: Trend Alert Layer")
    out.append("- Layer file: `app/brain/layers/trend_alerts.py`")
    out.append("")

    out.append("#### Direct answer / severity")

    if len(rows) < 1:
        out.append("- No proactive trend alert check can be made yet because no snapshots exist.")
        out.append("")
        out.append("#### Next safest step")
        out.append("- Run or refresh ZimaBrain once so it records a trend snapshot, then ask again.")
        out.append("")
        out.append("#### Forum-ready summary")
        out.append("ZimaBrain proactive trend alerts need at least two saved snapshots before drift can be verified.")
        return "\n".join(out)

    latest = rows[0]
    previous = rows[1] if len(rows) > 1 else None

    if not previous:
        out.append("- One trend snapshot exists, but no previous scan exists for comparison.")
        out.append("")
        out.append("#### Latest alert baseline")
        out.append(f"- Latest snapshot: #{latest['id']} `{latest['created_at']}`")
        out.append(f"- Running containers: {latest['running_containers']}")
        out.append(f"- Published ports: {latest['published_ports']}")
        out.append(f"- LAN reachable ports: {latest['lan_reachable_ports']}")
        out.append(f"- Possible blocked ports: {latest['possible_blocked_ports']}")
        out.append(f"- SMART warning markers: {latest['smart_warning_markers']}")
        out.append(f"- NVMe warning markers: {latest['nvme_warning_markers']}")
        out.append("")
        out.append("#### Next safest step")
        out.append("- Collect a second snapshot, then ZimaBrain can compare drift.")
        out.append("")
        out.append("#### Forum-ready summary")
        out.append("ZimaBrain has started trend alert baselining, but it needs one more snapshot before proactive drift checks are meaningful.")
        return "\n".join(out)

    alerts, stable = _analyse(latest, previous)

    if alerts:
        out.append(f"- Trend drift detected: {len(alerts)} alert item(s).")
    else:
        out.append("- No trend drift alerts detected between the latest two snapshots.")
    out.append(f"- Latest snapshot: #{latest['id']} `{latest['created_at']}`")
    out.append(f"- Previous snapshot: #{previous['id']} `{previous['created_at']}`")
    out.append("")

    out.append("#### Trend alerts")
    if alerts:
        for item in alerts:
            out.append(f"- {item}")
    else:
        out.append("- None detected.")
    out.append("")

    out.append("#### Stable trend checks")
    for item in stable:
        out.append(f"- {item}")
    out.append("")

    out.append("#### Latest alert baseline")
    out.append(f"- Running containers: {latest['running_containers']}")
    out.append(f"- Published ports: {latest['published_ports']}")
    out.append(f"- LAN reachable ports: {latest['lan_reachable_ports']}")
    out.append(f"- Intentional localhost-only ports: {latest['localhost_only_ports']}")
    out.append(f"- Possible blocked ports: {latest['possible_blocked_ports']}")
    out.append(f"- SMART warning markers: {latest['smart_warning_markers']}")
    out.append(f"- NVMe warning markers: {latest['nvme_warning_markers']}")
    out.append("")

    out.append("#### Next safest step")
    if alerts:
        out.append("- Review the alert items before exposing new ports, changing firewall rules, or trusting disk health.")
    else:
        out.append("- Keep collecting snapshots. No alert threshold was crossed between the latest two scans.")
    out.append("")

    out.append("#### Forum-ready summary")
    out.append("ZimaBrain proactive trend alerts compare the latest two local SQLite snapshots for drift in container count, published ports, LAN reachable ports, possible blocked ports, and SMART/NVMe warning markers.")

    return "\n".join(out)
