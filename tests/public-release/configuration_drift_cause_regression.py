#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, "/app")
if "/app" not in Path(__file__).resolve().as_posix():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))

from brain import health_memory
from brain.layers import comprehensive_health


def evidence(lan, bind):
    return {
        "port_reachability": (
            "HOST_LAN_IP=192.168.1.100\n"
            f"example|8080|localhost=open|lan={lan}|lan_ip=192.168.1.100"
        ),
        "docker_access": (
            f"/example||8080/tcp=>{bind}:8080,;"
        ),
    }


def exposure_drift(db_path):
    history = health_memory.configuration_drift_history(db_path, limit=10)
    matches = [
        item for item in history["drifts"]
        if item["entity_key"] == "example:8080"
        and item["metric"] == "reachability"
    ]
    assert len(matches) == 1, matches
    return matches[0]


with tempfile.TemporaryDirectory() as tmp:
    db_path = str(Path(tmp) / "verified-cause.sqlite")
    health_memory.record_health_scan(
        evidence("closed", "127.0.0.1"),
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-28 10:00:00",
    )
    health_memory.record_health_scan(
        evidence("open", "0.0.0.0"),
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-28 11:00:00",
    )
    drift = exposure_drift(db_path)
    assert drift["classification"] == "new_lan_exposure"
    assert drift["severity"] == "attention"
    assert drift["cause_verification"] == "VERIFIED"
    assert "Docker host bind changed" in drift["cause"]
    assert "`127.0.0.1` to `0.0.0.0`" in drift["message"]

    history = health_memory.configuration_drift_history(db_path, limit=10)
    original_timeline = comprehensive_health._timeline
    comprehensive_health._timeline = lambda: (
        {"id": 2},
        [],
        [],
        [],
        history,
        {},
    )
    try:
        report = comprehensive_health.answer({
            "same_report_evidence": {},
            "critical_findings": [],
        })
    finally:
        comprehensive_health._timeline = original_timeline
    report_text = "\n".join(report["lines"])
    assert "Drift requiring attention:" in report_text
    assert "Cause verified: the Docker host bind changed" in report_text


with tempfile.TemporaryDirectory() as tmp:
    db_path = str(Path(tmp) / "unknown-cause.sqlite")
    health_memory.record_health_scan(
        evidence("closed", "0.0.0.0"),
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-28 10:00:00",
    )
    health_memory.record_health_scan(
        evidence("open", "0.0.0.0"),
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-28 11:00:00",
    )
    drift = exposure_drift(db_path)
    assert drift["classification"] == "new_lan_exposure"
    assert drift["cause_verification"] == "NOT VERIFIED"
    assert "host bind remained `0.0.0.0`" in drift["cause"]
    assert "does not prove" in drift["message"]


with tempfile.TemporaryDirectory() as tmp:
    db_path = str(Path(tmp) / "restricted-cause.sqlite")
    health_memory.record_health_scan(
        evidence("open", "0.0.0.0"),
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-28 10:00:00",
    )
    health_memory.record_health_scan(
        evidence("closed", "127.0.0.1"),
        "v1.6.0-beta",
        db_path=db_path,
        created_at="2026-07-28 11:00:00",
    )
    drift = exposure_drift(db_path)
    assert drift["classification"] == "lan_exposure_restricted"
    assert drift["severity"] == "recovery"
    assert drift["cause_verification"] == "VERIFIED"
    assert "restricting it to localhost" in drift["message"]


print("RESULT: PASS (configuration drift causal explanation)")
