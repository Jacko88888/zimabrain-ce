def answer(bundle, question):
    disks = bundle.get("disks", []) or []
    report = bundle.get("report", "") or ""

    lines = []
    lines.append("- This is an add-drive / RAID / storage planning question.")
    lines.append("- The layer checks disk inventory first and avoids formatting or pool changes until the target drives are confirmed.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Disk inventory parsed: {'yes' if disks else 'no'}")
    lines.append(f"- Report text present: {'yes' if report.strip() else 'no'}")

    if disks:
        lines.append("")
        lines.append("### Parsed disks")
        for d in disks[:12]:
            name = d.get("name") or d.get("device") or "unknown"
            size = d.get("size") or "unknown"
            model = d.get("model") or "unknown"
            mount = d.get("mount") or d.get("mountpoint") or "not mounted"
            lines.append(f"- {name}: {size}, {model}, mount={mount}")
        lines.append("")
        lines.append("- Disk inventory exists, but the intended RAID/pool layout is not fully verified from same-report evidence.")
        return {
            "lines": lines,
            "next_step": "Confirm which disks are new, which disk holds ZimaOS, which disks contain data, and whether the goal is redundancy or capacity.",
            "forum_summary": "Disk inventory exists, but RAID/add-drive action is only partially verified until the target drives and desired layout are confirmed.",
        }

    lines.append("")
    lines.append("- No matching same-report disk inventory was found.")
    return {
        "lines": lines,
        "next_step": "Collect disk inventory, current pool/RAID layout, and data-preservation requirement before advising add-drive steps.",
        "forum_summary": "Add-drive/RAID issue is not verified yet. Collect disk inventory and current storage layout first.",
    }
