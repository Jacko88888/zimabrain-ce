from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class HardwareLayerResult:
    matched: bool
    answer: str = ""


HARDWARE_KEYWORDS = [
    "pcie",
    "pci-e",
    "pci express",
    "bifurcation",
    "burification",
    "nvme",
    "m.2",
    "dual nvme",
    "zfs",
    "mirror",
    "raid",
    "hba",
    "sata",
    "gpu",
    "graphics card",
    "10gbe",
    "2.5gbe",
    "nic",
    "ethernet card",
    "realtek",
    "intel nic",
    "usb boot",
    "boot device",
    "zimaboard",
    "zimaboard 2",
    "zimaboard2",
    "zimablade",
    "zimacube",
    "zimacube pro",
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def is_hardware_question(question: str) -> bool:
    q = _norm(question)
    return any(k in q for k in HARDWARE_KEYWORDS)


def answer_hardware_compatibility(question: str) -> HardwareLayerResult:
    q = _norm(question)

    if not is_hardware_question(q):
        return HardwareLayerResult(matched=False)

    if (
        ("zimaboard 2" in q or "zimaboard2" in q)
        and (
            "dual nvme" in q
            or "2 nvme" in q
            or "two nvme" in q
            or ("nvme" in q and "adapter" in q)
        )
        and (
            "bifurcation" in q
            or "burification" in q
            or "without" in q
            or "zfs" in q
            or "mirror" in q
        )
    ):
        return HardwareLayerResult(
            matched=True,
            answer=f"""## ❓ Question asked
### {question.strip()}

#### Verification status
@@VERIFY:PARTIALLY VERIFIED@@ ✅ PARTIALLY VERIFIED
- Active layer: Hardware Compatibility Layer
- Layer file: app/brain/layers/hardware_compatibility_layer.py

#### Direct answer / severity
The official PCIe 3.0 x4 Dual NVMe Adapter is intended to support two NVMe SSDs on ZimaBoard 2 without user-configured PCIe bifurcation.

For a ZFS mirror, do not create the mirror until both NVMe drives are confirmed visible and stable in ZimaOS.

#### Verified facts
- ZimaBoard 2 has a PCIe 3.0 x4 expansion slot.
- The official dual NVMe adapter is designed for two NVMe M.2 SSDs.
- No user BIOS bifurcation setting should be required for the official adapter path.

#### Not verified yet
- Whether this specific user has the official adapter installed.
- Whether both NVMe drives are detected by the OS.
- Whether either NVMe drive has errors, disconnects, or unstable links.
- Whether the user already has data on either drive.

#### Next safest step
Run these checks before creating any ZFS mirror:

```bash
lspci -tv
nvme list
lsblk -o NAME,SIZE,MODEL,TYPE,MOUNTPOINTS
```

Optional stability check:

```bash
dmesg | grep -Ei 'nvme|pcie|aer|reset|timeout|error'
```

#### Safe recommendation
If both NVMe drives appear correctly in nvme list and lsblk, then a ZFS mirror is technically possible.

Do not create or format any mirror until disk identity is confirmed. ZFS mirror creation can destroy existing data if the wrong devices are selected.

#### Forum-ready summary
The official ZimaBoard 2 dual NVMe adapter should support two NVMe SSDs without user-configured PCIe bifurcation. Before creating a ZFS mirror, first confirm both NVMe drives are visible with nvme list and lsblk.
""",
        )

    return HardwareLayerResult(
        matched=True,
        answer=f"""## ❓ Question asked
### {question.strip()}

#### Verification status
@@VERIFY:NOT VERIFIED@@ ❌ NOT VERIFIED
- Active layer: Hardware Compatibility Layer
- Layer file: app/brain/layers/hardware_compatibility_layer.py

#### Direct answer / severity
This is a hardware compatibility question. ZimaBrain should not guess hardware support without official hardware facts, a verified test report, or local system evidence.

#### Detected hardware topic
Possible hardware compatibility issue:
- PCIe / NVMe / SATA / NIC / GPU / HBA / USB / boot device / RAID / ZFS

#### Not verified yet
- Exact Zima device model.
- Exact accessory or PCIe card model.
- Whether the hardware is detected by ZimaOS.
- Whether kernel logs show errors.
- Whether the device is safe to use for storage, boot, VM passthrough, or RAID/ZFS.

#### Next safest step
Collect local evidence first:

```bash
lspci -nn
lsblk -o NAME,SIZE,MODEL,TYPE,MOUNTPOINTS
dmesg | grep -Ei 'pcie|nvme|sata|ahci|hba|raid|gpu|i915|nvidia|realtek|intel|usb|error|reset|timeout'
```

For NVMe-specific questions:

```bash
nvme list
```

For network card questions:

```bash
ip link
ethtool -i eth0 2>/dev/null || true
```

#### Safe recommendation
Do not recommend hardware as supported until the hardware is confirmed by official documentation, a verified test report, or local detection evidence.

#### Forum-ready summary
This is a hardware compatibility question. Please confirm the exact device/card model and provide lspci -nn, lsblk, and relevant dmesg output before relying on it for storage, boot, RAID/ZFS, or passthrough.
""",
    )
