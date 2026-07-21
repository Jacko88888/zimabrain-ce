import os

from brain import health_memory


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


def is_alert_question(question):
    q = (question or "").lower()
    return any(x in q for x in [
        "trend alert", "trend alerts", "any alerts", "do i have alerts",
        "do i have any alerts", "proactive alert", "proactive alerts",
        "alert me", "drift alert", "drift alerts", "port alert",
        "smart alert", "nvme alert", "what should alert",
        "anything changed dangerously", "what should i check first",
    ])


def _actionable(event):
    classification = event.get("classification")
    if classification in {"worsening", "new_issue"}:
        return True
    if classification != "persistent":
        return False
    if event.get("category") in {"service", "service_exec"}:
        return True
    if event.get("category") == "container":
        if event.get("metric") == "health":
            return event.get("current_text") == "unhealthy"
        if event.get("metric") == "state":
            return event.get("current_text") in {"restarting", "dead", "paused"}
    if event.get("category") in {"smart", "nvme"}:
        return True
    return False


def answer(question, bundle):
    scan = health_memory.latest_scan(TREND_DB_PATH) if os.path.exists(TREND_DB_PATH) else None
    events = health_memory.latest_events(TREND_DB_PATH, limit=500) if scan else []
    actionable = [x for x in events if _actionable(x)]
    historical = [x for x in events if x.get("classification") == "historical_stable"]
    recovered = [x for x in events if x.get("classification") == "recovered"]
    drift_history = health_memory.configuration_drift_history(
        TREND_DB_PATH, limit=10
    ) if scan else {"drifts": []}
    drift_attention = [
        item for item in drift_history.get("drifts", [])
        if item.get("severity") == "attention"
        and item.get("to_scan") == scan["id"]
    ] if scan else []
    inactive = [x for x in events if
                x.get("classification") == "persistent" and
                x.get("category") == "container" and
                x.get("metric") == "state" and
                x.get("current_text") == "exited"]

    out = [
        "### ZimaBrain Answer", "", "## ❓ Question asked",
        f"### {question.strip()}", "", "#### Verification status",
    ]
    if scan and events:
        out.extend([
            "@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM LOCAL HEALTH TIMELINE",
            "- Alert status is based on the latest detailed local scan and its previous baseline.",
        ])
    else:
        out.extend([
            "@@VERIFY:NOT VERIFIED@@ ❌ NOT VERIFIED",
            "- No detailed health-memory comparison is available yet.",
        ])
    out.extend([
        "- Active layer: Health Timeline Alert Layer",
        "- Layer files: `app/brain/health_memory.py`, `app/brain/layers/trend_alerts.py`",
        "", "#### Direct answer / severity",
    ])

    if not scan or not events:
        out.extend([
            "- No verified detailed trend alert can be produced yet.", "",
            "#### Next safest step", "- Collect at least two detailed scans.", "",
            "#### Forum-ready summary",
            "ZimaBrain needs detailed local health scans before trend alerts can be verified.",
        ])
        return "\n".join(out)

    total_actionable = len(actionable) + len(drift_attention)
    if total_actionable:
        out.append(
            f"- Actionable timeline conditions detected: {total_actionable}"
        )
    else:
        out.append(
            "- No actionable new, worsening, persistent, or configuration-drift "
            "condition was detected."
        )
    out.extend([
        f"- Actionable configuration drift: {len(drift_attention)}",
        f"- Historical stable values: {len(historical)}",
        f"- Recovered signals: {len(recovered)}",
        f"- Persistently exited containers requiring intent verification: {len(inactive)}", "",
        "#### Actionable timeline alerts",
    ])
    if actionable:
        for item in actionable[:25]:
            out.append(f"- {item['message']}")
    if drift_attention:
        for item in drift_attention[:25]:
            out.append(
                f"- Configuration drift: {item['message']} "
                f"Status: {item['classification'].replace('_', ' ').title()}."
            )
    if not actionable and not drift_attention:
        out.append("- None detected.")

    out.extend(["", "#### Historical values with no increase"])
    if historical:
        for item in historical[:20]:
            out.append(f"- {item['message']}")
    else:
        out.append("- None recorded in the latest comparison.")

    out.extend(["", "#### Persistent inactive containers"])
    if inactive:
        for item in inactive[:20]:
            out.append(f"- {item['entity_name']} remains exited. Verify whether this is intentional before treating it as a fault.")
    else:
        out.append("- None detected.")

    out.extend([
        "", "#### Next safest step",
        "- Investigate worsening counters, restart loops, missing paths or mounts, newly exposed LAN ports, firewall/audit changes, and newly enabled privilege or Docker-socket access first. Verify intent before changing configuration.",
        "", "#### Forum-ready summary",
        "ZimaBrain separated actionable timeline alerts from unchanged historical counters and persistently inactive containers. This prevents old values from being repeatedly presented as new faults.",
    ])
    return "\n".join(out)
