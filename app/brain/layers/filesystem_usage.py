def clean_alert_text(alert):
    text = str(alert).strip()
    for prefix in ["YELLOW:", "RED:", "INFO:"]:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def answer(bundle):
    n = bundle["normalized"]
    lines = []

    usage_alerts = [
        alert for alert in n.get("real_alerts", [])
        if "filesystem usage" in alert.lower()
    ]

    sdd = None
    for d in bundle.get("disks", []):
        if d.get("device") == "sdd":
            sdd = d
            break

    model = sdd.get("model") if sdd else "UNKNOWN"
    size = sdd.get("size") if sdd else "UNKNOWN"
    mount = sdd.get("mount") if sdd else "UNKNOWN"
    health = sdd.get("health") if sdd else "UNKNOWN"
    temp = sdd.get("temp") if sdd else "UNKNOWN"

    lines.append("- This is a filesystem usage warning question.")
    lines.append("- The answer comes from the Filesystem Usage Layer using normalized dashboard evidence.")
    lines.append("")

    lines.append("### Verdict")
    lines.append("- sdd at 100% filesystem usage is very likely a USB flash / installer / recovery device that is auto-mounted by ZimaOS/CasaOS.")
    lines.append("- Based on the current evidence, this does **not** look like your main HDD/NVMe storage pool being full.")
    lines.append("- This is likely harmless, but it still needs read-only verification before anything is unmounted, deleted, formatted, or cleaned.")
    lines.append("")

    lines.append("### Confidence")
    lines.append("- Confidence: High, based on model, size, mount path, health visibility, and device type.")
    lines.append("- Limitation: The current report strongly suggests a USB/flash device, but the exact active mount still needs host verification.")
    lines.append("")

    lines.append("### Evidence used")
    if usage_alerts:
        for alert in usage_alerts:
            lines.append(f"- 🟡 YELLOW: {clean_alert_text(alert)}")
    else:
        lines.append("- No real filesystem usage alert was parsed.")

    lines.append(f"- Device: sdd")
    lines.append(f"- Model: {model}")
    lines.append(f"- Size: {size}")
    lines.append(f"- Mount shown by dashboard: {mount}")
    lines.append(f"- Health: {health}")
    lines.append(f"- Temperature: {temp}")
    lines.append("")

    lines.append("### Why ZimaBrain thinks this")
    lines.append("- `Flash Drive` plus a size around 59.8G strongly matches a USB stick, installer media, boot media, recovery stick, or small removable drive.")
    lines.append("- `Health=UNKNOWN` and `Temp=N/A` are common for USB flash devices because they often do not expose full SMART data.")
    lines.append("- The mount path shown as `/host/var/lib/casaos_data/.media/...` looks like a ZimaOS/CasaOS auto-mounted removable media path.")
    lines.append("- The device name and mount label can appear slightly mismatched after auto-mounting, so the host mount table must be checked before touching anything.")
    lines.append("")

    lines.append("### Most likely scenarios")
    lines.append("1. ZimaOS installation USB is still plugged in.")
    lines.append("2. A recovery or boot USB is mounted.")
    lines.append("3. A small external flash drive is genuinely full.")
    lines.append("4. A transfer/backup USB is attached.")
    lines.append("5. Less common: stale mount, duplicate media path, or wrong device label.")
    lines.append("")

    lines.append("### Safe read-only commands")
    lines.append("- These commands are read-only.")
    lines.append("- Copy and paste them exactly as shown.")
    lines.append("- Share the output before unmounting, deleting, formatting, or cleaning anything.")
    lines.append("")
    lines.append("```bash")
    lines.append("lsblk -f -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,LABEL")
    lines.append("findmnt | grep -E 'sdd|sdc|media'")
    lines.append("df -h | grep -E 'sdd|sdc|media'")
    lines.append("```")
    lines.append("")

    lines.append("### How to interpret the result")
    lines.append("- If `lsblk` shows `sdd` as a removable/USB-style flash device, then the 100% warning is likely not related to your main storage.")
    lines.append("- If `findmnt` confirms it is mounted under a CasaOS/ZimaOS media path, it is likely auto-mounted removable media.")
    lines.append("- If the contents look like installer, EFI, boot, recovery, or ISO files, then 100% usage can be normal.")
    lines.append("- If it contains real user data, back it up before cleaning or formatting anything.")
    lines.append("")

    lines.append("### What not to touch")
    lines.append("- Do not delete anything from the media path until the active mount is verified.")
    lines.append("- Do not format the USB unless you have confirmed it is not needed.")
    lines.append("- Do not unmount it until you confirm what it is.")
    lines.append("- Do not assume this is affecting the main storage pool without checking the mount.")
    lines.append("")

    lines.append("### Safest next action")
    lines.append("- Run the three read-only commands above and confirm whether sdd is the ZimaOS installer/recovery USB or another removable flash drive.")

    return {
        "lines": lines,
        "next_step": "Run lsblk, findmnt, and df using the safe read-only commands. Confirm whether sdd is installer/recovery USB media before unmounting, deleting, formatting, or cleaning anything.",
        "forum_summary": "sdd is showing 100% filesystem usage, but the evidence strongly suggests it is a 59.8G Flash Drive auto-mounted by ZimaOS/CasaOS rather than one of the main HDD/NVMe storage drives. This is often normal for installer, recovery, or boot USB media. Verify with lsblk, findmnt, and df before unmounting, deleting, formatting, or cleaning anything.",
    }
