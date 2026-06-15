def _lines_from_text(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _contains_any(text, needles):
    low = (text or "").lower()
    return any(n.lower() in low for n in needles)


def answer(bundle, question=""):
    lines = []

    q = (question or "").lower().strip()
    version_only = any(x in q for x in [
        "what zimaos version",
        "which zimaos version",
        "zimaos version",
        "zima version",
        "host version",
        "what version",
        "which version",
        "kernel version",
        "what kernel",
        "rauc status",
    ]) and not any(x in q for x in [
        "regression",
        "after update",
        "after upgrade",
        "apps broke",
        "paths changed",
        "ghost",
        "duplicate",
        "rollback",
        "problem",
        "issue",
        "broken",
    ])

    report = bundle.get("report", "")
    evidence = bundle.get("same_report_evidence", {})
    mounts = evidence.get("mounts", "")
    docker_access = evidence.get("docker_access", "")
    host_os_raw = evidence.get("host_os", "")
    host_kernel = (evidence.get("kernel", "") or "").strip()
    host_uptime = (evidence.get("uptime", "") or "").strip()
    host_rauc_raw = (evidence.get("rauc", "") or "").strip()
    host_cmdline = (evidence.get("cmdline", "") or "").strip()
    normalized = bundle.get("normalized", {})

    host_os_name = ""
    host_os_version = ""
    for os_line in _lines_from_text(host_os_raw):
        if os_line.startswith("PRETTY_NAME="):
            host_os_name = os_line.split("=", 1)[1].strip().strip('"')
        elif os_line.startswith("VERSION="):
            host_os_version = os_line.split("=", 1)[1].strip().strip('"')
        elif os_line.startswith("VERSION_ID=") and not host_os_version:
            host_os_version = os_line.split("=", 1)[1].strip().strip('"')

    lines.append("- This is a ZimaOS update / regression verification question.")
    lines.append("- The answer comes from the ZimaOS Update / Regression Layer using current dashboard and same-report evidence.")
    lines.append("")

    version_clues = []
    regression_clues = []
    media_path_clues = []
    failed_unit_clues = []
    limitation_clues = []

    for line in _lines_from_text(report):
        low = line.lower()

        if "zimaos" in low and ("version" in low or "build" in low or "release" in low):
            version_clues.append(line)

        if "failed" in low and ("service" in low or ".service" in low):
            failed_unit_clues.append(line)

        if ".media" in low or "/media/" in low or "/host/var/lib/casaos_data/.media" in low:
            media_path_clues.append(line)

        if "duplicate" in low or "ghost" in low or "rollback" in low or "rauc" in low or "cmdline" in low:
            regression_clues.append(line)

    for line in _lines_from_text(mounts):
        low = line.lower()
        if ".media" in low or "/media/" in low or "-/dev/" in low:
            media_path_clues.append(line)

    for line in _lines_from_text(docker_access):
        low = line.lower()
        if "/data/.media" in low or "/var/lib/casaos_data/.media" in low or "-/dev/" in low:
            media_path_clues.append(line)
        if (
            "/data/.media" in low
            or "/var/lib/casaos_data/.media" in low
            or "-/dev/" in low
            or "duplicate" in low
            or "ghost" in low
            or "rollback" in low
            or "rauc" in low
            or "cmdline" in low
        ):
            regression_clues.append(line)

    for alert in normalized.get("real_alerts", []):
        low = alert.lower()
        if "failed" in low or ".service" in low:
            failed_unit_clues.append(alert)
        if "filesystem usage" in low or ".media" in low:
            regression_clues.append(alert)

    host_version_available = any([host_os_name, host_os_version, host_kernel, host_rauc_raw, host_cmdline])

    if not version_clues and not host_version_available:
        limitation_clues.append("No ZimaOS version, RAUC slot, rollback, or os-release evidence was parsed by the current collector.")

    lines.append("### Version / update evidence")

    if host_os_name:
        lines.append(f"- Host OS: {host_os_name}")
    if host_os_version:
        lines.append(f"- Host Version: {host_os_version}")
    if host_kernel:
        lines.append(f"- Kernel: {host_kernel}")
    if host_uptime:
        lines.append(f"- Uptime: {host_uptime}")
    if host_rauc_raw and "not found" not in host_rauc_raw.lower():
        useful_rauc = []
        for rauc_line in _lines_from_text(host_rauc_raw):
            low = rauc_line.lower()
            if rauc_line.startswith("==="):
                continue
            if "system info" in low:
                continue
            useful_rauc.append(rauc_line)
        if useful_rauc:
            lines.append(f"- RAUC: {useful_rauc[0]}")
    if host_cmdline:
        lines.append(f"- Boot cmdline: {host_cmdline[:240]}")

    if version_clues:
        for item in version_clues[:12]:
            lines.append(f"- {item}")

    if not host_version_available and not version_clues:
        lines.append("- No direct ZimaOS version or update-slot evidence was parsed from the current report.")

    if version_only:
        return {
            "lines": lines,
            "next_step": "Use this version evidence as the baseline. Only run the full regression check if the issue started after an update or paths/apps changed.",
            "forum_summary": "The running ZimaOS host version, kernel, uptime, RAUC compatibility, and boot command line were checked from same-report host evidence.",
        }

    lines.append("")
    lines.append("### Regression-style symptoms detected")

    shown_any = False

    if failed_unit_clues:
        shown_any = True
        lines.append("- Failed unit / service clues:")
        seen = set()
        for item in failed_unit_clues[:12]:
            if item in seen:
                continue
            seen.add(item)
            lines.append(f"  - {item}")

    if media_path_clues:
        shown_any = True
        lines.append("- Media / mount path clues:")
        seen = set()
        for item in media_path_clues[:18]:
            if item in seen:
                continue
            seen.add(item)
            lines.append(f"  - {item}")

    if regression_clues:
        shown_any = True
        lines.append("- Other regression clues:")
        seen = set()
        for item in regression_clues[:18]:
            if item in seen:
                continue
            seen.add(item)
            lines.append(f"  - {item}")

    if not shown_any:
        lines.append("- No obvious update/regression-style symptoms were detected from the current evidence.")

    lines.append("")
    lines.append("### Important limitations")
    for item in limitation_clues:
        lines.append(f"- {item}")
    lines.append("- This layer confirms the running host OS/version when os-release evidence is available. RAUC compatibility may also be visible, but this layer does not yet fully confirm boot-slot history, rollback state, or the cause of any regression.")

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- After a ZimaOS update, path symptoms matter: `.media`, `/media`, old `/dev`-style paths, ghost folders, or apps pointing to stale mounts.")
    lines.append("- Failed units after an update should be inspected by exact unit name, not by restarting unrelated containers.")
    lines.append("- A visible folder does not prove an active mount. Confirm with `findmnt` before changing app paths.")
    lines.append("- Host OS, kernel, RAUC, uptime, and boot command line evidence are now collected when available.")

    return {
        "lines": lines,
        "next_step": "Verify active mounts with findmnt and inspect any exact failed unit before blaming the update. Add version/RAUC evidence before confirming a true update regression.",
        "forum_summary": "This checks the running ZimaOS host version when os-release evidence is available, and also looks for update/regression symptoms such as failed units, .media paths, stale /media or /dev-style paths, and app path changes. RAUC boot-slot history and rollback cause still need deeper verification before calling it a confirmed update regression.",
    }
