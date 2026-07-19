#!/usr/bin/env python3
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/app")

from brain import question_memory
import flask_app


with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / "question-memory.sqlite")

    first = question_memory.record_and_compare(
        "performance:status:memory",
        "Is memory pressure high?",
        10,
        "VERIFIED",
        "Host Hardware Metrics Layer",
        "Memory pressure is normal; 7.5 GiB is available.",
        db,
        "2026-07-19 06:00:00",
    )
    assert first["state"] == "first_observation"
    assert first["lines"] == []

    same = question_memory.record_and_compare(
        "performance:status:memory",
        "Do I have enough available RAM?",
        10,
        "VERIFIED",
        "Host Hardware Metrics Layer",
        "Memory pressure is normal; 7.5 GiB is available.",
        db,
        "2026-07-19 06:01:00",
    )
    assert same["state"] == "same_snapshot"
    assert "repeats evidence snapshot #10" in "\n".join(same["lines"])

    changed = question_memory.record_and_compare(
        "performance:status:memory",
        "Am I running out of memory?",
        11,
        "PARTIALLY VERIFIED",
        "Host Hardware Metrics Layer",
        "Memory pressure is elevated; 900 MiB is available.",
        db,
        "2026-07-19 07:00:00",
    )
    assert changed["state"] == "changed"
    changed_text = "\n".join(changed["lines"])
    assert "Previous evidence snapshot: #10" in changed_text
    assert "current evidence snapshot: #11" in changed_text
    assert "VERIFIED → PARTIALLY VERIFIED" in changed_text
    assert "Previous conclusion:" in changed_text
    assert "Current conclusion:" in changed_text

    other = question_memory.record_and_compare(
        "network:status:dns-routing",
        "Is DNS working?",
        11,
        "VERIFIED",
        "Network Connectivity Diagnostics Layer",
        "DNS resolution and the active default route are working.",
        db,
    )
    assert other["state"] == "first_observation"

    question_memory.record_and_compare(
        "security:status:test",
        "password=super-secret-value",
        11,
        "NOT VERIFIED",
        "Custom Question Evidence Layer",
        "token=another-secret-value",
        db,
    )

    with sqlite3.connect(db) as con:
        stored = "\n".join(
            str(value)
            for row in con.execute(
                "SELECT question,direct_answer FROM question_memory_entries"
            )
            for value in row
        )

    assert "super-secret-value" not in stored
    assert "another-secret-value" not in stored
    assert "[REDACTED]" in stored
    assert question_memory.memory_count(db) == 4

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / "answer-integration.sqlite")
    flask_app.QUESTION_MEMORY_DB_PATH = db
    flask_app.QUESTION_MEMORY_ENABLED = True

    snapshot_20 = {
        "trend_snapshot": {
            "memory_scan": {"ok": True, "scan_id": 20}
        }
    }
    snapshot_21 = {
        "trend_snapshot": {
            "memory_scan": {"ok": True, "scan_id": 21}
        }
    }

    normal_answer = """### ZimaBrain Answer

#### Verification status
@@VERIFY:VERIFIED@@ ✅ VERIFIED
- Active layer: Host Hardware Metrics Layer

#### Direct answer / severity
- Memory pressure is normal.
- Memory available: 7500 MiB.

#### Next safest step
- Continue monitoring.
"""

    elevated_answer = """### ZimaBrain Answer

#### Verification status
@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED
- Active layer: Host Hardware Metrics Layer

#### Direct answer / severity
- Memory pressure is elevated.
- Memory available: 900 MiB.

#### Next safest step
- Inspect memory-consuming processes.
"""

    first = flask_app._apply_question_memory(
        "Is memory pressure high?",
        normal_answer,
        snapshot_20,
    )
    assert "Previous answer comparison" not in first

    repeated = flask_app._apply_question_memory(
        "Do I have enough available RAM?",
        normal_answer,
        snapshot_20,
    )
    assert "Previous answer comparison" in repeated
    assert "repeats evidence snapshot #20" in repeated
    assert "Direct conclusion: unchanged" in repeated

    changed = flask_app._apply_question_memory(
        "Am I running out of memory?",
        elevated_answer,
        snapshot_21,
    )
    assert "Previous evidence snapshot: #20" in changed
    assert "current evidence snapshot: #21" in changed
    assert "VERIFIED → PARTIALLY VERIFIED" in changed
    assert "Previous conclusion:" in changed
    assert "Current conclusion:" in changed

    for scan_id in range(100, 160):
        question_memory.record_and_compare(
            "performance:status:retention-test",
            "Is memory pressure high?",
            scan_id,
            "VERIFIED",
            "Host Hardware Metrics Layer",
            f"Memory sample {scan_id}",
            db,
        )

    with sqlite3.connect(db) as con:
        retained = con.execute(
            """
            SELECT COUNT(*)
            FROM question_memory_entries
            WHERE memory_key = ?
            """,
            ("performance:status:retention-test",),
        ).fetchone()[0]

    assert retained == 50

print(
    "RESULT: PASS "
    "(persistence, paraphrase recall, answer comparison, redaction, retention)"
)
