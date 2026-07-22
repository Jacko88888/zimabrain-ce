#!/usr/bin/env python3
import copy
import json
import sqlite3
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, "/app")
if "/app" not in Path(__file__).resolve().as_posix():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))

from brain import answer_builder
from brain import bind_mount_permissions
from brain import health_memory
from brain import intent_policy
from brain import router
from brain.layers import container_bind_mount_permissions


def record(**overrides):
    value = {
        "container": "plex",
        "source": "/media/Expansion_1/Movies",
        "destination": "/Movies",
        "bind_rw": True,
        "role": "media",
        "configured_user": "",
        "environment": {"PUID": "1000", "PGID": "1000"},
        "runtime_uid": 0,
        "runtime_gid": 0,
        "runtime_groups": [0],
        "effective_uid": 1000,
        "effective_gid": 1000,
        "identity_source": "PUID/PGID environment",
        "stat": {
            "evidence_available": True,
            "exists": True,
            "mode": "755",
            "symbolic": "drwxr-xr-x",
            "uid": 531,
            "gid": 0,
            "type": "directory",
        },
        "mount": {
            "evidence_available": True,
            "source": "/dev/sda2",
            "target": "/media/Expansion_1",
            "fstype": "exfat",
            "options": "rw,uid=531,gid=0,fmask=0022,dmask=0022",
        },
        "acl": {"available": False, "named_entries": False, "text": ""},
        "persistence": {
            "searched": ["/etc/fstab"],
            "matches": [],
            "source_verified": False,
        },
        "active_users": {
            "collected": True,
            "text": "/media/Expansion_1: root kernel mount\n  4123 root docker",
        },
        "live_remount": {"attempted": True, "result": "failed/unsupported"},
        "write_test": {
            "attempted": True,
            "result": "permission denied",
            "evidence": "touch: Permission denied",
        },
        "evidence_available": True,
    }
    value.update(overrides)
    return value


def evidence(*records):
    return {"collected": True, "records": list(records), "limitations": []}


def bundle(*records):
    return {
        "report": "synthetic current report with container permission evidence",
        "normalized": {},
        "critical_findings": [],
        "same_report_evidence": {
            "bind_mount_permissions": evidence(*records),
        },
    }


exfat = bind_mount_permissions.assess_record(record())
assert exfat["classification"] == "filesystem_mount_mask_restriction"
assert exfat["verification"] == "VERIFIED"
assert exfat["severity"] == "HIGH"
assert exfat["host_read_only"] is False
assert exfat["bind_read_only"] is False
assert exfat["mode_write_allowed"] is False
assert "read/write" in exfat["explanation"]
assert "does not grant write access" in exfat["explanation"]

host_ro_record = record()
host_ro_record["mount"] = dict(host_ro_record["mount"], options="ro,uid=531,gid=0")
host_ro = bind_mount_permissions.assess_record(host_ro_record)
assert host_ro["classification"] == "host_mount_read_only"
assert host_ro["verification"] == "VERIFIED"

bind_ro = bind_mount_permissions.assess_record(record(bind_rw=False))
assert bind_ro["classification"] == "docker_bind_read_only"
assert bind_ro["verification"] == "VERIFIED"

posix_record = record()
posix_record["mount"] = dict(
    posix_record["mount"], fstype="ext4", options="rw,relatime"
)
posix_record["acl"] = {"available": True, "named_entries": False, "text": ""}
posix = bind_mount_permissions.assess_record(posix_record)
assert posix["classification"] == "numeric_uid_gid_mismatch"
assert posix["verification"] == "VERIFIED"

posix_untested_record = copy.deepcopy(posix_record)
posix_untested_record["write_test"] = {"attempted": False, "result": "not tested"}
posix_untested = bind_mount_permissions.assess_record(posix_untested_record)
assert posix_untested["classification"] == "numeric_uid_gid_mismatch"
assert posix_untested["verification"] == "PARTIALLY VERIFIED"

acl_record = copy.deepcopy(posix_record)
acl_record["acl"] = {"available": False, "named_entries": False, "text": ""}
acl = bind_mount_permissions.assess_record(acl_record)
assert acl["classification"] == "acl_or_directory_permission_restriction"
assert acl["verification"] == "PARTIALLY VERIFIED"

write_success_record = record()
write_success_record["stat"] = dict(
    write_success_record["stat"], mode="775", gid=1000
)
write_success_record["write_test"] = {
    "attempted": True,
    "result": "success",
    "evidence": "test file created and removed",
}
write_success = bind_mount_permissions.assess_record(write_success_record)
assert write_success["classification"] == "application_level_restriction_possible"
assert not write_success["issue"]
assert "application-level" in write_success["explanation"]

layer = container_bind_mount_permissions.answer(
    bundle(record()),
    "Why can Plex read but not delete files?",
)
layer_text = "\n".join(layer["lines"])
assert layer["trust_state"] == "VERIFIED"
assert "Container: plex" in layer_text
assert "/media/Expansion_1/Movies -> /Movies" in layer_text
assert "Docker bind access: read/write" in layer_text
assert "Filesystem: exfat" in layer_text
assert "fmask=0022,dmask=0022" in layer_text
assert "531:0 mode=755" in layer_text
assert "1000:1000 (PUID/PGID environment)" in layer_text
assert "filesystem_mount_mask_restriction" in layer_text
assert "failed/unsupported; no remount success is assumed" in layer_text
assert "recursive chmod/chown is not an appropriate correction" in layer_text
assert "Do not change PUID/PGID" in layer_text
assert "Do not force-unmount" in layer_text
assert "Persistent ZimaOS mount-management source: not verified" in layer_text
assert "No persistent correction is claimed" in layer_text

untested = record()
untested["write_test"] = {"attempted": False, "result": "not tested"}
untested["live_remount"] = {"attempted": False, "result": "not tested"}
probe_layer = container_bind_mount_permissions.answer(
    bundle(untested),
    "Can Plex write to this media folder?",
)
probe_text = "\n".join(probe_layer["lines"])
assert probe_layer["trust_state"] == "PARTIALLY VERIFIED"
assert "Optional temporary verification" in probe_text
assert "docker exec -u 1000:1000 plex" in probe_text
assert ".zimabrain-permission-test" in probe_text
assert "trap" in probe_text and "rm -f" in probe_text

unknown_layer = container_bind_mount_permissions.answer(
    {
        "report": "report",
        "same_report_evidence": {
            "bind_mount_permissions": {"collected": True, "records": []}
        },
    },
    "Can a container write to this drive?",
)
assert unknown_layer["trust_state"] == "NOT VERIFIED"
assert "No actionable storage bind" in "\n".join(unknown_layer["lines"])

healthy_unrelated = record(
    container="unrelated-db",
    source="/DATA/AppData/unrelated/data",
    destination="/var/lib/data",
    role="storage",
    stat={
        "evidence_available": True,
        "exists": True,
        "mode": "775",
        "symbolic": "drwxrwxr-x",
        "uid": 1000,
        "gid": 1000,
        "type": "directory",
    },
    mount={
        "evidence_available": True,
        "source": "/dev/nvme0n1p8",
        "target": "/DATA",
        "fstype": "ext4",
        "options": "rw,relatime",
    },
    acl={"available": True, "named_entries": False, "text": ""},
    write_test={"attempted": False, "result": "not tested"},
)
generic_layer = container_bind_mount_permissions.answer(
    bundle(record(), healthy_unrelated),
    "Why does my container get permission denied on a USB drive?",
)
generic_text = "\n".join(generic_layer["lines"])
assert generic_layer["trust_state"] == "PARTIALLY VERIFIED"
assert "Candidate container: plex" in generic_text
assert "Container: unrelated-db" not in generic_text
assert "leads, not a verified match" in generic_text
assert "Optional temporary verification" not in generic_text
assert "Confirm the exact failing container name" in generic_layer["next_step"]

integrated = answer_builder.answer_question(
    "Why can Plex read but not delete files?",
    bundle(record()),
    lambda value: [],
    lambda value: value,
    lambda value: value,
)
assert "@@VERIFY:VERIFIED@@" in integrated
assert "Active layer: Container Bind-Mount Permission Diagnostics Layer" in integrated
assert "filesystem_mount_mask_restriction" in integrated

route_questions = [
    "Why can Plex read but not delete files?",
    "Why does my container get permission denied on a USB drive?",
    "Can Emby write to this media folder?",
    "Is this Docker volume mounted read-only?",
    "Why can the Files app delete files but my container cannot?",
    "Check permissions between this container and its mounted storage",
    "A Docker app can read but cannot rename files on an NTFS disk",
    "Can dropbridge write to /media?",
]
for question in route_questions:
    route = router.classify(question)
    policy = intent_policy.classify(question)
    assert route["_intent"] == "container_bind_mount_permissions", question
    assert policy["handler"] == "container_bind_mount_permissions", question
    assert policy["memory_key"] == "containers:diagnose:bind-permissions", question

assert router.classify("smb permission denied")["_intent"] == "permissions_ownership_diag"
assert router.classify("drive is read only")["_intent"] == "read_only_storage_diag"
assert router.classify("Plex cannot see my media files")["_intent"] != "container_bind_mount_permissions"
assert router.classify("Can root write to /media?")["_intent"] != "container_bind_mount_permissions"

dropbridge_media = record(
    container="dropbridge",
    source="/media",
    destination="/media",
)
dropbridge_data = record(
    container="dropbridge",
    source="/DATA/dropbridge/incoming",
    destination="/data/incoming",
)
focused_records = bind_mount_permissions.records_for_question(
    bind_mount_permissions.assess_evidence(evidence(dropbridge_media, dropbridge_data)),
    "Can dropbridge write to /media?",
)
assert len(focused_records) == 1
assert focused_records[0]["source"] == "/media"

explicit_integrated = answer_builder.answer_question(
    "Can dropbridge write to /media?",
    bundle(dropbridge_media, dropbridge_data),
    lambda value: [],
    lambda value: value,
    lambda value: value,
)
assert "Active layer: Container Bind-Mount Permission Diagnostics Layer" in explicit_integrated
assert "Files / AppData / Media Same-Report Verifier" not in explicit_integrated


# Collector remains read-only, bounded and correlates config/runtime identity.
commands = []


def fake_run(command, timeout=12):
    commands.append(command)
    if command.startswith("docker inspect --format"):
        return json.dumps({
            "Name": "/plex",
            "Config": {
                "User": "",
                "Env": ["PUID=1000", "PGID=1000", "UMASK=022"],
            },
            "State": {"Pid": 4242},
        })
    if "===PID 4242===" in command:
        return "===PID 4242===\nUid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\nGroups:\t0"
    if "---STAT---" in command and "Expansion_1" in command:
        return """---STAT---
exists=yes mode=755 symbolic=drwxr-xr-x uid=531 gid=0 type=directory
---FINDMNT---
SOURCE=\"/dev/sda2\" TARGET=\"/media/Expansion_1\" FSTYPE=\"exfat\" OPTIONS=\"rw,uid=531,gid=0,fmask=0022,dmask=0022\"
---ACL---
tool=unavailable"""
    if "---STAT---" in command and "AppData" in command:
        return """---STAT---
exists=yes mode=755 symbolic=drwxr-xr-x uid=1000 gid=1000 type=directory
---FINDMNT---
SOURCE=\"/dev/nvme0n1p8\" TARGET=\"/DATA\" FSTYPE=\"btrfs\" OPTIONS=\"rw,relatime\"
---ACL---
tool=available
user::rwx
group::r-x
other::r-x"""
    if command.startswith("fuser -vm"):
        return "/media/Expansion_1: root kernel mount\n  4242 root docker"
    if "/etc/fstab" in command:
        return "FILE|/etc/fstab"
    return ""


collected = bind_mount_permissions.collect_bind_mount_permission_evidence(
    "plex|/media/Expansion_1/Movies->/Movies:True;/DATA/AppData/plex/config->/config:True;|",
    fake_run,
)
assert collected["collected"]
assert len(collected["records"]) == 2
media_record = next(item for item in collected["records"] if item["role"] == "media")
config_record = next(item for item in collected["records"] if item["role"] == "configuration")
assert media_record["effective_uid"] == 1000
assert media_record["effective_gid"] == 1000
assert media_record["mount"]["fstype"] == "exfat"
assert media_record["active_users"]["collected"]
assert config_record["stat"]["uid"] == 1000
joined_commands = "\n".join(commands)
for forbidden in ("touch ", "rm -", "mount -o remount", "umount", "chmod", "chown"):
    assert forbidden not in joined_commands, forbidden
assert "find /DATA" not in joined_commands


# Existing health timeline: issue baseline -> persistent -> recovered.
with tempfile.TemporaryDirectory() as tmp:
    db_path = str(Path(tmp) / "trends.sqlite")
    issue = record()
    first = health_memory.record_health_scan(
        {"bind_mount_permissions": evidence(issue)},
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-22 10:00:00",
    )
    second = health_memory.record_health_scan(
        {"bind_mount_permissions": evidence(issue)},
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-22 11:00:00",
    )
    fixed = record()
    fixed["stat"] = dict(fixed["stat"], mode="775", gid=1000)
    fixed["write_test"] = {
        "attempted": True,
        "result": "success",
        "evidence": "created and removed",
    }
    third = health_memory.record_health_scan(
        {"bind_mount_permissions": evidence(fixed)},
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-22 12:00:00",
    )
    assert first["classifications"].get("historical_baseline", 0) >= 1
    assert second["classifications"].get("persistent", 0) >= 1
    assert third["classifications"].get("recovered", 0) >= 1
    with sqlite3.connect(db_path) as con:
        rows = con.execute("""
            SELECT classification FROM health_events
            WHERE category='container_mount' AND metric='permission_state'
            ORDER BY id
        """).fetchall()
    assert [row[0] for row in rows] == [
        "historical_baseline", "persistent", "recovered"
    ]


print("RESULT: PASS (container bind permissions, filesystem causes, safety, routing, timeline)")
