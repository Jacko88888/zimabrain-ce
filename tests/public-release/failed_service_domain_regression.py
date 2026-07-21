#!/usr/bin/env python3
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/app")
if "/app" not in Path(__file__).resolve().as_posix():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))

from brain import health_memory
from brain import answer_builder
from brain import intent_policy
from brain import router
from brain import service_diagnostics
from brain.layers import failed_units
from brain.layers import trend_alerts


def path(path, source="ExecStart", exists=True, executable=True,
         requires_executable=True):
    return {
        "path": path,
        "source": source,
        "exists": exists,
        "executable": executable,
        "readable": exists,
        "requires_executable": requires_executable,
        "broken_symlink": False,
        "evidence_available": True,
        "stat": "",
    }


def detail(unit="alpha-watchdog.service", primary_state="active",
           primary_available=True, paths=None, status="1", journal="",
           fragment="/etc/systemd/system/alpha-watchdog.service"):
    primary = {
        "unit": "alpha.service",
        "properties": {
            "Id": "alpha.service",
            "LoadState": "loaded",
            "ActiveState": primary_state,
            "SubState": "running" if primary_state == "active" else primary_state,
            "Result": "success" if primary_state == "active" else "exit-code",
        },
        "raw_show": f"Id=alpha.service\nActiveState={primary_state}",
        "evidence_available": primary_available,
    }
    return {
        "unit": unit,
        "failed_line": f"{unit} loaded failed failed test helper",
        "properties": {
            "Id": unit,
            "LoadState": "loaded",
            "ActiveState": "failed",
            "SubState": "failed",
            "Result": "exit-code",
            "ExecMainStatus": status,
            "FragmentPath": fragment,
            "ExecStart": "",
            "PartOf": "alpha.service" if "alpha" in unit else "",
        },
        "raw_show": f"Id={unit}\nActiveState=failed\nExecMainStatus={status}",
        "journal": journal,
        "paths": paths or [],
        "primary_candidates": ["alpha.service"],
        "primary": primary,
        "evidence_available": True,
    }


def answer_for(details, failed=True, question="Which helper services failed?"):
    raw = ""
    if failed:
        raw = "\n".join(item["failed_line"] for item in details)
    bundle = {
        "same_report_evidence": {
            "failed_units": raw,
            "failed_unit_details": details,
            "failed_unit_details_collected": True,
        }
    }
    return failed_units.answer(bundle, lambda value: value, question)


active = answer_for([detail(primary_state="active")])
active_text = "\n".join(active["lines"])
assert active["trust_state"] == "VERIFIED"
assert "Related primary service: alpha.service" in active_text
assert "Current primary-service state: active/running" in active_text
assert "Current outage indicated: no" in active_text
assert "No current primary-service outage was verified" in active_text
assert "Severity: LOWERED WARNING" in active_text
assert service_diagnostics.critical_finding(
    service_diagnostics.assess_detail(detail(primary_state="active"))
)["level"] == "YELLOW"

integrated_bundle = {
    "report": "synthetic current report",
    "normalized": {},
    "critical_findings": [],
    "same_report_evidence": {
        "failed_units": detail(primary_state="active")["failed_line"],
        "failed_unit_details": [detail(primary_state="active")],
        "failed_unit_details_collected": True,
    },
}
integrated_answer = answer_builder.answer_question(
    "Which watchdog failed while its primary service stayed active?",
    integrated_bundle,
    lambda bundle: [],
    lambda level: level,
    lambda text: text,
)
assert "@@VERIFY:VERIFIED@@" in integrated_answer
assert "Active layer: Failed Units Layer" in integrated_answer
assert "No current primary-service outage was verified" in integrated_answer

both_failed = answer_for([detail(primary_state="failed")])
both_failed_text = "\n".join(both_failed["lines"])
assert "Current outage indicated: yes" in both_failed_text
assert "Severity: HIGH" in both_failed_text
assert "severity remains high" in both_failed_text
assert service_diagnostics.critical_finding(
    service_diagnostics.assess_detail(detail(primary_state="failed"))
)["level"] == "RED"

unknown = detail(primary_state="unknown", primary_available=False)
unavailable = answer_for([unknown])
unavailable_text = "\n".join(unavailable["lines"])
assert unavailable["trust_state"] == "PARTIALLY VERIFIED"
assert "Current primary-service state: evidence unavailable" in unavailable_text
assert "Confirmation is still required" in unavailable_text

ordinary_failure = detail(unit="ordinary-job.service")
ordinary_failure["primary_candidates"] = []
ordinary_failure["primary"] = None
no_helper_relationship = answer_for(
    [ordinary_failure],
    question="Which failed watchdog or helper services have an active primary service?",
)
no_helper_text = "\n".join(no_helper_relationship["lines"])
assert (
    "No failed helper/watchdog relationship with a related primary service was verified"
    in no_helper_text
)
assert "No missing required helper files were verified" not in no_helper_text
assert "No helper-to-primary outage repair is indicated" in no_helper_relationship["next_step"]
assert "incomplete" not in no_helper_relationship["next_step"].lower()

system_missing = detail(
    unit="image-helper.service",
    paths=[path("/usr/libexec/image-helper", exists=False)],
    status="203",
    journal="image-helper.service: Failed at step EXEC: No such file or directory status=203/EXEC",
    fragment="/usr/lib/systemd/system/image-helper.service",
)
system_missing["primary_candidates"] = []
system_missing["primary"] = None
system_answer = answer_for([system_missing], question="Are required ZimaOS helper files missing?")
system_text = "\n".join(system_answer["lines"])
assert "Missing ZimaOS-managed helper/executable" in system_text
assert "status=203/EXEC was verified" in system_text
assert "No such file or directory" in system_text
assert "possible ZimaOS packaging regression" in system_text
assert "not confirmed" in system_text
assert "package provenance" in system_answer["next_step"]

data_missing = detail(
    unit="local-job.service",
    paths=[path("/DATA/AppData/jobs/run.sh", exists=False)],
)
data_missing["primary_candidates"] = []
data_missing["primary"] = None
data_text = "\n".join(answer_for([data_missing])["lines"])
assert "Missing user/local script or required file under /DATA" in data_text
assert "broken or stale local service configuration" in data_text

not_executable = detail(
    unit="local-mode.service",
    paths=[path("/DATA/AppData/jobs/run.sh", exists=True, executable=False)],
)
not_executable["primary_candidates"] = []
not_executable["primary"] = None
mode_text = "\n".join(answer_for([not_executable])["lines"])
assert "exists without executable permission" in mode_text

no_missing = answer_for([detail(primary_state="active")], question="Are helper files missing?")
assert (
    "No missing required helper files were verified from the current failed-unit evidence."
    in "\n".join(no_missing["lines"])
)
assert "No missing-helper repair is indicated" in no_missing["next_step"]
assert "incomplete" not in no_missing["next_step"].lower()

evidence_unavailable = failed_units.answer({
    "same_report_evidence": {
        "failed_units": "ERROR: host systemd evidence unavailable",
        "failed_unit_details": [],
        "failed_unit_details_collected": False,
    }
}, lambda value: value, "Are any helper files missing?")
assert evidence_unavailable["trust_state"] == "NOT VERIFIED"
assert "verification evidence is unavailable" in "\n".join(evidence_unavailable["lines"])
assert "incomplete" in evidence_unavailable["next_step"].lower()

route_questions = [
    "Are any required ZimaOS helper files missing?",
    "Which executables referenced by systemd cannot be found?",
    "Show me broken ExecStart paths.",
    "Did any unit fail with 203/EXEC?",
    "Which watchdog failed while its primary service stayed active?",
    "Are related primary services degraded?",
]
for question in route_questions:
    assert router.classify(question)["_intent"] == "failed_units", question
    assert intent_policy.classify(question)["handler"] == "failed_units", question

assert intent_policy.classify(route_questions[0])["memory_key"] == (
    intent_policy.classify(route_questions[1])["memory_key"]
)
assert intent_policy.classify(route_questions[0])["memory_key"] == "services:diagnose:execution"

assert service_diagnostics.related_service_name("alpha-monitor.service") == "alpha.service"
assert service_diagnostics.related_service_name(
    "unusual-helper-unit.service",
    {"PartOf": "primary-engine.service"},
) == "primary-engine.service"


def fake_host(command, timeout=10):
    if "systemctl show collector-watchdog.service" in command:
        return "\n".join((
            "Id=collector-watchdog.service",
            "LoadState=loaded",
            "ActiveState=failed",
            "SubState=failed",
            "Result=exit-code",
            "ExecMainStatus=203",
            "FragmentPath=/usr/lib/systemd/system/collector-watchdog.service",
            "ExecStartPre={ path=/usr/bin/preflight ; argv[]=/usr/bin/preflight ; ignore_errors=no ; }",
            "ExecStart={ path=/usr/libexec/collector-watchdog ; argv[]=/usr/libexec/collector-watchdog /DATA/AppData/collector/run.sh ; ignore_errors=no ; }",
            "ExecStartPost={ path=/usr/bin/postflight ; argv[]=/usr/bin/postflight ; ignore_errors=no ; }",
            "PartOf=collector.service",
        ))
    if "systemctl show collector.service" in command:
        return "\n".join((
            "Id=collector.service",
            "LoadState=loaded",
            "ActiveState=active",
            "SubState=running",
            "Result=success",
        ))
    if "journalctl -u collector-watchdog.service" in command:
        return "collector-watchdog.service: Failed at step EXEC: No such file or directory status=203/EXEC"
    if "p=/usr/libexec/collector-watchdog" in command:
        return "exists=no"
    if "p=/DATA/AppData/collector/run.sh" in command:
        return "exists=yes\nexecutable=no\nreadable=yes\nmode=-rw-r--r-- (644) owner=root:root type=regular file"
    return "exists=yes\nexecutable=yes\nreadable=yes\nmode=-rwxr-xr-x (755) owner=root:root type=regular file"


collected = service_diagnostics.collect_failed_unit_details(
    "collector-watchdog.service loaded failed failed collector",
    fake_host,
)
assert len(collected) == 1
collected_detail = collected[0]
assert "status" in collected_detail
sources = {item["source"] for item in collected_detail["paths"]}
assert {"FragmentPath", "ExecStartPre", "ExecStart", "ExecStartPost"} <= sources
collected_assessment = service_diagnostics.assess_detail(collected_detail)
assert collected_assessment["primary_state"] == "active"
assert collected_assessment["current_outage"] == "no"
assert collected_assessment["status_203"]
assert collected_assessment["journal_missing_path"]
assert any(
    item["path"] == "/usr/libexec/collector-watchdog"
    for item in collected_assessment["missing_system"]
)

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / "timeline.sqlite")
    failed_line = "alpha-watchdog.service loaded failed failed test helper"

    for boot_id, created_at in (
        ("boot-a", "2026-07-20 10:00:00"),
        ("boot-b", "2026-07-21 10:00:00"),
    ):
        health_memory.record_health_scan({
            "boot_id": boot_id,
            "failed_units": failed_line,
            "failed_unit_details": [detail(primary_state="active")],
            "failed_unit_details_collected": True,
        }, "v1.6.0-beta", db, created_at)

    correlations = health_memory.helper_service_correlations(db, limit=20)
    alpha = next(item for item in correlations if item["helper"] == "alpha-watchdog.service")
    assert alpha["classification"] == "known_historical_helper_issue"
    assert "remains active" in alpha["message"]

    health_memory.record_health_scan({
        "boot_id": "boot-c",
        "failed_units": "",
        "failed_unit_details": [],
        "failed_unit_details_collected": True,
        "active_services": (
            "alpha-watchdog.service loaded active running helper recovered\n"
            "alpha.service loaded active running primary"
        ),
    }, "v1.6.0-beta", db, "2026-07-22 10:00:00")

    correlations = health_memory.helper_service_correlations(db, limit=20)
    alpha = next(item for item in correlations if item["helper"] == "alpha-watchdog.service")
    assert alpha["classification"] == "recovered_helper"

    with sqlite3.connect(db) as con:
        persistent = con.execute("""
            SELECT COUNT(*) FROM health_events
            WHERE category = 'service' AND entity_key = 'alpha-watchdog.service'
              AND metric = 'failed' AND classification = 'persistent'
        """).fetchone()[0]
        recovered = con.execute("""
            SELECT COUNT(*) FROM health_events
            WHERE category = 'service' AND entity_key = 'alpha-watchdog.service'
              AND metric = 'failed' AND classification = 'recovered'
        """).fetchone()[0]
    assert persistent == 1
    assert recovered == 1

    missing_local = data_missing
    for boot_id, created_at in (
        ("boot-d", "2026-07-23 10:00:00"),
        ("boot-e", "2026-07-24 10:00:00"),
    ):
        health_memory.record_health_scan({
            "boot_id": boot_id,
            "failed_units": missing_local["failed_line"],
            "failed_unit_details": [missing_local],
            "failed_unit_details_collected": True,
        }, "v1.6.0-beta", db, created_at)

    health_memory.record_health_scan({
        "boot_id": "boot-f",
        "failed_units": "",
        "failed_unit_details": [],
        "failed_unit_details_collected": True,
    }, "v1.6.0-beta", db, "2026-07-25 10:00:00")

    with sqlite3.connect(db) as con:
        missing_classifications = [
            row[0] for row in con.execute("""
                SELECT classification FROM health_events
                WHERE category = 'service_exec'
                  AND metric = 'missing_required_file'
            """).fetchall()
        ]
    assert "persistent" in missing_classifications
    assert "recovered" in missing_classifications
    persistent_missing = {
        "classification": "persistent",
        "category": "service_exec",
        "metric": "missing_required_file",
    }
    assert trend_alerts._actionable(persistent_missing)

    health_memory.record_health_scan({
        "boot_id": "boot-g",
        "host_os": 'PRETTY_NAME="ZimaOS 1.6.2"\nVERSION_ID="1.6.2"',
        "failed_units": "",
        "failed_unit_details": [],
        "failed_unit_details_collected": True,
    }, "v1.6.0-beta", db, "2026-07-26 10:00:00")
    health_memory.record_health_scan({
        "boot_id": "boot-h",
        "host_os": 'PRETTY_NAME="ZimaOS 1.7.0"\nVERSION_ID="1.7.0"',
        "failed_units": missing_local["failed_line"],
        "failed_unit_details": [missing_local],
        "failed_unit_details_collected": True,
    }, "v1.6.0-beta", db, "2026-07-27 10:00:00")
    update_history = health_memory.system_update_history(db, limit=10)
    transition = next(
        item for item in update_history["transitions"]
        if any(change["current"] == "1.7.0" for change in item["changes"])
    )
    assert transition["classification"] == "post_update_attention"
    assert any(item["category"] == "service_exec" for item in transition["issues"])
    assert "does not prove" in transition["causality_note"]

print("RESULT: PASS (failed-helper, primary correlation, executable verification, routing, timeline)")
