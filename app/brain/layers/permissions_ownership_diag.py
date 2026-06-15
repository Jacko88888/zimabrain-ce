def answer(bundle, question):
    report = bundle.get("report", "") or ""
    evidence = bundle.get("same_report_evidence", {}) or {}

    mounts = evidence.get("mounts", "") or ""
    docker_access = evidence.get("docker_access", "") or ""

    lines = []
    lines.append("- This is a permissions / ownership diagnostic question.")
    lines.append("- The layer checks whether the issue is host permissions, Docker bind mounts, UID/GID mismatch, or read-only storage.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Mount evidence parsed: {'yes' if mounts.strip() else 'no'}")
    lines.append(f"- Docker bind-mount evidence parsed: {'yes' if docker_access.strip() else 'no'}")
    lines.append(f"- General report evidence present: {'yes' if report.strip() else 'no'}")

    if not mounts.strip() and not docker_access.strip():
        lines.append("")
        lines.append("- No matching same-report permission/path evidence was found.")
        return {
            "lines": lines,
            "next_step": "Collect ls -ld output for the path, mount state, app container user, and Docker bind path before changing ownership.",
            "forum_summary": "Permission issue is not verified yet. Collect path ownership, mount, and Docker bind evidence first.",
        }

    lines.append("")
    lines.append("- Some path evidence exists, but the permission root cause is not fully verified from same-report evidence.")
    lines.append("")
    lines.append("### Diagnostic focus")
    lines.append("- Confirm exact host path.")
    lines.append("- Confirm exact container path if Docker is involved.")
    lines.append("- Confirm owner, group, and mode.")
    lines.append("- Confirm whether filesystem is read-only.")
    lines.append("- Confirm UID/GID expected by the app.")
    return {
        "lines": lines,
        "next_step": "Verify exact path ownership, mount read/write state, and app UID/GID before applying chmod or chown.",
        "forum_summary": "Permission evidence is partial. Verify path, mount state, ownership, and UID/GID before repair.",
    }
