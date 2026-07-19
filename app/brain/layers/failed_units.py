def answer(bundle, critical_badge):
    evidence = bundle.get("same_report_evidence", {}) or {}
    raw = str(evidence.get("failed_units", "") or "")

    failed_lines = []

    for raw_line in raw.splitlines():
        line = " ".join(raw_line.split())
        low = line.lower()

        if not line:
            continue
        if (
            "0 loaded units listed" in low
            or "no units listed" in low
        ):
            continue

        failed_lines.append(line)

    lines = [
        "Failed service / systemd unit check",
        "",
        "Confirmed:",
    ]

    if failed_lines:
        lines.append(
            f"- Failed-unit assessment: {len(failed_lines)} failed "
            "unit(s) were captured by systemctl."
        )

        for line in failed_lines:
            name = line.split()[0]
            lines.append(f"- Failed unit: {name}")
            lines.append(f"  Evidence: {line}")

        next_step = (
            "Inspect status and recent journal entries for the listed "
            "failed unit before changing unrelated services or containers."
        )
        forum_summary = (
            f"Current systemctl evidence contains {len(failed_lines)} "
            "failed unit(s). Inspect those exact units first."
        )
    else:
        lines.append(
            "- Failed-unit assessment: no failed host unit was captured "
            "by the current systemctl evidence."
        )
        next_step = (
            "No failed-unit repair is indicated by this snapshot. "
            "Recheck systemctl only if a service symptom is still active."
        )
        forum_summary = (
            "Current systemctl evidence did not contain a failed host unit."
        )

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
    }
