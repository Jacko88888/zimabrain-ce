#!/usr/bin/env python3
import sqlite3
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, "/app")
if "/app" not in Path(__file__).resolve().as_posix():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))

from brain import answer_builder
from brain import dashboard
from brain import health_memory
from brain import intent_policy
from brain import rauc_diagnostics
from brain import router
from brain.layers import zimaos_regression


HEALTHY_KERNEL_LAYOUT = """=== System Info ===
Compatible: zimaos-zimacube
Variant:
Booted from: kernel.1 (B)

=== Bootloader ===
Activated: kernel.1 (B)

=== Slot States ===
o [rootfs.1] (/dev/mmcblk0p5, ext4, booted)
        bootname: B
        mounted: /
        boot status: good
    [kernel.1] (/dev/mmcblk0p3, raw, active)
        bootname: B
        parent: rootfs.1

x [rootfs.0] (/dev/mmcblk0p4, ext4, inactive)
        bootname: A
        boot status: good
    [kernel.0] (/dev/mmcblk0p2, raw, inactive)
        bootname: A
        parent: rootfs.0
"""


HEALTHY_ROOTFS_LAYOUT = """=== System Info ===
Compatible: Test Config
Variant:
Booted from: rootfs.0 (A)

=== Bootloader ===
Activated: rootfs.0 (A)

=== Slot States ===
x [rootfs.0] (/dev/root, raw, booted)
        bootname: A
        mounted: /
        boot status: good
    [appfs.0] (/dev/app0, raw, active)

o [rootfs.1] (/dev/root1, raw, inactive)
        bootname: B
        boot status: good
    [appfs.1] (/dev/app1, raw, inactive)
"""


HEALTHY_ZIMAOS_LAYOUT = """=== System Info ===
Compatible:  zimaos-zimacube
Variant:
Booted from: kernel.1 (B)

=== Bootloader ===
Activated: kernel.1 (B)

=== Slot States ===
  [boot.0] (/dev/disk/by-partlabel/casaos-boot, vfat, inactive)

○ [kernel.0] (/dev/disk/by-partlabel/casaos-kernel0, raw, inactive)
      bootname: A
      boot status: good
    [rootfs.0] (/dev/disk/by-partlabel/casaos-system0, raw, inactive)

⏺ [kernel.1] (/dev/disk/by-partlabel/casaos-kernel1, raw, booted)
      bootname: B
      boot status: good
    [rootfs.1] (/dev/disk/by-partlabel/casaos-system1, raw, active)
"""


def replace_once(text, old, new):
    assert old in text
    return text.replace(old, new, 1)


def bundle(rauc):
    return {
        "report": "synthetic current report with RAUC evidence",
        "normalized": {},
        "critical_findings": [],
        "same_report_evidence": {
            "host_os": 'PRETTY_NAME="ZimaOS 1.7.0"\nVERSION_ID="1.7.0"',
            "kernel": "6.18.9",
            "uptime": "up 2 days",
            "rauc": rauc,
            "cmdline": "quiet rauc.slot=B",
            "mounts": "",
            "docker_access": "",
        },
    }


healthy = rauc_diagnostics.assess_status(HEALTHY_KERNEL_LAYOUT)
assert healthy["verification"] == "VERIFIED"
assert healthy["healthy"]
assert healthy["severity"] == "HEALTHY"
assert healthy["compatible"] == "zimaos-zimacube"
assert healthy["booted"]["name"] == "kernel.1"
assert healthy["activated"]["name"] == "kernel.1"
assert healthy["active_rootfs"]["name"] == "rootfs.1"
assert healthy["booted_status"] == "good"
assert {slot["name"] for slot in healthy["inactive_slots"]} == {"rootfs.0"}
assert "Both slot groups are present" in healthy["conclusion"]
assert rauc_diagnostics.critical_finding(healthy) is None
assert not any(
    item["title"] == "RAUC update-slot state needs attention"
    for item in dashboard.evaluate_critical_same_report({"rauc": HEALTHY_KERNEL_LAYOUT})
)

official_layout = rauc_diagnostics.assess_status(HEALTHY_ROOTFS_LAYOUT)
assert official_layout["healthy"]
assert official_layout["booted"]["name"] == "rootfs.0"
assert official_layout["active_rootfs"]["name"] == "rootfs.0"

zimaos_layout = rauc_diagnostics.assess_status(HEALTHY_ZIMAOS_LAYOUT)
assert zimaos_layout["verification"] == "VERIFIED"
assert zimaos_layout["healthy"]
assert zimaos_layout["severity"] == "HEALTHY"
assert zimaos_layout["booted"]["name"] == "kernel.1"
assert zimaos_layout["activated"]["name"] == "kernel.1"
assert zimaos_layout["active_rootfs"]["name"] == "rootfs.1"
assert zimaos_layout["booted_status"] == "good"
assert [slot["name"] for slot in zimaos_layout["inactive_slots"]] == ["kernel.0"]
zimaos_slots = {slot["name"]: slot for slot in zimaos_layout["slots"]}
assert zimaos_slots["rootfs.0"]["parent"] == "kernel.0"
assert zimaos_slots["rootfs.1"]["parent"] == "kernel.1"
assert zimaos_slots["boot.0"]["parent"] == ""

zimaos_layer = zimaos_regression.answer(bundle(HEALTHY_ZIMAOS_LAYOUT), "sudo rauc status")
zimaos_layer_text = "\n".join(zimaos_layer["lines"])
assert zimaos_layer["trust_state"] == "VERIFIED"
assert "Inactive slot(s): kernel.0 (A)" in zimaos_layer_text
assert "Boot status: good" in zimaos_layer_text
assert "parent=kernel.0" in zimaos_layer_text
assert "parent=kernel.1" in zimaos_layer_text

layer = zimaos_regression.answer(bundle(HEALTHY_KERNEL_LAYOUT), "sudo rauc status")
layer_text = "\n".join(layer["lines"])
assert layer["trust_state"] == "VERIFIED"
assert "### RAUC Status" in layer_text
assert "Compatible: zimaos-zimacube" in layer_text
assert "Booted slot: kernel.1 (B)" in layer_text
assert "Active rootfs: rootfs.1 (B)" in layer_text
assert "Activated slot: kernel.1 (B)" in layer_text
assert "Inactive slot(s): rootfs.0 (A)" in layer_text
assert "Boot status: good" in layer_text
assert "Severity: HEALTHY" in layer_text
assert "RAUC status looks healthy" in layer_text
assert "No RAUC repair or slot switch is indicated" in layer["next_step"]

integrated = answer_builder.answer_question(
    "Which RAUC slot is booted and is it healthy?",
    bundle(HEALTHY_KERNEL_LAYOUT),
    lambda value: [],
    lambda value: value,
    lambda value: value,
)
assert "@@VERIFY:VERIFIED@@" in integrated
assert "Active layer: ZimaOS Update / Regression Layer" in integrated
assert "Booted slot: kernel.1 (B)" in integrated

booted_bad_text = replace_once(
    HEALTHY_KERNEL_LAYOUT,
    "boot status: good",
    "boot status: bad",
)
booted_bad = rauc_diagnostics.assess_status(booted_bad_text)
assert booted_bad["verification"] == "VERIFIED"
assert booted_bad["severity"] == "HIGH"
assert not booted_bad["healthy"]
assert any(item["kind"] == "bad_boot_status" for item in booted_bad["issues"])
assert "does not by itself prove an update failure" in booted_bad["conclusion"]
assert rauc_diagnostics.critical_finding(booted_bad)["level"] == "RED"
assert any(
    item["title"] == "RAUC update-slot state needs attention" and item["level"] == "RED"
    for item in dashboard.evaluate_critical_same_report({"rauc": booted_bad_text})
)

inactive_bad_text = replace_once(
    HEALTHY_KERNEL_LAYOUT,
    "bootname: A\n        boot status: good",
    "bootname: A\n        boot status: bad",
)
inactive_bad = rauc_diagnostics.assess_status(inactive_bad_text)
assert inactive_bad["severity"] == "WARNING"
assert any(
    item["kind"] == "bad_boot_status" and "rootfs.0" in item["message"]
    for item in inactive_bad["issues"]
)
assert rauc_diagnostics.critical_finding(inactive_bad)["level"] == "YELLOW"

mismatch_text = replace_once(
    HEALTHY_KERNEL_LAYOUT,
    "Activated: kernel.1 (B)",
    "Activated: kernel.0 (A)",
)
mismatch = rauc_diagnostics.assess_status(mismatch_text)
assert mismatch["severity"] == "WARNING"
assert any(item["kind"] == "activation_mismatch" for item in mismatch["issues"])
assert "not automatically a failure" in "\n".join(
    item["message"] for item in mismatch["issues"]
)

missing_text = replace_once(
    HEALTHY_KERNEL_LAYOUT,
    "[kernel.0] (/dev/mmcblk0p2, raw, inactive)",
    "[kernel.0] (/dev/mmcblk0p2, raw, missing)",
)
missing = rauc_diagnostics.assess_status(missing_text)
assert missing["severity"] == "WARNING"
assert any(item["kind"] == "missing_slot" for item in missing["issues"])

partial_text = """=== System Info ===
Compatible: zimaos-zimacube
Booted from: kernel.1 (B)
"""
partial = rauc_diagnostics.assess_status(partial_text)
assert partial["verification"] == "PARTIALLY VERIFIED"
assert not partial["healthy"]
assert partial["issues"] == []
assert "No bad slot was verified" in partial["conclusion"]
partial_layer = zimaos_regression.answer(bundle(partial_text), "Show RAUC slots")
assert partial_layer["trust_state"] == "PARTIALLY VERIFIED"
assert "Confirm the incomplete RAUC" in partial_layer["next_step"]

unavailable = rauc_diagnostics.assess_status("")
assert unavailable["verification"] == "NOT VERIFIED"
unavailable_layer = zimaos_regression.answer(bundle(""), "What is the RAUC status?")
assert unavailable_layer["trust_state"] == "NOT VERIFIED"
assert "fresh read-only `rauc status`" in unavailable_layer["next_step"]

route_questions = [
    "sudo rauc status",
    "What is the current RAUC slot status?",
    "Which RAUC slot is booted and is it healthy?",
    "Are both update slots present and good?",
    "Is the inactive RAUC slot missing or bad?",
    "Show the booted and activated slots.",
]
for question in route_questions:
    assert router.classify(question)["_intent"] == "zimaos_regression", question
    policy = intent_policy.classify(question)
    assert policy["handler"] == "zimaos_regression", question
    assert policy["memory_key"] == "system:status:rauc", question

for question in [
    "Is it safe to rollback with this RAUC status?",
    "Should I run rauc status mark-good?",
]:
    assert router.classify(question)["_intent"] == "zimaos_update_safety", question
    assert intent_policy.classify(question)["handler"] == "zimaos_update_safety", question

assert router.classify("Which PCIe slots are present?")["_intent"] != "zimaos_regression"

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / "timeline.sqlite")
    common = {
        "boot_id": "boot-a",
        "host_os": 'PRETTY_NAME="ZimaOS 1.6.2"\nVERSION_ID="1.6.2"',
        "kernel": "6.18.9",
        "rauc": HEALTHY_KERNEL_LAYOUT,
    }
    health_memory.record_health_scan(
        common, "v1.6.0-beta", db, "2026-07-20 10:00:00"
    )
    health_memory.record_health_scan({
        **common,
        "boot_id": "boot-b",
        "host_os": 'PRETTY_NAME="ZimaOS 1.7.0"\nVERSION_ID="1.7.0"',
        "rauc": booted_bad_text,
    }, "v1.6.0-beta", db, "2026-07-21 10:00:00")
    health_memory.record_health_scan({
        **common,
        "boot_id": "boot-c",
        "host_os": 'PRETTY_NAME="ZimaOS 1.7.0"\nVERSION_ID="1.7.0"',
    }, "v1.6.0-beta", db, "2026-07-22 10:00:00")

    with sqlite3.connect(db) as con:
        classifications = [
            row[0] for row in con.execute("""
                SELECT classification FROM health_events
                WHERE category = 'system'
                  AND entity_key = 'host'
                  AND metric = 'rauc_slot_health'
                ORDER BY id
            """).fetchall()
        ]
    assert classifications == ["baseline", "new_issue", "recovered"]

    update_history = health_memory.system_update_history(db, limit=10)
    transition = next(
        item for item in update_history["transitions"]
        if any(change["current"] == "1.7.0" for change in item["changes"])
    )
    assert transition["classification"] == "post_update_attention"
    assert any(
        item["category"] == "system" and item["metric"] == "rauc_slot_health"
        for item in transition["issues"]
    )
    assert "does not prove" in transition["causality_note"]

print("RESULT: PASS (RAUC parsing, health, routing, verification, timeline)")
