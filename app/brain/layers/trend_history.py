import os
import sqlite3

TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


def is_trend_question(question):
    q = (question or "").lower()
    return any(x in q for x in [
        "trend history",
        "trend snapshot",
        "trend snapshots",
        "snapshot history",
        "port and smart trend",
        "smart trend history",
        "port trend history",
        "what changed since the last scan",
        "what changed from last scan",
        "compare last scan",
        "compare trend",
    ])


def _read_rows(limit=8):
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


def _delta(now, prev, key):
    if not now or not prev:
        return None
    return int(now[key]) - int(prev[key])


def _fmt_delta(value):
    if value is None:
        return "n/a"
    if value > 0:
        return f"+{value}"
    return str(value)


def answer(question, bundle):
    rows = _read_rows(limit=8)

    out = []
    out.append("### ZimaBrain Answer")
    out.append("")
    out.append("## ❓ Question asked")
    out.append(f"### {question.strip()}")
    out.append("")
    out.append("#### Verification status")
    if rows:
        out.append("@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM LOCAL TREND DATABASE")
        out.append("- This answer is based on ZimaBrain's local SQLite trend database.")
    else:
        out.append("@@VERIFY:NOT VERIFIED@@ ❌ NOT VERIFIED")
        out.append("- No trend snapshots were found yet.")
    out.append("- Active layer: Trend History Layer")
    out.append("- Layer file: `app/brain/layers/trend_history.py`")
    out.append("")

    out.append("#### Direct answer / severity")

    if not rows:
        out.append("- No trend history has been recorded yet.")
        out.append("- Refresh ZimaBrain or ask a diagnostic question first so a trend snapshot can be saved.")
        out.append("")
        out.append("#### Next safest step")
        out.append("- Run one scan, then ask this question again.")
        out.append("")
        out.append("#### Forum-ready summary")
        out.append("ZimaBrain trend history was requested, but no local trend snapshots exist yet.")
        return "\n".join(out)

    latest = rows[0]
    previous = rows[1] if len(rows) > 1 else None

    out.append("- ZimaBrain found local saved trend snapshots.")
    out.append(f"- Snapshots available in this view: {len(rows)}")
    out.append(f"- Latest snapshot: `{latest['created_at']}`")
    out.append("")

    out.append("#### Latest trend snapshot")
    out.append(f"- App version: `{latest['app_version']}`")
    out.append(f"- Running containers: {latest['running_containers']}")
    out.append(f"- Published ports: {latest['published_ports']}")
    out.append(f"- LAN reachable ports: {latest['lan_reachable_ports']}")
    out.append(f"- Intentional localhost-only ports: {latest['localhost_only_ports']}")
    out.append(f"- Possible blocked ports: {latest['possible_blocked_ports']}")
    out.append(f"- SMART warning markers: {latest['smart_warning_markers']}")
    out.append(f"- NVMe warning markers: {latest['nvme_warning_markers']}")
    out.append("")

    out.append("#### Change since previous scan")
    if previous:
        out.append(f"- Previous snapshot: `{previous['created_at']}`")
        for label, key in [
            ("Running containers", "running_containers"),
            ("Published ports", "published_ports"),
            ("LAN reachable ports", "lan_reachable_ports"),
            ("Intentional localhost-only ports", "localhost_only_ports"),
            ("Possible blocked ports", "possible_blocked_ports"),
            ("SMART warning markers", "smart_warning_markers"),
            ("NVMe warning markers", "nvme_warning_markers"),
        ]:
            out.append(f"- {label}: {_fmt_delta(_delta(latest, previous, key))}")
    else:
        out.append("- No previous snapshot yet, so there is nothing to compare against.")
    out.append("")

    out.append("#### Recent snapshots")
    for row in rows:
        out.append(
            f"- #{row['id']} `{row['created_at']}` "
            f"containers={row['running_containers']} "
            f"ports={row['published_ports']} "
            f"lan={row['lan_reachable_ports']} "
            f"localhost_only={row['localhost_only_ports']} "
            f"blocked={row['possible_blocked_ports']} "
            f"smart={row['smart_warning_markers']} "
            f"nvme={row['nvme_warning_markers']}"
        )

    out.append("")
    out.append("#### Next safest step")
    out.append("- Keep collecting snapshots over time, then use changes in ports, SMART markers, NVMe markers, and container count to detect drift.")
    out.append("")
    out.append("#### Forum-ready summary")
    out.append("ZimaBrain trend history is now backed by a local SQLite trend database. It records container count, published ports, LAN reachability, localhost-only ports, possible blocked ports, and SMART/NVMe warning markers so future scans can be compared.")

    return "\n".join(out)
