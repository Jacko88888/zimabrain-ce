def clean_alert_text(alert):
    text = str(alert).strip()
    for prefix in ["YELLOW:", "RED:", "INFO:"]:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def answer(bundle):
    n = bundle["normalized"]
    lines = []

    lines.append("- This is a disk CRC warning question.")
    lines.append("- The answer comes from the Disk CRC Layer using normalized dashboard evidence.")
    lines.append("")

    lines.append("CRC-related dashboard evidence:")

    crc_alerts = [
        alert for alert in n.get("real_alerts", [])
        if "crc" in alert.lower()
    ]

    if crc_alerts:
        for alert in crc_alerts:
            lines.append(f"- 🟡 YELLOW: {clean_alert_text(alert)}")
    else:
        lines.append("- No real CRC alerts were parsed.")

    crc_disks = []
    for d in bundle.get("disks", []):
        raw_crc = d.get("crc")
        try:
            crc_value = int(str(raw_crc).strip())
        except Exception:
            crc_value = 0
        if crc_value > 0:
            crc_disks.append((d, crc_value))

    if crc_disks:
        for d, crc_value in crc_disks:
            dev = d.get("device", "unknown")
            lines.append(
                f"- {dev} evidence: health={d.get('health')}, temp={d.get('temp')}°C, "
                f"realloc={d.get('realloc')}, pending={d.get('pending')}, "
                f"crc={crc_value}, power_on={d.get('power_on')}."
            )
    else:
        lines.append("- No disk with a non-zero CRC count was found in the parsed SMART disk table.")

    lines.append("")
    lines.append("What CRC errors usually mean:")
    lines.append("- CRC errors usually point to a communication/link issue between the drive and the controller, not automatic disk failure.")
    lines.append("- The usual causes are SATA/SAS cable, loose connection, controller/HBA port, backplane path, or unstable power.")
    lines.append("- With SMART health PASSED, reallocated sectors 0, and pending sectors 0, the current evidence points away from media/platter failure.")

    lines.append("")
    lines.append("Most likely causes:")
    lines.append("1. SATA/SAS data cable issue.")
    lines.append("2. Loose connection at the drive, backplane, controller, or HBA.")
    lines.append("3. Faulty controller/HBA/backplane port.")
    lines.append("4. Power delivery instability.")
    lines.append("5. Less common: drive interface issue, firmware issue, electrical noise, or connector heat/damage.")

    lines.append("")
    lines.append("What to check:")
    lines.append("- Monitor whether the CRC count stays at the same value or keeps increasing.")
    lines.append("- If it stays at the same value, it may be an old link event.")
    lines.append("- If it increases, power down, reseat the cable, try a known-good short cable, move to another port, and check power.")

    return {
        "lines": lines,
        "next_step": "Confirm whether the CRC count is increasing over time on the exact disk shown above. If it increases, check cable, port, backplane, controller path, and power before blaming the disk.",
        "forum_summary": "The disk shown above has CRC errors, but SMART health may still report PASSED with no reallocated or pending sectors. This usually points to a SATA/SAS link issue such as cable, port, backplane, controller path, or power stability rather than a failing disk. Monitor whether the CRC count increases. If it does, reseat or replace the cable and try another port before considering disk replacement.",
    }
