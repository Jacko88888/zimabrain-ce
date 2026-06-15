def _disk_type(name, model):
    n = (name or "").lower()
    m = (model or "").lower()

    if n.startswith("nvme"):
        return "NVMe"
    if "flash" in m or "usb" in m:
        return "USB / removable"
    if n.startswith("sd"):
        return "SATA / USB disk"
    return "Disk"


def answer(bundle):
    lines = []

    disks = bundle.get("disks", [])

    lines.append("- This is a disk inventory / drive count question.")
    lines.append("- The answer comes from the Disk Inventory Layer using parsed dashboard disk evidence.")
    lines.append("")

    lines.append("### Disk count")
    if not disks:
        lines.append("- No disks were parsed from the current dashboard report.")
        return {
            "lines": lines,
            "next_step": "Refresh dashboard evidence and confirm the disk table is present.",
            "forum_summary": "No disk inventory was parsed from the current report. Refresh the evidence and confirm the disk table is available.",
        }

    total = len(disks)
    nvme = 0
    sata_or_usb = 0
    removable = 0
    mounted = 0
    not_mounted = 0
    passed = 0
    unknown = 0

    for d in disks:
        name = d.get("device") or d.get("name") or ""
        model = d.get("model", "")
        dtype = _disk_type(name, model)

        if dtype == "NVMe":
            nvme += 1
        elif dtype == "USB / removable":
            removable += 1
        else:
            sata_or_usb += 1

        mount = d.get("mount", "") or ""
        if mount and mount.lower() != "not mounted":
            mounted += 1
        else:
            not_mounted += 1

        health = (d.get("health", "") or "").upper()
        if health == "PASSED":
            passed += 1
        elif health == "UNKNOWN":
            unknown += 1

    lines.append(f"- Total disks/devices parsed: {total}")
    lines.append(f"- NVMe devices: {nvme}")
    lines.append(f"- SATA / USB disk devices: {sata_or_usb}")
    lines.append(f"- USB / removable devices: {removable}")
    lines.append(f"- Mounted: {mounted}")
    lines.append(f"- Not mounted: {not_mounted}")
    lines.append(f"- SMART passed: {passed}")
    lines.append(f"- SMART unknown / not available: {unknown}")

    lines.append("")
    lines.append("### Disk list")
    for d in disks:
        name = d.get("device") or d.get("name") or "unknown"
        model = d.get("model", "unknown")
        size = d.get("size", "unknown")
        health = d.get("health", "unknown")
        temp = d.get("temp", "N/A")
        mount = d.get("mount", "not mounted")
        crc = d.get("crc", "N/A")
        pending = d.get("pending", "N/A")
        realloc = d.get("realloc", "N/A")
        dtype = _disk_type(name, model)

        lines.append(
            f"- {name}: type={dtype}, model={model}, size={size}, health={health}, "
            f"temp={temp}, crc={crc}, pending={pending}, realloc={realloc}, mount={mount}"
        )

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- NVMe and SATA disks are your main storage candidates.")
    lines.append("- Flash/ISO-style devices may be installer, recovery, or removable media.")
    lines.append("- A disk showing `not mounted` is detected by the system but not currently mounted as storage.")
    lines.append("- A `PASSED` SMART result is good, but CRC/pending/reallocated values still matter.")

    return {
        "lines": lines,
        "next_step": "Use this disk inventory as the baseline, then inspect any disk with CRC errors, unknown SMART, not mounted state, or unexpected media path.",
        "forum_summary": "The disk inventory layer lists all parsed disks, counts them, separates NVMe/SATA/removable devices, and shows health, mount path, CRC, pending, and reallocated values. This is the first check before changing storage paths or troubleshooting apps.",
    }
