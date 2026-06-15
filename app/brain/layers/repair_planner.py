def answer(bundle, question):
    report = bundle.get("report", "") or ""
    evidence = bundle.get("same_report_evidence", {}) or {}
    disks = bundle.get("disks", []) or []

    lines = []
    lines.append("- This is a final recommendation / repair planner question.")
    lines.append("- The layer does not repair directly. It orders the next checks from safest to riskiest.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Report text present: {'yes' if report.strip() else 'no'}")
    lines.append(f"- Evidence groups present: {len([k for k,v in evidence.items() if v])}")
    lines.append(f"- Disk inventory parsed: {'yes' if disks else 'no'}")

    if not report.strip() and not evidence and not disks:
        lines.append("")
        lines.append("- No matching same-report evidence was found for a repair plan.")
        return {
            "lines": lines,
            "next_step": "Collect report evidence before generating a repair plan.",
            "forum_summary": "No verified evidence is available yet, so no repair plan should be given.",
        }

    lines.append("")
    lines.append("- Evidence exists, but final repair action is not fully verified until the affected layer confirms the root cause.")
    lines.append("")
    lines.append("### Safe order")
    lines.append("1. Identify the affected layer.")
    lines.append("2. Confirm same-report evidence.")
    lines.append("3. Use read-only commands first.")
    lines.append("4. Back up important data before repair.")
    lines.append("5. Apply only the smallest repair step.")
    lines.append("6. Re-test and compare evidence.")
    return {
        "lines": lines,
        "next_step": "Use the active diagnostic layer first, then apply the smallest safe repair step only after evidence is confirmed.",
        "forum_summary": "Repair plan should follow verified evidence, read-only checks first, backup before repair, and smallest-change-first action.",
    }
