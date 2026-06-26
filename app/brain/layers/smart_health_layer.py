from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SmartLayerResult:
    matched: bool
    answer: str = ""


CODE_FENCE = chr(96) * 3


SMART_KEYWORDS = [
    "smart",
    "smartctl",
    "disk health",
    "drive health",
    "hdd health",
    "ssd health",
    "nvme health",
    "media errors",
    "critical warning",
    "unsafe shutdown",
    "unsafe shutdowns",
    "crc error",
    "crc errors",
    "pending sector",
    "reallocated sector",
    "offline uncorrectable",
    "error log entries",
    "error log",
    "num_err_log_entries",
    "is my disk healthy",
    "are my disks healthy",
    "which disks are healthy",
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def is_smart_question(question: str) -> bool:
    q = _norm(question)

    if any(k in q for k in SMART_KEYWORDS):
        return True

    # NVMe health wording often appears without the word SMART.
    if ("nvme" in q or "nvme0n1" in q or "nvme1n1" in q or "nvme2n1" in q or "nvme3n1" in q) and (
        "healthy" in q
        or "health" in q
        or "error log" in q
        or "error entries" in q
        or "media error" in q
        or "critical warning" in q
        or "unsafe shutdown" in q
    ):
        return True

    return False


def _get_text(bundle: dict) -> str:
    parts = []

    if not isinstance(bundle, dict):
        return ""

    for key in ("raw_report", "report_text", "dashboard_report", "report"):
        parts.append(str(bundle.get(key, "") or ""))

    evidence = bundle.get("same_report_evidence", {}) or {}
    for key in ("smart", "smart_health", "nvme", "nvme_smart", "lsblk"):
        parts.append(str(evidence.get(key, "") or ""))

    return "\n".join(parts)


def _parse_int(raw: str) -> int | None:
    try:
        return int(str(raw).replace(",", "").strip())
    except Exception:
        return None


def _smart_attr_value(line: str) -> int | None:
    parts = line.split()
    if not parts:
        return None
    return _parse_int(parts[-1])


def _collect_findings(text: str):
    critical = []
    warning = []
    ok = []

    current = "unknown"
    current_kind = ""
    smart_passed_devices = set()
    smart_attr_seen = {}
    smart_visibility_limited = set()
    controller_visibility_hints = set()

    def mark_attr(dev: str):
        if not dev or dev == "unknown":
            return
        smart_attr_seen[dev] = smart_attr_seen.get(dev, 0) + 1

    def mark_visibility_limited(dev: str, reason: str):
        if not dev or dev == "unknown":
            return
        key = (dev, reason)
        if key in smart_visibility_limited:
            return
        smart_visibility_limited.add(key)
        warning.append(f"{dev}: SMART visibility limited - {reason}")

    for line in str(text or "").splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        m_dev = re.search(r"===== (SMART|NVME)\s+([^=]+?)\s*=====", stripped, re.I)
        if m_dev:
            current_kind = m_dev.group(1).upper()
            current = m_dev.group(2).strip()
            continue

        if any(x in lower for x in ("raid", "sas", "hba", "megaraid", "silicon image", "sat", "scsi")):
            if current and current != "unknown":
                controller_visibility_hints.add(current)

        if "smart overall-health self-assessment test result:" in lower:
            if "passed" in lower:
                smart_passed_devices.add(current)
                ok.append(f"{current}: SMART overall-health PASSED")
            elif "failed" in lower:
                critical.append(f"{current}: SMART overall-health FAILED")
            else:
                warning.append(f"{current}: SMART overall-health unclear: {stripped}")

        if "smart status not supported" in lower or "attribute check" in lower:
            mark_visibility_limited(current, "status is incomplete / attribute-based only")

        if "unknown usb bridge" in lower or "please specify device type with the -d option" in lower or "specify device type" in lower:
            mark_visibility_limited(current, "bridge/controller requires a smartctl device type option")

        if "smart support is: unavailable" in lower or "smart support is: disabled" in lower:
            mark_visibility_limited(current, stripped)

        if "smart value unavailable" in lower or " n/a" in lower or "n/a (" in lower:
            if any(x in lower for x in ("pending", "reallocated", "crc", "offline", "smart")):
                mark_visibility_limited(current, "detailed SMART fields are unavailable / N/A")

        if "critical_warning" in lower:
            val = _parse_int(stripped.split(":")[-1])
            if val is not None:
                if val == 0:
                    ok.append(f"{current}: NVMe critical_warning = 0")
                else:
                    critical.append(f"{current}: NVMe critical_warning = {val}")

        if "media_errors" in lower:
            val = _parse_int(stripped.split(":")[-1])
            if val is not None:
                if val == 0:
                    ok.append(f"{current}: NVMe media_errors = 0")
                else:
                    critical.append(f"{current}: NVMe media_errors = {val}")

        if "num_err_log_entries" in lower:
            val = _parse_int(stripped.split(":")[-1])
            if val is not None and val > 0:
                warning.append(f"{current}: NVMe error log entries = {val}")

        if "unsafe_shutdowns" in lower:
            val = _parse_int(stripped.split(":")[-1])
            if val is not None and val > 0:
                warning.append(f"{current}: NVMe unsafe_shutdowns = {val}")

        for attr in (
            "Reallocated_Sector_Ct",
            "Current_Pending_Sector",
            "Offline_Uncorrectable",
            "Reported_Uncorrect",
            "UDMA_CRC_Error_Count",
            "CRC_Error_Count",
            "Command_Timeout",
        ):
            if attr.lower() in lower:
                val = _smart_attr_value(stripped)
                if val is None:
                    mark_visibility_limited(current, f"{attr} value unavailable")
                    continue

                mark_attr(current)

                if attr in ("UDMA_CRC_Error_Count", "CRC_Error_Count", "Command_Timeout"):
                    if val > 0:
                        warning.append(f"{current}: {attr} = {val}")
                    else:
                        ok.append(f"{current}: {attr} = 0")
                else:
                    if val > 0:
                        critical.append(f"{current}: {attr} = {val}")
                    else:
                        ok.append(f"{current}: {attr} = 0")

    for dev in sorted(smart_passed_devices):
        if smart_attr_seen.get(dev, 0) == 0:
            mark_visibility_limited(
                dev,
                "SMART PASSED was visible, but detailed attributes were not parsed; health is only partially verified",
            )

    for dev in sorted(controller_visibility_hints):
        if dev in smart_passed_devices and smart_attr_seen.get(dev, 0) == 0:
            mark_visibility_limited(
                dev,
                "possible RAID/SAS/HBA/controller passthrough limitation",
            )

    return critical, warning, ok


def _bullets(items):
    if not items:
        return "- None parsed."

    deduped = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)

    return "\n".join(f"- {x}" for x in deduped[:30])


def _question_devices(question):
    q = str(question or "").lower()
    found = []

    for m in re.findall(r"/dev/(sd[a-z]+|nvme\d+n\d+|mmcblk\d+)", q):
        dev = f"/dev/{m}"
        if dev not in found:
            found.append(dev)

    for m in re.findall(r"\b(sd[a-z]+|nvme\d+n\d+|mmcblk\d+)\b", q):
        dev = f"/dev/{m}"
        if dev not in found:
            found.append(dev)

    return found


def _device_items(items, dev):
    dev = str(dev or "")
    bare = dev.replace("/dev/", "")
    prefixes = (f"{dev}:", f"{bare}:")
    return [x for x in items if str(x).startswith(prefixes)]


def _specific_disk_focus(question, critical, warning, ok):
    devices = _question_devices(question)
    if not devices:
        return ""

    lines = []
    target_set = set(devices) | {d.replace("/dev/", "") for d in devices}

    for dev in devices:
        dev_critical = _device_items(critical, dev)
        dev_warning = _device_items(warning, dev)
        dev_ok = _device_items(ok, dev)
        crc_items = [x for x in dev_critical + dev_warning + dev_ok if "crc" in x.lower()]

        lines.append(f"#### Specific disk focus: {dev}")

        if crc_items:
            zero_crc = [x for x in crc_items if re.search(r"=\s*0\b", x)]
            nonzero_crc = [x for x in crc_items if not re.search(r"=\s*0\b", x)]
            if nonzero_crc:
                lines.append("- CRC evidence was found for the disk mentioned in the question:")
                lines.extend(f"  - {x}" for x in nonzero_crc)
            elif zero_crc:
                lines.append(f"- No CRC errors are shown on {dev} in the collected evidence.")
                lines.extend(f"  - {x}" for x in zero_crc)
        else:
            lines.append(f"- No CRC counter evidence was parsed for {dev} in the current report.")

        if dev_critical:
            lines.append("- Critical SMART attributes for the disk mentioned in the question:")
            lines.extend(f"  - {x}" for x in dev_critical)
        elif dev_warning:
            lines.append("- Warning SMART attributes for the disk mentioned in the question:")
            lines.extend(f"  - {x}" for x in dev_warning)
        else:
            lines.append(f"- No critical SMART media-failure indicators were parsed for {dev}.")

        lines.append("")

    other_critical = []
    for x in critical:
        name = str(x).split(":", 1)[0]
        if name not in target_set and name.replace("/dev/", "") not in target_set:
            other_critical.append(x)

    if other_critical:
        lines.append("#### Other disk risks found separately")
        lines.append("- The disk named in the question is not the only item checked.")
        lines.append("- Other disks with higher-risk SMART attributes:")
        lines.extend(f"  - {x}" for x in other_critical[:12])
        lines.append("")

    return "\n".join(lines).rstrip()


def answer_smart_health(question: str, bundle: dict | None = None) -> SmartLayerResult:
    if not is_smart_question(question):
        return SmartLayerResult(matched=False)

    text = _get_text(bundle or {})
    critical, warning, ok = _collect_findings(text)

    if not text.strip():
        status = "NOT VERIFIED"
        title = "❌ NOT VERIFIED"
        direct = "This is a SMART / disk health question, but no SMART or NVMe health evidence was available in the current report."
    elif critical:
        status = "VERIFIED"
        title = "✅ VERIFIED"
        direct = "SMART/NVMe evidence found disk health risk indicators that need attention."
    elif warning:
        status = "PARTIALLY VERIFIED"
        title = "✅ PARTIALLY VERIFIED"
        direct = "SMART/NVMe evidence does not show confirmed media failure, but warnings, limited SMART visibility, or unverifiable devices were found."
    else:
        status = "VERIFIED"
        title = "✅ VERIFIED"
        direct = "SMART/NVMe evidence did not show obvious disk failure indicators in the parsed fields."

    specific_focus = _specific_disk_focus(question, critical, warning, ok)

    commands = (
        f"{CODE_FENCE}bash\n"
        "for d in /dev/sda /dev/sdb /dev/sdc /dev/sdd; do echo \"===== SMART $d =====\"; smartctl -H -A \"$d\" 2>&1 | sed -n '1,140p'; done\n"
        "for n in /dev/nvme0n1 /dev/nvme1n1 /dev/nvme2n1 /dev/nvme3n1; do echo \"===== NVME $n =====\"; nvme smart-log \"$n\" 2>&1 | sed -n '1,90p'; done\n"
        f"{CODE_FENCE}"
    )

    return SmartLayerResult(
        matched=True,
        answer=f"""## ❓ Question asked
### {question.strip()}

#### Verification status
@@VERIFY:{status}@@ {title}
- Active layer: SMART / NVMe Health Layer
- Layer file: app/brain/layers/smart_health_layer.py

#### Direct answer / severity
{direct}

{specific_focus + chr(10) + chr(10) if specific_focus else ""}#### Critical findings
{_bullets(critical)}

#### Warnings / context
{_bullets(warning)}

#### Healthy / normal parsed evidence
{_bullets(ok)}

#### Next safest step
Collect complete host SMART/NVMe evidence before replacing disks or creating RAID/ZFS:

{commands}

#### Safe recommendation
Do not call a drive fully healthy from SMART PASSED alone. Check reallocated sectors, pending sectors, offline uncorrectable sectors, CRC errors, NVMe critical warnings, media errors, unsafe shutdowns, and error log entries. If detailed SMART attributes are N/A or missing, treat health as only partially verified. RAID, SAS/HBA, USB bridge, or controller passthrough can hide SMART detail.

#### Forum-ready summary
SMART/NVMe health should be verified from host evidence. PASSED is useful, but it is not enough by itself. If detailed SMART attributes are unavailable or N/A, treat the result as limited visibility, not confirmed healthy and not confirmed failed. Review critical attributes, controller passthrough, and NVMe error fields before deciding a disk is healthy or safe for RAID/ZFS.
""",
    )
