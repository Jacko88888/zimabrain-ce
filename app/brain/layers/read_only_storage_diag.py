def _evidence(bundle, key):
    return (bundle.get("same_report_evidence", {}) or {}).get(key, "") or ""


def _has_read_only_text(text):
    t = (text or "").lower()
    return any(x in t for x in ["read-only", "read only", "readonly", " ro,", "(ro", " ro "])


def answer(bundle, question):
    report = bundle.get("report", "") or ""
    mounts = _evidence(bundle, "mounts")
    df = _evidence(bundle, "df")
    disk_health = str(bundle.get("disk_health", "") or "")
    all_text = "\n".join([report, mounts, df, disk_health])

    has_ro = _has_read_only_text(all_text)
    has_mounts = bool(mounts.strip())
    has_disk = bool(disk_health.strip())

    lines = []
    lines.append("- This is a read-only storage diagnostic question.")
    lines.append("- The layer checks same-report mount, filesystem, and disk evidence before suggesting repair steps.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Mount evidence parsed: {'yes' if has_mounts else 'no'}")
    lines.append(f"- Disk health evidence parsed: {'yes' if has_disk else 'no'}")
    lines.append(f"- Read-only wording detected in current evidence: {'yes' if has_ro else 'no'}")

    if not has_ro:
        lines.append("")
        lines.append("- No matching same-report read-only mount evidence was found.")
        lines.append("- The root cause is not verified from the current report.")
        return {
            "lines": lines,
            "next_step": "Collect active mount output, df output, lsblk output, and recent filesystem errors before attempting any repair.",
            "forum_summary": "The read-only storage issue is not verified yet. Collect active mount, df, lsblk, SMART, and filesystem error evidence before repair.",
        }

    lines.append("")
    lines.append("- Read-only wording was detected in the current evidence.")
    lines.append("- Root cause is not fully verified until the affected device, filesystem, and journal errors are checked.")

    lines.append("")
    lines.append("### Required checks before repair")
    lines.append("- Confirm the exact path that became read-only.")
    lines.append("- Confirm which block device backs that path.")
    lines.append("- Check filesystem errors from journal.")
    lines.append("- Check SMART health, pending sectors, reallocated sectors, and CRC errors.")
    lines.append("- Check whether Docker apps are writing to the affected path.")

    lines.append("")
    lines.append("### Do not do yet")
    lines.append("- Do not force remount read-write until the affected device is confirmed.")
    lines.append("- Do not run filesystem repair on a mounted filesystem.")
    lines.append("- Do not delete app data or Docker folders.")
    lines.append("- Do not recreate apps until the storage fault is understood.")

    return {
        "lines": lines,
        "next_step": "Confirm the exact read-only mount path, backing device, filesystem type, and recent filesystem errors before repair.",
        "forum_summary": "Read-only evidence exists, but the exact root cause still needs confirmation from mount, device, filesystem, SMART, and journal evidence.",
    }
