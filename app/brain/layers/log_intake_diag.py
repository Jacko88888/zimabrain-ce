def answer(bundle, question):
    report = bundle.get("report", "") or ""

    has_log_words = any(x in report.lower() for x in ["error", "failed", "traceback", "journal", "exception", "permission denied"])

    lines = []
    lines.append("- This is a log intake / uploaded evidence question.")
    lines.append("- The layer classifies logs first, then routes to the correct diagnostic area.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Report text present: {'yes' if report.strip() else 'no'}")
    lines.append(f"- Error-style wording detected: {'yes' if has_log_words else 'no'}")

    if not report.strip():
        lines.append("")
        lines.append("- No matching same-report log evidence was found.")
        return {
            "lines": lines,
            "next_step": "Upload or paste the relevant log output, then identify the affected service, app, disk, or mount.",
            "forum_summary": "No log evidence was available. Upload the log and identify the affected service/app/path first.",
        }

    lines.append("")
    lines.append("- Log/report text exists, but the root cause is not fully verified until the failing service/path/device is identified.")
    lines.append("")
    lines.append("### Intake focus")
    lines.append("- Identify exact failing service or container.")
    lines.append("- Identify first real error, not only repeated follow-up errors.")
    lines.append("- Match error to disk, mount, Docker, network, permission, or app layer.")
    return {
        "lines": lines,
        "next_step": "Identify the first real error and affected service/path/device, then route to the matching diagnostic layer.",
        "forum_summary": "Log evidence exists, but root cause needs classification by affected service, app, path, disk, or mount.",
    }
