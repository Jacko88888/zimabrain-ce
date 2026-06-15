def _disk_items(bundle):
    return bundle.get("disks", [])


def _as_int(value, default=0):
    try:
        if value is None:
            return default
        return int(str(value).strip())
    except Exception:
        return default


def answer(bundle):
    lines = []
    disks = _disk_items(bundle)

    lines.append("- This is a SMART trend / disk-risk question.")
    lines.append("- The answer comes from the SMART Trend Monitor using current dashboard disk evidence.")
    lines.append("")

    if not disks:
        lines.append("No disk SMART evidence was parsed from the current report.")
        return {
            "lines": lines,
            "next_step": "Collect current SMART evidence before making any disk replacement or cabling decision.",
            "forum_summary": "No SMART evidence was available in the current report. Collect disk health evidence before making storage changes.",
        }

    crc_items = []
    realloc_items = []
    pending_items = []
    temp_items = []
    passed_items = []
    unknown_items = []

    for d in disks:
        name = d.get("device") or d.get("name", "unknown")
        health = str(d.get("health", "")).upper()
        model = d.get("model", "")
        temp = d.get("temp", "")
        crc = _as_int(d.get("crc", 0))
        realloc = _as_int(d.get("realloc", 0))
        pending = _as_int(d.get("pending", 0))
        power_on = d.get("power_on", "")

        label = f"{name}: health={health or 'UNKNOWN'}, model={model}, temp={temp}, realloc={realloc}, pending={pending}, crc={crc}, power_on={power_on}"

        if crc > 0:
            crc_items.append(label)
        if realloc > 0:
            realloc_items.append(label)
        if pending > 0:
            pending_items.append(label)
        if health == "PASSED":
            passed_items.append(label)
        if health in ("UNKNOWN", "N/A", ""):
            unknown_items.append(label)

        try:
            temp_num = int(str(temp).replace("°C", "").replace("C", "").strip())
            if temp_num >= 50:
                temp_items.append(label)
        except Exception:
            pass

    lines.append("### Current SMART risk findings")

    if crc_items:
        lines.append("- CRC/link errors detected:")
        for item in crc_items:
            lines.append(f"  - {item}")
    else:
        lines.append("- No CRC/link errors were detected in parsed disk evidence.")

    if realloc_items:
        lines.append("")
        lines.append("- Reallocated sector count detected:")
        for item in realloc_items:
            lines.append(f"  - {item}")
    else:
        lines.append("")
        lines.append("- No reallocated sectors were detected in parsed disk evidence.")

    if pending_items:
        lines.append("")
        lines.append("- Pending sectors detected:")
        for item in pending_items:
            lines.append(f"  - {item}")
    else:
        lines.append("")
        lines.append("- No pending sectors were detected in parsed disk evidence.")

    if temp_items:
        lines.append("")
        lines.append("- High temperature warning:")
        for item in temp_items:
            lines.append(f"  - {item}")
    else:
        lines.append("")
        lines.append("- No high disk temperature warning was detected in parsed disk evidence.")

    if unknown_items:
        lines.append("")
        lines.append("- Disks/devices with UNKNOWN health:")
        for item in unknown_items[:12]:
            lines.append(f"  - {item}")

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- CRC errors usually point to the connection path first: cable, port, backplane, controller, or power.")
    lines.append("- Reallocated or pending sectors point more directly toward disk media problems.")
    lines.append("- A single current report is not a real trend yet. Trend means comparing this report against an older report.")
    lines.append("- If CRC, pending, or reallocated counts increase between reports, the risk is higher.")

    return {
        "lines": lines,
        "next_step": "Save this report and compare it with the next report. If CRC, pending, or reallocated counts increase, inspect the cable/backplane/port first, then consider disk replacement if media errors appear.",
        "forum_summary": "Current SMART evidence should be treated as a baseline. CRC errors usually point to the connection path first, while pending or reallocated sectors point more toward disk media problems. Compare future reports to confirm whether the counts are increasing.",
    }
