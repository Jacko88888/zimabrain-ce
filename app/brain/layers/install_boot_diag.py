def answer(bundle, question):
    report = bundle.get("report", "") or ""
    evidence = bundle.get("same_report_evidence", {}) or {}

    has_host = bool(report.strip())
    has_boot = any(k in evidence for k in ["host_os", "cmdline", "rauc", "kernel"])

    lines = []
    lines.append("- This is an install / boot diagnostic question.")
    lines.append("- The layer separates installer, EFI/boot picker, disk detection, and post-install boot problems.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- General report evidence present: {'yes' if has_host else 'no'}")
    lines.append(f"- Host boot/version evidence present: {'yes' if has_boot else 'no'}")

    lines.append("")
    lines.append("### Diagnostic focus")
    lines.append("- Confirm whether the issue is installer boot, disk detection, EFI boot entry, or first boot after install.")
    lines.append("- For Mac hardware, confirm whether EFI Boot appears in the boot picker.")
    lines.append("- Confirm whether Linux live USB can see the internal disk.")
    lines.append("- Confirm target disk, partition table, and whether ZimaOS installer detected any install device.")

    if not has_host and not has_boot:
        lines.append("")
        lines.append("- No matching same-report install/boot evidence was found.")
        return {
            "lines": lines,
            "next_step": "Collect photos of the boot picker, installer disk screen, and lsblk output from a live Linux USB before advising reinstall or disk changes.",
            "forum_summary": "Install/boot issue is not verified yet. Collect boot picker, installer disk detection, and live USB disk evidence first.",
        }

    lines.append("")
    lines.append("- Some local report evidence exists, but the boot/install root cause is not fully verified from same-report evidence.")
    return {
        "lines": lines,
        "next_step": "Verify boot picker result, EFI entry, installer disk detection, and live USB lsblk output before changing the disk.",
        "forum_summary": "Install/boot evidence is partial. Confirm EFI boot visibility and disk detection before reinstalling or wiping anything.",
    }
