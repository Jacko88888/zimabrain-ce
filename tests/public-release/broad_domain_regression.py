#!/usr/bin/env python3
import sqlite3
import sys

sys.path.insert(0, "/app")

import flask_app
from brain import router

DB = "/data/zimabrain_trends.sqlite"

flask_app.record_trend_snapshot = lambda bundle: {
    "ok": False,
    "error": "disabled for read-only broad regression",
}

groups = [
    {
        "name": "whole-system health",
        "questions": [
            "Can you assess the overall condition of this machine?",
            "How healthy is my whole ZimaCube right now?",
            "Assess the entire host and tell me what needs attention.",
            "Give me a full assessment of the whole system.",
        ],
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Comprehensive System Health Layer",
            "Overall severity:",
            "Current actionable findings",
        ],
        "forbidden": [
            "Custom Question Evidence Layer",
            "Hardware Compatibility Layer",
            "Inspect assess",
        ],
    },
    {
        "name": "memory and swap",
        "questions": [
            "Do I have enough available memory, or is swap under pressure?",
            "Is available RAM getting too low?",
            "Am I running out of memory?",
            "How much memory is available and how much swap is used?",
        ],
        "required": [
            "Active layer: Host Hardware Metrics Layer",
            "Memory pressure assessment:",
            "Memory available:",
            "Swap:",
        ],
        "forbidden": ["Custom Question Evidence Layer"],
    },
    {
        "name": "dns and routing",
        "questions": [
            "Is DNS working, and which gateway is currently active?",
            "Can this host resolve DNS and reach its default route?",
            "Do I have a current DNS or gateway problem?",
            "Are multiple interfaces creating an active routing conflict?",
        ],
        "required": [
            "Active layer: Network Connectivity Diagnostics Layer",
            "DNS/routing assessment:",
            "Active default routes detected:",
        ],
        "forbidden": [
            "App Runtime Diagnostics Layer",
            "Hardware Compatibility Layer",
        ],
    },
    {
        "name": "container states",
        "questions": [
            "Show containers that are exited, restarting, or unhealthy.",
            "Which containers are stopped or unhealthy?",
            "Summarize running, exited, restarting and unhealthy containers.",
        ],
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Containers Layer",
            "Current Docker state summary:",
            "Restarting containers:",
            "Unhealthy running containers:",
        ],
        "forbidden": ["Docker Daemon Diagnostics Layer"],
    },
    {
        "name": "read-only storage",
        "questions": [
            "Are any storage filesystems unexpectedly read-only?",
            "Do any writable data mounts currently show read-only?",
            "Check whether DATA or media storage has become read-only.",
        ],
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Read-Only Storage Diagnostics Layer",
            "Unexpectedly read-only writable-storage mounts:",
        ],
        "forbidden": ["root cause is not verified"],
    },
    {
        "name": "disk and nvme trends",
        "questions": [
            "Have any disk or NVMe error counters increased?",
            "Are any SMART values getting worse?",
            "Did CRC, media-error, or unsafe-shutdown counts rise?",
        ],
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Health Timeline and Local Memory Layer",
            "SMART/NVMe trend assessment:",
        ],
        "forbidden": ["Hardware Compatibility Layer"],
    },
    {
        "name": "update comparison",
        "questions": [
            "What changed after my latest ZimaOS update?",
            "Did system health change after the OS update?",
            "Compare current problems with the recorded ZimaOS update baseline.",
        ],
        "required": [
            "Active layer: Health Timeline and Local Memory Layer",
            "ZimaOS update / regression timing",
        ],
        "forbidden": ["ZimaOS Update / Rollback Safety Layer"],
    },
    {
        "name": "failed services",
        "questions": [
            "Which services are failed or degraded?",
            "Show current failed systemd units.",
            "Are any host services currently failed?",
        ],
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Failed Units Layer",
            "zima-cron-fix.service",
        ],
        "forbidden": ["Custom Question Evidence Layer"],
    },
    {
        "name": "security posture",
        "questions": [
            "Is the system adequately protected?",
            "Assess firewall, audit and container exposure security.",
        ],
        "required": [
            "Active layer: Network Exposure / Firewall Layer",
            "ZFW firewall status",
            "DOCKER-USER firewall chain",
        ],
        "forbidden": ["SnapRAID / mergerfs Layer"],
    },
    {
        "name": "tailscale status",
        "questions": [
            "Is Tailscale functioning correctly?",
            "Is the Tailscale tunnel currently up?",
        ],
        "required": [
            "Active layer: Network Connectivity Diagnostics Layer",
            "Tailscale assessment:",
        ],
        "forbidden": ["Network Exposure / Firewall Layer"],
    },
    {
        "name": "unknown components",
        "questions": [
            "Why is the fictional quantum-reactor service failing?",
            "Is the imaginary warp-drive controller healthy?",
        ],
        "required": [
            "@@VERIFY:NOT VERIFIED@@",
            "Active layer: Custom Question Evidence Layer",
        ],
        "forbidden": [
            "VERIFIED FROM SAME-REPORT EVIDENCE",
            "Inspect fictional",
            "Inspect imaginary",
        ],
    },
]


def db_state():
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as con:
        scans = con.execute(
            "SELECT COUNT(*),COALESCE(MAX(created_at),'') FROM health_scans"
        ).fetchone()
        snapshots = con.execute(
            "SELECT COUNT(*),COALESCE(MAX(created_at),'') FROM trend_snapshots"
        ).fetchone()
    return scans, snapshots


before = db_state()
failures = []
number = 0

for group in groups:
    for question in group["questions"]:
        number += 1
        route = router.classify(question)
        answer = flask_app.answer_question(question)
        verification = next(
            (
                line.strip()
                for line in answer.splitlines()
                if line.startswith("@@VERIFY:")
            ),
            "MISSING",
        )
        active = next(
            (
                line.strip()
                for line in answer.splitlines()
                if "Active layer:" in line
            ),
            "MISSING",
        )

        missing = [text for text in group["required"] if text not in answer]
        forbidden = [
            text for text in group["forbidden"]
            if text.lower() in answer.lower()
        ]

        status = "PASS" if not missing and not forbidden else "FAIL"
        print(
            f"{number:02d} {status} group={group['name']} "
            f"route={route['_intent']} verification={verification} {active}"
        )
        print(f"   {question}")

        for text in missing:
            failures.append(
                f"{number}: missing {text!r} for {question!r}"
            )
        for text in forbidden:
            failures.append(
                f"{number}: forbidden {text!r} for {question!r}"
            )

after = db_state()

if after != before:
    failures.append(f"database changed: before={before!r} after={after!r}")

print("=" * 90)
print(f"database_before={before!r}")
print(f"database_after={after!r}")

if failures:
    print(f"RESULT: FAIL ({len(failures)} failure(s))")
    for failure in failures:
        print(f"- {failure}")
    raise SystemExit(1)

print(f"RESULT: PASS ({number} questions)")
