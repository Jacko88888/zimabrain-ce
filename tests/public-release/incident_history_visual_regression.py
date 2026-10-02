#!/usr/bin/env python3
import ast
import html
import os
import sys
import tempfile
import time


REPO_APP_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "app")
)
APP_ROOT = "/app" if os.path.isdir("/app/brain") else REPO_APP_ROOT
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from brain import background_monitor
from brain import health_memory

try:
    import flask_app
except ModuleNotFoundError as error:
    if error.name not in {"flask", "werkzeug"}:
        raise
    flask_app = None


def visual_renderer():
    if flask_app is not None:
        return flask_app.incident_history_panel

    flask_source = os.path.join(REPO_APP_ROOT, "flask_app.py")
    source = open(flask_source, "r", encoding="utf-8").read()
    tree = ast.parse(source, filename=flask_source)
    names = {
        "_incident_rate", "_incident_value", "_incident_chart_svg",
        "incident_history_panel",
    }
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    require(len(functions) == len(names), "incident visual helper extraction failed")
    namespace = {
        "TREND_DB_PATH": health_memory.TREND_DB_PATH,
        "health_memory": health_memory,
        "background_monitor": background_monitor,
        "esc": lambda value: html.escape(str(value), quote=True),
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), flask_source, "exec"), namespace)
    return namespace["incident_history_panel"]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


with tempfile.TemporaryDirectory() as temp_dir:
    db_path = os.path.join(temp_dir, "incident-history.sqlite")
    now = time.time()

    for index, values in enumerate((
        (18.0, 42.0, 3.0, 1024.0, 2048.0),
        (92.0, 81.0, 12.0, 1048576.0, 524288.0),
        (36.0, 55.0, 8.0, 4096.0, 8192.0),
    )):
        cpu, memory, swap, disk_read, disk_write = values
        health_memory.record_monitor_sample({
            "created_at": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(now - (120 - index * 60))
            ),
            "created_epoch": now - (120 - index * 60),
            "boot_id": "visual-boot-a",
            "uptime_seconds": 1000 + index * 60,
            "cpu_percent": cpu,
            "memory_percent": memory,
            "swap_percent": swap,
            "disk_read_bps": disk_read,
            "disk_write_bps": disk_write,
            "running_containers": 8,
            "total_containers": 10,
            "top_cpu": [{
                "pid": 4242,
                "command": "example-worker",
                "host_percent": cpu,
            }],
            "top_memory": [{
                "pid": 4343,
                "command": "memory-worker",
                "rss_mb": 512.5,
                "memory_percent": 4.2,
            }],
            "containers": [
                {"name": "running-app", "state": "running"},
                {"name": "stopped-app", "state": "exited"},
            ],
            "mounts": [{"target": "/DATA", "source": "/dev/test", "read_only": False}],
            "collector_status": "ok",
            "events": [{
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                "created_epoch": now,
                "kind": "oom",
                "severity": "critical",
                "message": "Kernel OOM activity was recorded.",
                "evidence": "Killed process 4242 (example-worker)",
                "fingerprint": "visual-test-oom",
            }] if index == 1 else [],
        }, db_path=db_path)

    health_memory.record_monitor_boot_evidence({
        "boot_id": "visual-boot-a",
        "observed_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "previous_boot_id": "visual-boot-before",
        "journal_available": True,
        "clean_shutdown": False,
        "kernel_panic": False,
        "manual_reboot": False,
        "update_reboot": False,
        "update_activity": False,
        "oom_before_reboot": True,
        "abrupt_shutdown_possible": True,
        "details": {"oom": ["Killed process 4242 (example-worker)"]},
    }, db_path=db_path)

    history = health_memory.monitor_history(db_path, hours=24)
    require(len(history["samples"]) == 3, "visual history sample count mismatch")
    require(history["summary"]["peak_cpu_percent"] == 92.0, "peak CPU mismatch")
    require(history["summary"]["peak_memory_percent"] == 81.0, "peak memory mismatch")
    require(history["summary"]["event_count"] == 1, "event count mismatch")
    require(history["latest_details"]["container_states"]["running"] == 1, "container state missing")

    expected_visuals = (
        'id="incident-history"',
        "Incident History",
        "Peak CPU",
        "CPU, memory and swap",
        "Disk I/O",
        "example-worker",
        "memory-worker",
        "Kernel OOM activity was recorded.",
        "visual-boot-",
        "<svg",
    )
    panel = visual_renderer()(db_path=db_path, hours=24)
    for expected in expected_visuals:
        require(expected in panel, f"missing incident visual content: {expected}")
    require("92.0%" in panel, "rendered peak CPU value missing")

print("RESULT: PASS (incident-history API data, charts, processes, containers, boots, events)")
