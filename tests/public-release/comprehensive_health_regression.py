#!/usr/bin/env python3
import sqlite3
import sys

sys.path.insert(0, "/app")

import flask_app
from brain import router


DB_URI = "file:/data/zimabrain_trends.sqlite?mode=ro"


def database_state():
    queries = (
        "SELECT COUNT(*), COALESCE(MAX(created_at), '') FROM health_scans",
        "SELECT COUNT(*), COALESCE(MAX(scan_id), 0) FROM health_observations",
        "SELECT COUNT(*), COALESCE(MAX(scan_id), 0) FROM health_events",
        "SELECT COUNT(*), COALESCE(MAX(created_at), '') FROM trend_snapshots",
    )
    with sqlite3.connect(DB_URI, uri=True) as connection:
        return tuple(connection.execute(query).fetchone() for query in queries)


flask_app.record_trend_snapshot = lambda bundle: {
    "ok": False,
    "error": "disabled for read-only golden regression",
}


cases = [
    {
        "question": "Give me a complete system-health assessment.",
        "intent": "comprehensive_health",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Comprehensive System Health Layer",
            "Overall severity:",
            "CPU",
            "Memory",
            "Swap",
            "Filesystems",
            "SMART",
            "NVMe",
            "Containers",
            "Failed units",
            "Network",
            "Firewall",
            "Configuration drift",
            "Current actionable findings",
            "Historical",
        ],
        "forbidden": ["Inspect give", "Custom Question Evidence Layer"],
    },
    {
        "question": "Is my system healthy?",
        "intent": "comprehensive_health",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Comprehensive System Health Layer",
            "Overall severity:",
            "Current actionable findings",
        ],
        "forbidden": ["Custom Question Evidence Layer"],
    },
    {
        "question": "Summarize the health of my Cube.",
        "intent": "comprehensive_health",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Comprehensive System Health Layer",
            "Overall severity:",
            "Current actionable findings",
        ],
        "forbidden": ["Dashboard Alerts Layer"],
    },
    {
        "question": "What should I check first?",
        "intent": "unknown",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Health Timeline Alert Layer",
            "Actionable timeline alerts",
            "mailcowdockerized-ofelia-mailcow-1",
        ],
        "forbidden": ["Inspect what", "Custom Question Evidence Layer"],
    },
    {
        "question": "What changed since my previous scan?",
        "intent": "report_comparison",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Health Timeline and Local Memory Layer",
            "Worsening conditions",
            "Historical and stable values",
        ],
        "forbidden": ["Custom Question Evidence Layer"],
    },
    {
        "question": "Why is mailcowdockerized-ofelia-mailcow-1 restarting?",
        "intent": "unknown",
        "required": [
            "@@VERIFY:PARTIALLY VERIFIED@@",
            "Active layer: Custom Question Evidence Layer",
            "mailcowdockerized-ofelia-mailcow-1",
            "restarting",
            "restart count",
        ],
        "forbidden": ["Inspect why", "NOT VERIFIED FROM CURRENT REPORT"],
    },
    {
        "question": "Why is the fictional flux-capacitor-daemon overheating?",
        "intent": "unknown",
        "required": [
            "@@VERIFY:NOT VERIFIED@@",
            "Active layer: Custom Question Evidence Layer",
            "No matching same-report evidence",
            "flux-capacitor-daemon",
        ],
        "forbidden": ["Inspect fictional", "Inspect why"],
    },
    {
        "question": "Is memory pressure high?",
        "intent": "host_hardware_metrics",
        "required": [
            "Active layer: Host Hardware Metrics Layer",
            "Memory pressure assessment:",
            "Memory available:",
            "Swap:",
        ],
        "forbidden": [
            "Custom Question Evidence Layer",
            "High CPU process observed during report",
        ],
    },
    {
        "question": "Are there DNS or routing problems?",
        "intent": "network_connectivity_diag",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Network Connectivity Diagnostics Layer",
            "DNS/routing assessment:",
            "ip_addr",
            "ip_route",
            "resolv",
            "Default routes detected:",
        ],
        "forbidden": ["Network evidence keys found: docker_ps"],
    },
    {
        "question": "Are multiple network interfaces causing routing conflicts?",
        "intent": "network_connectivity_diag",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Network Connectivity Diagnostics Layer",
            "Interfaces with IPv4 addresses:",
            "Default routes detected:",
            "Routing-conflict assessment:",
        ],
        "forbidden": ["Custom Question Evidence Layer"],
    },
    {
        "question": "Which containers are stopped or unhealthy?",
        "intent": "containers",
        "required": [
            "@@VERIFY:VERIFIED@@",
            "Active layer: Containers Layer",
            "Current Docker state summary:",
            "Restarting containers: 1",
            "mailcowdockerized-ofelia-mailcow-1",
            "Unhealthy running containers: 0",
            "Exited containers:",
        ],
        "forbidden": [
            "according to the visual dashboard count",
            "Dashboard-parsed exited containers:",
        ],
    },
]


before = database_state()
failures = []

if flask_app.DASHBOARD_BUNDLE_CACHE_TTL < 120:
    failures.append(
        "bundle cache TTL must be at least 120 seconds for responsive session questions"
    )

for number, case in enumerate(cases, 1):
    question = case["question"]
    route = router.classify(question)
    answer = flask_app.answer_question(question)

    print("=" * 90)
    print(f"{number}. {question}")
    print(f"route={route['_intent']} confidence={route['_confidence']}")
    print(
        "verification="
        + next(
            (
                line.strip()
                for line in answer.splitlines()
                if line.startswith("@@VERIFY:")
            ),
            "MISSING",
        )
    )

    if route["_intent"] != case["intent"]:
        failures.append(
            f"{number}: route expected {case['intent']!r}, got {route['_intent']!r}"
        )

    for text in case["required"]:
        if text not in answer:
            failures.append(f"{number}: required text missing: {text!r}")

    for text in case["forbidden"]:
        if text.lower() in answer.lower():
            failures.append(f"{number}: forbidden text present: {text!r}")


after = database_state()

if after != before:
    failures.append(f"database changed: before={before!r} after={after!r}")

print("=" * 90)
print(f"database_before={before!r}")
print(f"database_after={after!r}")

if failures:
    print(f"RESULT: FAIL ({len(failures)} failure(s))")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)

print("RESULT: PASS")
