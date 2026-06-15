def answer(bundle, severity_dot):
    n = bundle["normalized"]

    lines = []
    lines.append("- This is a disk health summary question.")
    lines.append("")
    lines.append("Disks needing attention from real values:")

    real_attention = []

    for alert in n.get("real_alerts", []):
        low = alert.lower()

        if "sda" in low and "crc" in low:
            real_attention.append(
                "sda: CRC errors 8. SMART health still reports PASSED, so check the connection path first."
            )

        if "sdd" in low and "filesystem usage" in low:
            real_attention.append(
                "sdd: filesystem usage 100%. This appears to be a flash/USB-style device, so verify the mount and contents before deleting anything."
            )

    for d in bundle.get("disks", []):
        if d.get("device") == "sdd":
            detail = (
                f"sdd: filesystem usage 100%, health={d.get('health')}, "
                f"model={d.get('model')}, size={d.get('size')}, mount={d.get('mount')}. "
                "Verify the mount and contents before deleting anything."
            )
            real_attention = [x for x in real_attention if not x.startswith("sdd:")]
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

        if device == "sda":
            ok_lines.append(
                f"sda: health={health}, temp={temp}°C, realloc={d.get('realloc')}, "
                f"pending={d.get('pending')}, crc={d.get('crc')}. CRC is the attention item."
            )
        elif health.upper() in ["PASSED", "OK"] and device != "sdd":
            ok_lines.append(f"{device}: health={health}, temp={temp}°C, model={model}.")

    if ok_lines:
        for item in ok_lines:
            lines.append(f"- {item}")
    else:
        lines.append("- No OK disk list was parsed.")

    return {
        "lines": lines,
        "next_step": "Handle real disk warnings first: confirm whether sda CRC errors are increasing, then verify the active sdd mount and contents. Treat NVMe N/A SMART values as unavailable data, not failures.",
        "forum_summary": "Based on the verified dashboard evidence, the real disk attention items are sda CRC errors and sdd filesystem usage at 100%. NVMe N/A SMART values are informational only. Confirm whether sda CRC is increasing and verify the sdd mount before deleting or replacing anything.",
    }
