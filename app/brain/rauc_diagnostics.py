import re


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SLOT_HEADER_RE = re.compile(
    r"^(?P<indent>\s*)(?:(?P<marker>[xo]|[^\w\s\[]+)\s+)?"
    r"\[(?P<name>[^\]]+)\](?:\s+\((?P<meta>.*)\))?\s*$",
    re.IGNORECASE,
)
SLOT_NAME_RE = re.compile(r"^(?P<class>.+)\.(?P<index>\d+)$")
SLOT_REF_RE = re.compile(
    r"^(?P<name>[^\s(]+)(?:\s+\((?P<bootname>[^)]+)\))?\s*$"
)
KNOWN_STATES = {"booted", "active", "inactive", "missing"}


def _clean(value):
    return ANSI_RE.sub("", str(value or "")).rstrip()


def _slot_ref(value):
    clean = str(value or "").strip()
    match = SLOT_REF_RE.match(clean)
    if not match:
        return {"raw": clean, "name": clean, "bootname": ""}
    return {
        "raw": clean,
        "name": match.group("name").strip(),
        "bootname": (match.group("bootname") or "").strip(),
    }


def _slot_identity(name):
    match = SLOT_NAME_RE.match(str(name or "").strip())
    if not match:
        return str(name or "").strip(), None
    return match.group("class"), int(match.group("index"))


def parse_status(text):
    raw = _clean(text)
    result = {
        "raw": raw,
        "evidence_available": False,
        "compatible": "",
        "variant": "",
        "booted": {"raw": "", "name": "", "bootname": ""},
        "activated": {"raw": "", "name": "", "bootname": ""},
        "slots": [],
        "errors": [],
    }
    if not raw.strip():
        return result

    section = ""
    current_slot = None
    current_group = None

    for original in raw.splitlines():
        line = original.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("===") and stripped.endswith("==="):
            section = stripped.strip("= ").lower()
            current_slot = None
            continue

        low = stripped.lower()
        if low.startswith("error:") or "failed to obtain rauc status" in low:
            result["errors"].append(stripped)

        if stripped.startswith("Compatible:"):
            result["compatible"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("Variant:"):
            result["variant"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("Booted from:"):
            result["booted"] = _slot_ref(stripped.split(":", 1)[1])
            continue
        if stripped.startswith("Activated:") and (
            section == "bootloader" or not result["activated"]["name"]
        ):
            result["activated"] = _slot_ref(stripped.split(":", 1)[1])
            continue

        header = SLOT_HEADER_RE.match(line)
        if header:
            name = header.group("name").strip()
            slot_class, slot_index = _slot_identity(name)
            meta_parts = [
                item.strip() for item in (header.group("meta") or "").split(",")
                if item.strip()
            ]
            state = next(
                (item.lower() for item in reversed(meta_parts)
                 if item.lower() in KNOWN_STATES),
                "",
            )
            non_state = [item for item in meta_parts if item.lower() not in KNOWN_STATES]
            marker = (header.group("marker") or "").lower()
            indent = len(header.group("indent") or "")
            parent = ""
            if not marker and current_group and indent > current_group["indent"]:
                parent = current_group["name"]

            current_slot = {
                "name": name,
                "class": slot_class,
                "index": slot_index,
                "marker": marker,
                "device": non_state[0] if non_state else "",
                "type": non_state[1] if len(non_state) > 1 else "",
                "state": state,
                "bootname": "",
                "boot_status": "",
                "mounted": "",
                "parent": parent,
                "raw_header": stripped,
            }
            result["slots"].append(current_slot)
            if marker or current_group is None or indent <= current_group["indent"]:
                current_group = {"name": name, "indent": indent}
            continue

        if current_slot and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            if key == "bootname":
                current_slot["bootname"] = value
            elif key in {"boot_status", "boot-status"}:
                current_slot["boot_status"] = value.lower()
            elif key == "mounted":
                current_slot["mounted"] = value
            elif key == "parent":
                current_slot["parent"] = value
            elif key == "state" and value.lower() in KNOWN_STATES:
                current_slot["state"] = value.lower()

    result["evidence_available"] = bool(
        result["compatible"]
        or result["booted"]["name"]
        or result["activated"]["name"]
        or result["slots"]
    )
    return result


def _slot_by_name(parsed, name):
    return next(
        (slot for slot in parsed.get("slots", []) if slot["name"] == name),
        None,
    )


def _bootable_slot_groups(parsed):
    """Return top-level A/B groups, excluding shared/unbootable partitions."""
    booted_name = parsed.get("booted", {}).get("name", "")
    activated_name = parsed.get("activated", {}).get("name", "")
    return [
        slot for slot in parsed.get("slots", [])
        if not slot.get("parent")
        and (
            slot.get("marker")
            or slot.get("bootname")
            or slot.get("boot_status")
            or slot.get("name") in {booted_name, activated_name}
        )
    ]


def _same_group_slot_with_status(parsed, reference):
    _, index = _slot_identity(reference)
    if index is None:
        return None
    candidates = [
        slot for slot in parsed.get("slots", [])
        if slot.get("index") == index and slot.get("boot_status")
    ]
    return candidates[0] if candidates else None


def _active_rootfs(parsed):
    rootfs = [slot for slot in parsed.get("slots", []) if slot["class"] == "rootfs"]
    direct = next(
        (slot for slot in rootfs if slot["state"] in {"booted", "active"}),
        None,
    )
    if direct:
        return direct

    booted_name = parsed.get("booted", {}).get("name", "")
    booted_slot = _slot_by_name(parsed, booted_name)
    if booted_slot and booted_slot.get("parent"):
        parent = _slot_by_name(parsed, booted_slot["parent"])
        if parent and parent["class"] == "rootfs":
            return parent

    _, booted_index = _slot_identity(booted_name)
    if booted_index is not None:
        return next(
            (slot for slot in rootfs if slot.get("index") == booted_index),
            None,
        )
    return None


def assess_status(text):
    parsed = parse_status(text)
    assessment = {
        **parsed,
        "active_rootfs": None,
        "inactive_slots": [],
        "booted_status": "",
        "bad_slots": [],
        "issues": [],
        "limitations": [],
        "verification": "NOT VERIFIED",
        "severity": "UNKNOWN",
        "healthy": False,
        "conclusion": "RAUC status could not be verified from the current evidence.",
    }

    if not parsed["evidence_available"]:
        if parsed["errors"]:
            assessment["limitations"].extend(parsed["errors"])
        else:
            assessment["limitations"].append(
                "No parseable RAUC status evidence was captured."
            )
        return assessment

    slots = parsed["slots"]
    booted_name = parsed["booted"]["name"]
    activated_name = parsed["activated"]["name"]
    booted_slot = _slot_by_name(parsed, booted_name)
    booted_status_slot = (
        booted_slot
        if booted_slot and booted_slot.get("boot_status")
        else _same_group_slot_with_status(parsed, booted_name)
    )
    assessment["booted_status"] = (
        booted_status_slot.get("boot_status", "") if booted_status_slot else ""
    )
    assessment["active_rootfs"] = _active_rootfs(parsed)
    slot_groups = _bootable_slot_groups(parsed)
    assessment["inactive_slots"] = [
        slot for slot in slot_groups if slot["state"] == "inactive"
    ]
    assessment["bad_slots"] = [slot for slot in slots if slot["boot_status"] == "bad"]

    if not parsed["compatible"]:
        assessment["limitations"].append("RAUC Compatible was not captured.")
    if not booted_name:
        assessment["limitations"].append("RAUC booted slot was not captured.")
    if not activated_name:
        assessment["limitations"].append("RAUC activated slot was not captured.")
    if not slots:
        assessment["limitations"].append("RAUC slot-state entries were not captured.")
    elif booted_name and not booted_slot:
        assessment["limitations"].append(
            f"Booted slot {booted_name} was not matched to a parsed slot entry."
        )
    if booted_name and not assessment["booted_status"]:
        assessment["limitations"].append(
            "Boot status for the currently booted slot group was not captured."
        )

    indices = sorted({
        slot["index"] for slot in slot_groups if slot["index"] is not None
    })
    if slot_groups and len(indices) < 2:
        assessment["limitations"].append(
            "Only one RAUC slot index was parsed; a second A/B slot was not verified."
        )

    if booted_slot and booted_slot["state"] == "inactive":
        assessment["issues"].append({
            "level": "HIGH",
            "kind": "inconsistent_booted_state",
            "message": f"Booted slot {booted_name} is marked inactive.",
        })

    for slot in slots:
        if slot["state"] == "missing":
            assessment["issues"].append({
                "level": "HIGH" if slot["name"] in {booted_name, activated_name} else "WARNING",
                "kind": "missing_slot",
                "message": f"RAUC slot {slot['name']} is reported missing.",
            })

    for slot in assessment["bad_slots"]:
        same_current_group = (
            slot["name"] in {booted_name, activated_name}
            or (
                slot.get("index") is not None
                and slot.get("index") in {
                    _slot_identity(booted_name)[1],
                    _slot_identity(activated_name)[1],
                }
            )
        )
        assessment["issues"].append({
            "level": "HIGH" if same_current_group else "WARNING",
            "kind": "bad_boot_status",
            "message": (
                f"RAUC slot {slot['name']} has boot status bad"
                + (" in the current/activated slot group." if same_current_group else ".")
            ),
        })

    if booted_name and activated_name and booted_name != activated_name:
        assessment["issues"].append({
            "level": "WARNING",
            "kind": "activation_mismatch",
            "message": (
                f"Booted slot {booted_name} differs from activated slot {activated_name}. "
                "This may be an intentional next-boot selection and is not automatically a failure."
            ),
        })

    if assessment["issues"]:
        assessment["verification"] = (
            "PARTIALLY VERIFIED" if assessment["limitations"] else "VERIFIED"
        )
        assessment["severity"] = (
            "HIGH" if any(item["level"] == "HIGH" for item in assessment["issues"])
            else "WARNING"
        )
        assessment["conclusion"] = (
            "RAUC status needs attention. A possible update-slot problem was verified, "
            "but the evidence does not by itself prove an update failure."
            + (
                " Some RAUC fields are also incomplete."
                if assessment["limitations"] else ""
            )
        )
    elif assessment["limitations"]:
        assessment["verification"] = "PARTIALLY VERIFIED"
        assessment["severity"] = "INCOMPLETE"
        assessment["conclusion"] = (
            "RAUC status is only partially verified. No bad slot was verified, but the "
            "available evidence is incomplete."
        )
    else:
        assessment["verification"] = "VERIFIED"
        assessment["severity"] = "HEALTHY"
        assessment["healthy"] = True
        assessment["conclusion"] = (
            "RAUC status looks healthy. Both slot groups are present and the currently "
            "booted slot is marked as good."
        )

    return assessment


def slot_label(slot):
    if not slot:
        return "not verified"
    bootname = f" ({slot['bootname']})" if slot.get("bootname") else ""
    return f"{slot['name']}{bootname}"


def reference_label(reference):
    if not reference or not reference.get("name"):
        return "not verified"
    bootname = f" ({reference['bootname']})" if reference.get("bootname") else ""
    return f"{reference['name']}{bootname}"


def inventory_fingerprint(assessment):
    return ",".join(
        sorted(
            f"{slot['name']}:{slot['state'] or 'unknown'}:{slot['boot_status'] or 'unknown'}"
            for slot in assessment.get("slots", [])
        )
    )


def critical_finding(assessment):
    issues = assessment.get("issues", []) or []
    if not issues:
        return None
    level = "RED" if any(item["level"] == "HIGH" for item in issues) else "YELLOW"
    return {
        "level": level,
        "title": "RAUC update-slot state needs attention",
        "detail": "\n".join(item["message"] for item in issues),
        "why": (
            "RAUC reported a bad, missing or inconsistent slot condition. This may affect "
            "an update or fallback path, but it does not by itself prove an update failure."
        ),
        "next": (
            "Verify the booted and activated selections and the exact slot evidence before "
            "marking, switching, rolling back or reinstalling any slot."
        ),
    }
