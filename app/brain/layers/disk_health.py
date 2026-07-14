def answer(bundle, severity_dot):
    n = bundle["normalized"]

    lines = []
    lines.append("- This is a disk health summary question.")
    lines.append("")
    lines.append("Disks needing attention from real values:")

    real_attention = []

    for alert in n.get("real_alerts", []):
        low = alert.lower()

        if "crc" in low:
            real_attention.append(
                f"Dashboard alert mentions CRC: {alert}. Cross-check the exact disk below before naming the device."
            )

        if "filesystem usage" in low or "100%" in low:
            real_attention.append(
                f"Dashboard alert mentions filesystem usage: {alert}. Verify the mount and contents before deleting anything."
            )

    for d in bundle.get("disks", []):
        raw_crc = d.get("crc")
        try:
            crc_value = int(str(raw_crc).strip())
        except Exception:
            crc_value = 0
        if crc_value > 0:
            dev = d.get("device", "unknown")
            detail = (
                f"{dev}: CRC errors {crc_value}. health={d.get('health')}, "
                f"realloc={d.get('realloc')}, pending={d.get('pending')}. "
                "SMART health can still pass, so check the connection path first."
            )
            real_attention.append(detail)

        if str(d.get("filesystem_usage", "")).strip() in ("100", "100%"):
            dev = d.get("device", "unknown")
            detail = (
                f"{dev}: filesystem usage 100%, health={d.get('health')}, "
                f"model={d.get('model')}, size={d.get('size')}, mount={d.get('mount')}. "
                "Verify the mount and contents before deleting anything."
            )
            real_attention.append(detail)

    if real_attention:
        for item in real_attention:
            lines.append(f"- {item}")
    else:
        lines.append("- No real disk-health attention items were parsed.")

    lines.append("")
    lines.append("Info only / unavailable SMART fields:")

    if n.get("info_alerts"):
        for alert in n["info_alerts"]:
            lines.append(f"- {severity_dot(alert)}")
    else:
        lines.append("- No unsupported/N/A SMART values were parsed.")

    lines.append("")
    lines.append("Disks that look OK from available fields:")

    ok_lines = []

    for d in bundle.get("disks", []):
        device = d.get("device", "")
        health = d.get("health", "")
        temp = d.get("temp", "")
        model = d.get("model", "")

        try:
            crc_value = int(str(d.get("crc")).strip())
        except Exception:
            crc_value = 0

        if crc_value > 0:
            ok_lines.append(
                f"{device}: health={health}, temp={temp}°C, realloc={d.get('realloc')}, "
                f"pending={d.get('pending')}, crc={d.get('crc')}. CRC is the attention item."
            )
        elif health.upper() in ["PASSED", "OK"]:
            ok_lines.append(f"{device}: health={health}, temp={temp}°C, model={model}.")

    if ok_lines:
        for item in ok_lines:
            lines.append(f"- {item}")
    else:
        lines.append("- No OK disk list was parsed.")

    return {
        "lines": lines,
        "next_step": "Handle real disk warnings first: confirm whether the exact disk with CRC errors is increasing, then verify any 100% filesystem usage mount and contents. Treat NVMe N/A SMART values as unavailable data, not failures.",
        "forum_summary": "Based on the verified dashboard evidence, disk attention items should be tied to the exact device shown in parsed SMART evidence. NVMe N/A SMART values are informational only. Confirm whether any CRC count is increasing and verify any 100% filesystem usage mount before deleting or replacing anything.",
    }
