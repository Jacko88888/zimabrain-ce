def answer(bundle, question):
    report = bundle.get("report", "") or ""
    evidence = bundle.get("same_report_evidence", {}) or {}

    samba = evidence.get("samba", "") or ""
    mounts = evidence.get("mounts", "") or ""

    lines = []
    lines.append("- This is an SMB / shares diagnostic question.")
    lines.append("- The layer checks share access, Samba state, paths, permissions, and mounted storage.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Samba evidence parsed: {'yes' if samba.strip() else 'no'}")
    lines.append(f"- Mount evidence parsed: {'yes' if mounts.strip() else 'no'}")
    lines.append(f"- General report evidence present: {'yes' if report.strip() else 'no'}")

    if not samba.strip() and not mounts.strip():
        lines.append("")
        lines.append("- No matching same-report SMB/share evidence was found.")
        return {
            "lines": lines,
            "next_step": "Collect Samba service status, smb.conf/share path, mount output, and permissions before changing shares.",
            "forum_summary": "SMB/share issue is not verified yet. Collect Samba, share path, mount, and permission evidence first.",
        }

    lines.append("")
    lines.append("- Some storage/share evidence exists, but the SMB root cause is not fully verified from same-report evidence.")
    lines.append("")
    lines.append("### Diagnostic focus")
    lines.append("- Confirm the exact share path.")
    lines.append("- Confirm the path is mounted and writable on the host.")
    lines.append("- Confirm Samba user exists.")
    lines.append("- Confirm folder ownership and permissions.")
    lines.append("- Confirm Windows/macOS client error message.")
    return {
        "lines": lines,
        "next_step": "Verify the exact share path, Samba user, mount state, and permissions before changing SMB settings.",
        "forum_summary": "SMB evidence is partial. Verify share path, mount, user, and permissions before repair.",
    }
