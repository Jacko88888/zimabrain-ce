def _short(text, limit=220):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _count_lines(text):
    return len([x for x in (text or "").splitlines() if x.strip()])


def answer(bundle):
    lines = []

    report = bundle.get("report", "")
    normalized = bundle.get("normalized", {})
    evidence = bundle.get("same_report_evidence", {})
    critical = bundle.get("critical_findings", [])
    disks = bundle.get("disks", [])
    exited = bundle.get("exited", [])

    real_alerts = normalized.get("real_alerts", [])
    container_alerts = normalized.get("container_alerts", [])
    info_only = normalized.get("info_only", [])

    lines.append("- This is a report comparison / baseline question.")
    lines.append("- The answer comes from the Report Comparison Layer using the current dashboard bundle.")
    lines.append("")

    lines.append("### Current report baseline")
    lines.append(f"- Report size: {len(report):,} characters")
    lines.append(f"- Real alerts: {len(real_alerts)}")
    lines.append(f"- Container alerts: {len(container_alerts)}")
    lines.append(f"- Info-only items: {len(info_only)}")
    lines.append(f"- Critical same-report findings: {len(critical)}")
    lines.append(f"- Disks parsed: {len(disks)}")
    lines.append(f"- Exited containers parsed: {len(exited)}")
    lines.append(f"- Same-report evidence sections: {len(evidence)}")

    lines.append("")
    lines.append("### Highest priority items in this report")
    shown = False

    if critical:
        shown = True
        lines.append("- Critical same-report findings:")
        for item in critical[:10]:
            title = item.get("title", "Finding")
            detail = item.get("detail") or item.get("evidence") or ""
            lines.append(f"  - {title}: {_short(detail)}")

    if real_alerts:
        shown = True
        lines.append("- Real alerts:")
        for item in real_alerts[:10]:
            lines.append(f"  - {_short(item)}")

    if exited:
        shown = True
        lines.append("- Exited containers:")
        for item in exited[:10]:
            lines.append(f"  - {_short(str(item))}")

    if not shown:
        lines.append("- No high-priority critical findings, real alerts, or exited containers were parsed from the current report.")

    lines.append("")
    lines.append("### Disk comparison baseline")
    if disks:
        for d in disks[:20]:
            name = d.get("device") or d.get("name") or "unknown"
            model = d.get("model", "unknown")
            size = d.get("size", "unknown")
            health = d.get("health", "unknown")
            temp = d.get("temp", "N/A")
            crc = d.get("crc", "N/A")
            pending = d.get("pending", "N/A")
            realloc = d.get("realloc", "N/A")
            mount = d.get("mount", "")
            lines.append(
                f"- {name}: model={model}, size={size}, health={health}, temp={temp}, "
                f"crc={crc}, pending={pending}, realloc={realloc}, mount={mount}"
            )
    else:
        lines.append("- No disk table was parsed from the current report.")

    lines.append("")
    lines.append("### Same-report evidence coverage")
    if evidence:
        for key in sorted(evidence.keys()):
            value = evidence.get(key, "")
            lines.append(f"- {key}: {_count_lines(value)} non-empty lines")
    else:
        lines.append("- No same-report evidence sections were parsed.")

    lines.append("")
    lines.append("### What this can compare today")
    lines.append("- Current dashboard alerts versus same-report verifier findings.")
    lines.append("- Disk table values versus current alert state.")
    lines.append("- Container state versus Docker evidence.")
    lines.append("- Mount/path clues versus Docker bind paths.")
    lines.append("")

    lines.append("### Important limitation")
    lines.append("- This v1 layer does not yet compare against an older saved report.")
    lines.append("- It creates a current baseline so the next report can be compared safely.")
    lines.append("- For true before/after comparison, add saved report snapshots with timestamps.")

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- Treat this output as the current known-good or current-known-problem baseline.")
    lines.append("- Save this report before making changes.")
    lines.append("- After the next reboot, update, storage change, or container change, compare against this baseline.")
    lines.append("- Do not call something fixed until the next report shows the alert or value has changed.")

    return {
        "lines": lines,
        "next_step": "Save this current report as a baseline, then compare the next report after reboot, update, storage change, or container change.",
        "forum_summary": "This report comparison layer creates a current baseline from alerts, disks, containers, and same-report verifier evidence. It does not yet compare against an older saved report, so save this output first and compare the next report after the system changes.",
    }
