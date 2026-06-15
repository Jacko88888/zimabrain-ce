import re


def simplify_mount_line(line):
    pairs = dict(re.findall(r'([A-Z]+)="([^"]*)"', line))

    if pairs:
        source = pairs.get("SOURCE", "")
        target = pairs.get("TARGET", "")
        fstype = pairs.get("FSTYPE", "")
        opts = pairs.get("OPTIONS", "")
        mode = "ro" if opts.startswith("ro") or ",ro" in opts else "rw"

        label = f"{source} -> {target}"
        if fstype:
            label += f" [{fstype}]"
        label += f" {mode}"
        return label.strip()

    cleaned = line.replace("│", " ").replace("├─", " ").replace("└─", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def extract_mount_lines(bundle):
    mounts_text = bundle.get("same_report_evidence", {}).get("mounts", "")
    raw_mount_lines = [line.strip() for line in mounts_text.splitlines() if line.strip()]
    mount_lines = []

    for line in raw_mount_lines:
        low = line.lower()

        if " overlay " in low or low.startswith("overlay"):
            continue
        if line.startswith('SOURCE="sysext"') or ('TARGET="/usr"' in line and 'FSTYPE="overlay"' in line):
            continue
        if "/docker/overlay2/" in low:
            continue
        if "/docker/containers/" in low:
            continue
        if "/docker/buildkit/" in low:
            continue
        if "/docker/volumes/" in low:
            continue

        if (
            "/media/" in line
            or "/DATA" in line
            or "/var/lib/casaos_data/.media" in line
            or "mergerfs" in low
            or "snapraid" in low
            or line.startswith("/dev/")
            or line.startswith('SOURCE="/dev/')
        ):
            mount_lines.append(line)

    return mount_lines


def answer(bundle):
    lines = []
    lines.append("- This is a mount / media path verification question.")
    lines.append("- The answer comes from the Storage Mount Layer using host findmnt evidence, not from visible folders alone.")
    lines.append("")
    lines.append("Active storage-related mounts from this report:")

    mount_lines = extract_mount_lines(bundle)

    if mount_lines:
        simplified_seen = set()
        shown = 0

        for line in mount_lines[:40]:
            simple = simplify_mount_line(line)
            if simple in simplified_seen:
                continue
            simplified_seen.add(simple)
            lines.append(f"- {simple}")
            shown += 1

        if len(mount_lines) > 40:
            lines.append(f"- Only showing first 40 entries out of {len(mount_lines)} parsed mount lines.")
    else:
        lines.append("- No storage-related mounts were parsed from the current host evidence.")

    lines.append("")
    lines.append("How to interpret this:")
    lines.append("- A visible folder under /media does not prove a disk is mounted there.")
    lines.append("- Use active findmnt evidence before changing Docker app paths.")
    lines.append("- Do not delete old-looking /media folders until they are confirmed not to be active mounts.")

    return {
        "lines": lines,
        "next_step": "Compare active findmnt mount paths against Docker bind paths before changing storage paths or deleting any /media folders.",
        "forum_summary": "Based on the verified host mount evidence, storage paths should be trusted only when they appear as active mounts. Do not rely on visible /media folders alone, and do not change Docker bind paths until the exact active mount source is confirmed.",
    }
