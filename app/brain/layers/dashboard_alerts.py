def answer(bundle, severity_dot):
    n = bundle["normalized"]

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
    if n.get("container_alerts"):
        for alert in n["container_alerts"]:
            lines.append(f"- {severity_dot(alert)}")
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
        "next_step": "Inspect the failed zima-cron-fix.service first, then check whether sda CRC errors are increasing, verify the active sdd mount before deleting anything, and finally review the exited containers one by one.",
        "forum_summary": "Based on the verified report, the priority order is: failed zima-cron-fix.service, sda CRC errors, sdd filesystem usage at 100%, then exited containers. Handle each item by verifying the exact service, disk, mount, or container before making changes.",
    }
