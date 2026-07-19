import re
import shlex


def _evidence(bundle, key):
    return (bundle.get("same_report_evidence", {}) or {}).get(key, "") or ""


def _mount_values(line):
    values = dict(re.findall(r'([A-Z_]+)="([^"]*)"', str(line or "")))
    if values:
        return values

    try:
        return {
            key: value
            for token in shlex.split(str(line or ""))
            if "=" in token
            for key, value in [token.split("=", 1)]
        }
    except ValueError:
        return {}


def _writable_storage_target(target):
    return (
        target == "/DATA"
        or target.startswith("/DATA/")
        or target == "/media"
        or target.startswith("/media/")
        or target == "/var/lib/casaos_data/.media"
        or target.startswith("/var/lib/casaos_data/.media/")
    )


def _unexpected_read_only_mounts(text):
    result = []

    for raw in str(text or "").splitlines():
        values = _mount_values(raw)
        target = values.get("TARGET", "")
        options = {
            item.strip().lower()
            for item in values.get("OPTIONS", "").split(",")
            if item.strip()
        }
        fstype = values.get("FSTYPE", "").lower()

        if (
            target
            and _writable_storage_target(target)
            and "ro" in options
            and fstype != "iso9660"
        ):
            result.append(raw.strip())

    return result


def answer(bundle, question):
    mounts = _evidence(bundle, "mounts")
    has_mounts = bool(mounts.strip())
    unexpected = _unexpected_read_only_mounts(mounts)

    lines = [
        "- This is a read-only storage diagnostic question.",
        "- The layer checks structured active-mount targets and mount options.",
        "",
        "### Same-report evidence",
        f"- Active mount evidence parsed: {'yes' if has_mounts else 'no'}",
        (
            "- Unexpectedly read-only writable-storage mounts: "
            f"{len(unexpected)}"
        ),
    ]

    if not has_mounts:
        lines.extend([
            "",
            "- No evidence was parsed for active mounts.",
        ])
        return {
            "lines": lines,
            "next_step": (
                "Collect structured active mount evidence before changing "
                "mount options or running filesystem repair."
            ),
            "forum_summary": (
                "Active mount evidence was unavailable, so writable-storage "
                "mount state could not be assessed."
            ),
        }

    if unexpected:
        lines.extend(["", "### Affected active mounts"])
        for item in unexpected[:20]:
            lines.append(f"- {item}")
        lines.append(
            "- These active writable-storage targets currently advertise "
            "the `ro` mount option."
        )
        next_step = (
            "Confirm the backing device, filesystem type, and recent filesystem "
            "errors for the listed mount before attempting a remount or repair."
        )
        summary = (
            f"{len(unexpected)} active DATA/media writable-storage mount(s) "
            "currently advertise the read-only option."
        )
    else:
        lines.extend([
            "",
            "- No active DATA or media writable-storage mount currently "
            "advertises the `ro` option.",
        ])
        next_step = (
            "No read-only mount repair is indicated by this snapshot. If an "
            "application still cannot write, check its bind mount, permissions, "
            "and container-visible path."
        )
        summary = (
            "Structured active-mount evidence shows no unexpectedly read-only "
            "DATA or media writable-storage mount."
        )

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": summary,
    }
