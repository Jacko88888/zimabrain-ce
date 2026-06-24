def answer(bundle, severity_dot):
    n = bundle["normalized"]
    count = bundle.get("container_count", {}) or {}
    running = count.get("running")
    total = count.get("total")
    not_running = count.get("not_running")

    lines = []
    lines.append("- This is a dashboard alert question.")
    lines.append("- The answer comes from the Dashboard Alerts Layer after the Evidence Normalizer Layer has cleaned it.")
    lines.append("")

    lines.append("Real alerts:")
    if n.get("real_alerts"):
        for alert in n["real_alerts"]:
            lines.append(f"- {severity_dot(alert)}")
    else:
        lines.append("- No real hardware/storage alerts were parsed.")

    lines.append("")
    lines.append("Container/service alerts:")
    if running is not None and total is not None:
        lines.append(f"- Dashboard container count: {running}/{total} running.")
        if not_running and not_running > 0:
            lines.append(f"- {not_running} container(s) are not running according to the visual dashboard count.")

    if n.get("container_alerts"):
        for alert in n["container_alerts"]:
            lines.append(f"- {severity_dot(alert)}")
    else:
        if not_running and not_running > 0:
            lines.append("- No named exited container/service alert was parsed, but the dashboard count still shows a container mismatch.")
        else:
            lines.append("- No exited container/service alerts were parsed.")

    lines.append("")
    lines.append("Info only / unsupported metrics:")
    if n.get("info_alerts"):
        for alert in n["info_alerts"]:
            lines.append(f"- {severity_dot(alert)}")
    else:
        lines.append("- No unsupported/N/A SMART values were parsed.")

    return {
        "lines": lines,
        "next_step": "If the container count is not full, inspect Docker status for the missing stopped/exited container first. Then check any hardware, storage, or service alerts one by one.",
        "forum_summary": "Based on the verified report, compare the dashboard container count with named container alerts. If the count is not full but no name is parsed, verify Docker status before changing or removing anything.",
    }
