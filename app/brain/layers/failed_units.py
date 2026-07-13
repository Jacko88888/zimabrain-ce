def answer(bundle, critical_badge):
    lines = []
    lines.append("Failed service / systemd unit check")
    lines.append("")

    failed_items = [
        item for item in bundle.get("critical_findings", [])
        if "failed" in item.get("title", "").lower()
        or "failed" in (item.get("detail") or item.get("evidence") or "").lower()
    ]

    if failed_items:
        lines.append("Confirmed:")
        for item in failed_items:
            detail = item.get("detail") or item.get("evidence") or ""
            lines.append(f"- {critical_badge(item['level'])}: {item['title']}")
            lines.append(f"  Evidence: {detail}")
            lines.append(f"  Meaning: {item.get('why', '')}")
            lines.append(f"  Next safest step: {item.get('next', '')}")
    else:
        lines.append("Confirmed:")
        lines.append("- No failed host units were detected by the current verifier evidence.")

    return {
        "lines": lines,
        "next_step": "Inspect only the failed unit shown in the report before changing unrelated services or containers.",
        "forum_summary": "Confirmed: ZimaBrain checked failed host units from current verifier evidence. If a failed unit is shown, inspect that exact unit first and avoid changing unrelated Docker containers, mounts, or storage paths until the failed-unit evidence is understood.",
    }
