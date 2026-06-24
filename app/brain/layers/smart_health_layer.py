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

    for key in ("raw_report", "report_text", "dashboard_report"):
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

    for line in str(text or "").splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        m_dev = re.search(r"===== (SMART|NVME)\s+([^=]+?)\s*=====", stripped, re.I)
        if m_dev:
            current = m_dev.group(2).strip()
            continue

        if "smart overall-health self-assessment test result:" in lower:
            if "passed" in lower:
                ok.append(f"{current}: SMART overall-health PASSED")
            elif "failed" in lower:
                critical.append(f"{current}: SMART overall-health FAILED")
            else:
                warning.append(f"{current}: SMART overall-health unclear: {stripped}")

        if "smart status not supported" in lower or "attribute check" in lower:
            warning.append(f"{current}: SMART status is incomplete / attribute-based only")

        if "unknown usb bridge" in lower or "please specify device type with the -d option" in lower:
            warning.append(f"{current}: SMART cannot verify this USB bridge without a device type option")

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
            "UDMA_CRC_Error_Count",
        ):
            if attr.lower() in lower:
                val = _smart_attr_value(stripped)
                if val is None:
                    continue

                if attr == "UDMA_CRC_Error_Count":
                    if val > 0:
                        warning.append(f"{current}: {attr} = {val}")
                    else:
                        ok.append(f"{current}: {attr} = 0")
                else:
                    if val > 0:
                        critical.append(f"{current}: {attr} = {val}")
                    else:
                        ok.append(f"{current}: {attr} = 0")

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
        direct = "SMART/NVMe evidence does not show confirmed media failure, but warnings or unverifiable devices were found."
    else:
        status = "VERIFIED"
        title = "✅ VERIFIED"
        direct = "SMART/NVMe evidence did not show obvious disk failure indicators in the parsed fields."

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

#### Critical findings
{_bullets(critical)}

#### Warnings / context
{_bullets(warning)}

#### Healthy / normal parsed evidence
{_bullets(ok)}

#### Next safest step
Collect complete host SMART/NVMe evidence before replacing disks or creating RAID/ZFS:

{commands}

#### Safe recommendation
Do not call a drive fully healthy from SMART PASSED alone. Check reallocated sectors, pending sectors, offline uncorrectable sectors, CRC errors, NVMe critical warnings, media errors, unsafe shutdowns, and error log entries.

#### Forum-ready summary
SMART/NVMe health should be verified from host evidence. PASSED is useful, but it is not enough by itself. Review critical attributes and NVMe error fields before deciding a disk is healthy or safe for RAID/ZFS.
""",
    )
