def is_global_question(question):
    q = (question or "").lower()

    global_terms = [
        "what needs attention",
        "show dashboard alerts",
        "dashboard alerts",
        "show alerts",
        "any alerts",
        "all alerts",
        "full diagnosis",
        "full report",
        "system summary",
        "overall health",
        "health summary",
    ]

    return any(term in q for term in global_terms)


def other_system_findings(bundle, question):
    q = (question or "").lower()
    normalized = bundle.get("normalized", {})
    findings = []

    def about_crc():
        return "crc" in q or "sda" in q

    def about_sdd():
        return "sdd" in q or "filesystem usage" in q or "100%" in q or "usage" in q

    def about_containers():
        return "container" in q or "containers" in q or "exited" in q

    def about_failed_units():
        return "failed unit" in q or "failed service" in q or "systemd" in q or "zima-cron" in q or "cron" in q

    if not about_failed_units():
        for item in bundle.get("critical_findings", []):
            title = item.get("title", "")
            detail = item.get("detail") or item.get("evidence") or ""
            if "failed" in title.lower() or "failed" in detail.lower():
                findings.append("Failed host unit detected.")
                break

    for alert in normalized.get("real_alerts", []):
        low = alert.lower()

        if "crc" in low and not about_crc():
            findings.append("A disk has CRC errors. Check the exact device in SMART evidence.")

        if "filesystem usage" in low and not about_sdd():
            findings.append("A disk/filesystem usage alert was detected. Verify the exact mount before deleting anything.")

    exited = normalized.get("container_alerts", [])
    if exited and not about_containers():
        findings.append(f"{len(exited)} container/service alerts detected.")

    # Keep this brief; focused answers should not become full reports.
    return findings[:4]
