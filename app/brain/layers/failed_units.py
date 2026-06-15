def answer(bundle, critical_badge):
    lines = []
    lines.append("- This is a failed host unit / service question.")
    lines.append("- The answer comes from the Failed Units Layer using Critical Same-Report Verifier evidence.")
    lines.append("")

    failed_items = [
        item for item in bundle.get("critical_findings", [])
        if "failed" in item.get("title", "").lower()
        or "failed" in item.get("detail", "").lower()
    ]

    if failed_items:
        lines.append("Failed host unit findings:")
        for item in failed_items:
            lines.append(f"- {critical_badge(item['level'])}: {item['title']}")
            lines.append(f"  Evidence: {item['detail']}")
            lines.append(f"  Why it matters: {item['why']}")
            lines.append(f"  Next safest step: {item['next']}")
    else:
        lines.append("- No failed host units were detected by the current verifier layer.")

    return {
        "lines": lines,
        "next_step": "Inspect only the failed unit shown in the report before changing unrelated services or containers.",
        "forum_summary": "Based on the verified report, a failed host unit was detected. Inspect that exact service first and avoid changing unrelated Docker containers, mounts, or storage paths until the failed unit evidence is understood.",
    }
