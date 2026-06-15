def answer(bundle, question):
    report = bundle.get("report", "") or ""
    evidence = bundle.get("same_report_evidence", {}) or {}

    host_os = evidence.get("host_os", "") or ""
    rauc = evidence.get("rauc", "") or ""
    cmdline = evidence.get("cmdline", "") or ""

    lines = []
    lines.append("- This is a ZimaOS update / rollback safety question.")
    lines.append("- The layer checks current host evidence before advising update, rollback, or reinstall.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Host OS evidence parsed: {'yes' if host_os.strip() else 'no'}")
    lines.append(f"- RAUC evidence parsed: {'yes' if rauc.strip() else 'no'}")
    lines.append(f"- Boot cmdline evidence parsed: {'yes' if cmdline.strip() else 'no'}")

    if not host_os.strip() and not rauc.strip() and not cmdline.strip():
        lines.append("")
        lines.append("- No matching same-report update/rollback evidence was found.")
        return {
            "lines": lines,
            "next_step": "Collect host version, RAUC status, boot slot, failed units, and storage mount evidence before update or rollback advice.",
            "forum_summary": "Update/rollback safety is not verified yet. Collect version, RAUC, boot slot, failed units, and mount evidence first.",
        }

    lines.append("")
    lines.append("- Some update/host evidence exists, but rollback or update safety is not fully verified from same-report evidence.")
    lines.append("")
    lines.append("### Safety focus")
    lines.append("- Confirm current ZimaOS version.")
    lines.append("- Confirm RAUC compatibility/status.")
    lines.append("- Confirm failed units after update.")
    lines.append("- Confirm storage mounts before blaming the update.")
    lines.append("- Confirm backups before rollback or reinstall.")
    return {
        "lines": lines,
        "next_step": "Verify version, RAUC status, failed units, and storage mounts before rollback or update changes.",
        "forum_summary": "Update/rollback evidence is partial. Verify version, RAUC, failed units, mounts, and backups before changing system state.",
    }
