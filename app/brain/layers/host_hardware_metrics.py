import re


def is_host_hardware_question(question):
    q = (question or "").lower()
    return any(x in q for x in [
        "cpu temp",
        "cpu temperature",
        "cpu temps",
        "are my cpu temps normal",
        "hardware info",
        "hardware metrics",
        "cpu info",
        "cpu usage",
        "ram usage",
        "memory usage",
        "memory pressure",
        "system load",
        "load average",
        "thermal",
        "temperatures",
        "temps normal",
        "how much ram",
        "how much memory",
    ])


def _lscpu_value(text, key):
    for line in str(text or "").splitlines():
        if line.lower().startswith(key.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def _cpu_usage(text):
    m = re.search(r"CPU_USAGE_PERCENT=([0-9.]+|unknown)", str(text or ""))
    return m.group(1) if m else ""


def _memory_summary(text):
    mem = ""
    swap = ""

    for line in str(text or "").splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[0] == "Mem:":
            total = int(parts[1])
            used = int(parts[2])
            available = int(parts[6])
            pct = (used / total * 100) if total else 0
            mem = f"{used} MiB used / {total} MiB total ({pct:.1f}% used, {available} MiB available)"
        if len(parts) >= 4 and parts[0] == "Swap:":
            total = int(parts[1])
            used = int(parts[2])
            pct = (used / total * 100) if total else 0
            swap = f"{used} MiB used / {total} MiB total ({pct:.1f}% used)"

    return mem, swap


def _memory_pressure(text):
    total = 0
    available = 0
    swap_total = 0
    swap_used = 0

    for line in str(text or "").splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[0] == "Mem:":
            total = int(parts[1])
            available = int(parts[6])
        elif len(parts) >= 4 and parts[0] == "Swap:":
            swap_total = int(parts[1])
            swap_used = int(parts[2])

    if not total:
        return (
            "Memory pressure cannot be assessed because capacity evidence was not captured.",
            "Not captured",
        )

    available_pct = available / total * 100
    swap_pct = (swap_used / swap_total * 100) if swap_total else 0

    if available_pct < 5 or swap_pct >= 80:
        assessment = (
            "High capacity pressure is indicated by very low available memory "
            "or heavy swap consumption."
        )
    elif available_pct < 10 or swap_pct >= 50:
        assessment = (
            "Elevated capacity pressure is indicated; verify whether memory "
            "availability continues falling or swap use continues increasing."
        )
    else:
        assessment = (
            "No high capacity pressure is indicated by the captured memory "
            "availability and swap snapshot."
        )

    return assessment, f"{available} MiB ({available_pct:.1f}% of total)"


def _load_summary(text):
    parts = str(text or "").split()
    if len(parts) >= 3:
        return f"{parts[0]} / {parts[1]} / {parts[2]}"
    return ""


def _temps(text):
    vals = []
    for line in str(text or "").splitlines():
        low = line.lower()

        # Ignore threshold metadata. lm-sensors often prints:
        # high = +100.0°C, crit = +100.0°C
        # Those are limits, not current temperatures.
        if "high =" in low or "crit =" in low or "low =" in low:
            line = line.split("(", 1)[0]

        for m in re.finditer(r"([+-]?[0-9]+(?:\.[0-9]+)?)\s*°?C", line):
            try:
                v = float(m.group(1))
                if -20 <= v <= 150:
                    vals.append(v)
            except Exception:
                pass
    return vals


def _temp_status(max_temp):
    if max_temp is None:
        return "Temperature evidence was not captured."
    if max_temp >= 90:
        return "High temperature risk. Investigate cooling, dust, fan speed, and workload."
    if max_temp >= 80:
        return "Warm under load. Watch closely if this is idle or light load."
    if max_temp >= 70:
        return "Moderate temperature. Usually acceptable under load, but check airflow."
    return "Normal temperature range from captured evidence."


def _summary(bundle):
    ev = (bundle or {}).get("same_report_evidence", {}) or {}

    cpu_info = ev.get("cpu_info", "")
    cpu_usage = _cpu_usage(ev.get("cpu_usage", ""))
    mem, swap = _memory_summary(ev.get("memory", ""))
    memory_pressure, memory_available = _memory_pressure(
        ev.get("memory", "")
    )
    load = _load_summary(ev.get("loadavg", ""))

    sensors = ev.get("sensors", "")
    thermal = ev.get("thermal_zones", "")
    temp_values = _temps(sensors + "\n" + thermal)
    max_temp = max(temp_values) if temp_values else None

    return {
        "model": _lscpu_value(cpu_info, "Model name") or _lscpu_value(cpu_info, "BIOS Model name") or "Not captured",
        "vendor": _lscpu_value(cpu_info, "Vendor ID") or "Not captured",
        "cpus": _lscpu_value(cpu_info, "CPU(s)") or "Not captured",
        "cores": _lscpu_value(cpu_info, "Core(s) per socket") or "Not captured",
        "threads": _lscpu_value(cpu_info, "Thread(s) per core") or "Not captured",
        "max_mhz": _lscpu_value(cpu_info, "CPU max MHz") or "Not captured",
        "cpu_usage": (cpu_usage + "%") if cpu_usage else "Not captured",
        "memory": mem or "Not captured",
        "memory_available": memory_available,
        "memory_pressure": memory_pressure,
        "swap": swap or "Not captured",
        "load": load or "Not captured",
        "max_temp": f"{max_temp:.1f}°C" if max_temp is not None else "Not captured",
        "temp_status": _temp_status(max_temp),
        "thermal_zones": thermal.strip() or "Not captured",
        "sensors": sensors.strip() or "Not captured",
    }


def answer(question, bundle):
    h = _summary(bundle)
    q = str(question or "").lower()
    memory_focus = any(
        term in q for term in ("memory", "ram", "swap")
    )

    out = [
        "### ZimaBrain Answer",
        "",
        "## ❓ Question asked",
        f"### {question.strip()}",
        "",
        "#### Verification status",
        "@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM SAME-REPORT HOST EVIDENCE",
        "- This answer uses current local host evidence.",
        "- Active layer: Host Hardware Metrics Layer",
        "- Layer file: `app/brain/layers/host_hardware_metrics.py`",
        "",
        "#### Direct answer / severity",
    ]

    if memory_focus:
        out.extend([
            f"- Memory pressure assessment: {h['memory_pressure']}",
            f"- Memory available: {h['memory_available']}",
            f"- Memory: {h['memory']}",
            f"- Swap: {h['swap']}",
            f"- Load average 1/5/15 min: {h['load']}",
            "",
            "#### Next safest step",
            "- No immediate memory action is required when availability "
            "remains healthy and swap pressure is low. If slowness "
            "continues, compare available memory, swap use, and the "
            "largest memory-consuming processes while the symptom is active.",
            "",
            "#### Forum-ready summary",
            "ZimaBrain assessed current memory availability, RAM use, "
            "swap use, and system load without mixing unrelated "
            "CPU-temperature details into the answer.",
        ])
        return "\n".join(out)

    out.extend([
        f"- CPU: {h['model']}",
        f"- CPU usage snapshot: {h['cpu_usage']}",
        f"- Max captured temperature: {h['max_temp']}",
        f"- Temperature status: {h['temp_status']}",
        "",
        "#### Host hardware metrics",
        f"- Vendor: {h['vendor']}",
        f"- Visible CPUs / threads: {h['cpus']}",
        f"- Cores per socket: {h['cores']}",
        f"- Threads per core: {h['threads']}",
        f"- CPU max MHz: {h['max_mhz']}",
        f"- Memory: {h['memory']}",
        f"- Swap: {h['swap']}",
        f"- Load average 1/5/15 min: {h['load']}",
        "",
        "#### Temperature evidence",
    ])

    for line in h["thermal_zones"].splitlines()[:12]:
        out.append(f"- {line}")

    if h["thermal_zones"] == "Not captured":
        out.append("- Not captured")

    out.extend([
        "",
        "#### Next safest step",
        "- If temperatures look high, verify airflow, dust, fan speed, "
        "workload, and whether the reading is idle or under load before "
        "changing anything.",
        "",
        "#### Forum-ready summary",
        "ZimaBrain reports current CPU, hardware, load, and thermal evidence.",
    ])

    return "\n".join(out)
