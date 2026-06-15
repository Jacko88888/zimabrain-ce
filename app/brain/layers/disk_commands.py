def answer(bundle):
    lines = []

    lines.append("- This is a safe disk command question.")
    lines.append("- The answer comes from the Disk Commands Layer.")
    lines.append("")

    lines.append("### Verdict")
    lines.append("- Use read-only commands first.")
    lines.append("- These commands check disk identity, active mounts, filesystem usage, and SMART visibility without changing anything.")
    lines.append("- Do not repair, unmount, format, delete, rebuild, or clean anything until the outputs are reviewed.")
    lines.append("")

    lines.append("### Safe read-only commands")
    lines.append("- Copy and paste these commands exactly as shown.")
    lines.append("- Share the output before making any storage changes.")
    lines.append("")
    lines.append("```bash")
    lines.append("lsblk -f -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,LABEL")
    lines.append("findmnt | grep -E '/DATA|/media|sda|sdb|sdc|sdd|nvme'")
    lines.append("df -h")
    lines.append("```")
    lines.append("")

    lines.append("### Optional SMART health read")
    lines.append("- Use this only to read SMART health information.")
    lines.append("- If a USB device does not support SMART, that does not automatically mean the device has failed.")
    lines.append("")
    lines.append("```bash")
    lines.append("for d in /dev/sd? /dev/nvme?n1; do echo \"===== $d =====\"; smartctl -H -A \"$d\" 2>/dev/null | head -80; done")
    lines.append("```")
    lines.append("")

    lines.append("### What the commands verify")
    lines.append("- `lsblk` confirms disk names, size, filesystem, labels, and mountpoints.")
    lines.append("- `findmnt` confirms which paths are active mounts.")
    lines.append("- `df -h` confirms filesystem usage.")
    lines.append("- `smartctl` checks disk health attributes where supported.")
    lines.append("")

    lines.append("### What not to touch")
    lines.append("- Do not delete `/media` folders until `findmnt` confirms they are not active mounts.")
    lines.append("- Do not format any disk until the exact device is verified.")
    lines.append("- Do not rebuild RAID, SnapRAID, or mergerfs until disk identity and pool config are verified.")

    return {
        "lines": lines,
        "next_step": "Run the safe read-only disk commands and review the output before changing mounts, formatting disks, or repairing storage.",
        "forum_summary": "Start with read-only disk checks: lsblk for device identity, findmnt for active mounts, df -h for usage, and smartctl for SMART health where supported. Do not delete, unmount, format, rebuild, or repair anything until the exact disk and mount paths are verified.",
    }
