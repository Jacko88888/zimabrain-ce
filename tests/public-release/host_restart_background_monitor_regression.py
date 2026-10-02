#!/usr/bin/env python3
import os
import sys
import tempfile


REPO_APP_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "app")
)
APP_ROOT = "/app" if os.path.isdir("/app/brain") else REPO_APP_ROOT
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from brain import background_monitor
from brain import health_memory
from brain import intent_policy
from brain import router
from brain.layers import host_restart


def require(condition, message):
    if not condition:
        raise AssertionError(message)


host_questions = (
    "Why did my NAS restart?",
    "What caused the host to reboot?",
    "Why did my NAS become unresponsive?",
    "Why did CPU and RAM reach 100%?",
    "What was running before the reboot?",
)

for question in host_questions:
    policy = intent_policy.classify(question)
    route = router.classify(question)
    require(
        policy["handler"] == "host_restart",
        f"host incident policy route failed for: {question}",
    )
    require(
        route["_intent"] == "host_restart",
        f"host incident router route failed for: {question}",
    )

for question in (
    "Why did my Docker container restart?",
    "Docker keeps restarting",
    "Why did this service restart?",
):
    require(
        intent_policy.classify(question)["handler"] != "host_restart",
        f"container question incorrectly routed to host restart: {question}",
    )
    require(
        router.classify(question)["_intent"] != "host_restart",
        f"container router incorrectly routed to host restart: {question}",
    )


boot_list = """
-1 11111111111111111111111111111111 Wed 2026-07-29 10:00:00 AEST—Wed 2026-07-29 11:00:00 AEST
 0 22222222222222222222222222222222 Wed 2026-07-29 11:00:10 AEST—Wed 2026-07-29 11:05:00 AEST
"""

clean = background_monitor.assess_previous_boot_journal(
    "22222222222222222222222222222222",
    boot_list,
    "kernel: normal",
    "systemd[1]: Reached target System Reboot\nsystemd-shutdown: Syncing filesystems",
)
require(clean["clean_shutdown"], "clean shutdown marker was not detected")
require(not clean["abrupt_shutdown_possible"], "clean shutdown was marked abrupt")

panic = background_monitor.assess_previous_boot_journal(
    "22222222222222222222222222222222",
    boot_list,
    "kernel: Kernel panic - not syncing: fatal exception",
    "previous boot journal",
)
require(panic["kernel_panic"], "kernel panic marker was not detected")

update = background_monitor.assess_previous_boot_journal(
    "22222222222222222222222222222222",
    boot_list,
    "kernel: normal",
    "zimaos-updater requested reboot after update activation",
)
require(update["update_reboot"], "explicit update reboot marker was not detected")
require(update["update_activity"], "update activity marker was not detected")

unknown = background_monitor.assess_previous_boot_journal(
    "22222222222222222222222222222222",
    boot_list,
    "kernel: ordinary final line",
    "service: ordinary final line",
)
require(unknown["journal_available"], "available previous journal was rejected")
require(unknown["abrupt_shutdown_possible"], "missing clean shutdown did not stay possible")
require(not unknown["kernel_panic"], "kernel panic was invented")
require(not unknown["update_reboot"], "update reboot was invented")
require(not unknown["manual_reboot"], "manual reboot was invented")


saved_functions = {
    "boot": background_monitor._boot_id,
    "uptime": background_monitor._uptime_seconds,
    "cpu": background_monitor._cpu_snapshot,
    "memory": background_monitor._memory_snapshot,
    "disk": background_monitor._disk_snapshot,
    "process": background_monitor._process_snapshot,
    "mount": background_monitor._mount_snapshot,
    "container": background_monitor._container_snapshot,
    "events": background_monitor._kernel_events,
    "time": background_monitor.time.time,
}
try:
    clocks = iter((1000.0, 1060.0))
    cpus = iter((
        {"total": 1000, "idle": 800},
        {"total": 1100, "idle": 820},
    ))
    disks = iter((
        {"read_bytes": 1000, "write_bytes": 2000},
        {"read_bytes": 7000, "write_bytes": 14000},
    ))
    processes = iter((
        {(42, 1): {"pid": 42, "command": "worker", "ticks": 10, "rss_kb": 1024}},
        {(42, 1): {"pid": 42, "command": "worker", "ticks": 50, "rss_kb": 2048}},
    ))
    mounts = iter((
        [{"target": "/DATA", "source": "/dev/sda8", "fstype": "ext4", "read_only": False}],
        [{"target": "/DATA", "source": "/dev/sda8", "fstype": "ext4", "read_only": True}],
    ))
    containers = iter((
        [{"name": "app", "state": "running", "image": "app:1"}],
        [{"name": "app", "state": "exited", "image": "app:1"}],
    ))

    background_monitor._boot_id = lambda: "collector-boot"
    background_monitor._uptime_seconds = lambda: 500.0
    background_monitor._cpu_snapshot = lambda: next(cpus)
    background_monitor._memory_snapshot = lambda: {
        "total_kb": 8192,
        "memory_percent": 92.0,
        "swap_percent": 20.0,
    }
    background_monitor._disk_snapshot = lambda: next(disks)
    background_monitor._process_snapshot = lambda: next(processes)
    background_monitor._mount_snapshot = lambda: next(mounts)
    background_monitor._container_snapshot = lambda: next(containers)
    background_monitor._kernel_events = lambda: []
    background_monitor.time.time = lambda: next(clocks)

    collector = background_monitor.BackgroundMonitor(interval=60)
    collector.collect()
    collected = collector.collect()
    require(collected["cpu_percent"] == 80.0, "host CPU delta calculation failed")
    require(collected["disk_read_bps"] == 100.0, "disk read-rate calculation failed")
    require(collected["disk_write_bps"] == 200.0, "disk write-rate calculation failed")
    require(
        collected["top_cpu"][0]["host_percent"] == 40.0,
        "per-process CPU delta calculation failed",
    )
    require(
        any(event["kind"] == "filesystem_mount_change" for event in collected["events"]),
        "mount transition event was not generated",
    )
    require(
        any(event["kind"] == "container_state_change" for event in collected["events"]),
        "container transition event was not generated",
    )
finally:
    background_monitor._boot_id = saved_functions["boot"]
    background_monitor._uptime_seconds = saved_functions["uptime"]
    background_monitor._cpu_snapshot = saved_functions["cpu"]
    background_monitor._memory_snapshot = saved_functions["memory"]
    background_monitor._disk_snapshot = saved_functions["disk"]
    background_monitor._process_snapshot = saved_functions["process"]
    background_monitor._mount_snapshot = saved_functions["mount"]
    background_monitor._container_snapshot = saved_functions["container"]
    background_monitor._kernel_events = saved_functions["events"]
    background_monitor.time.time = saved_functions["time"]


def sample(boot_id, epoch, cpu, memory, read_bps, write_bps, *, events=None):
    return {
        "boot_id": boot_id,
        "created_epoch": epoch,
        "created_at": f"2026-07-29 10:{int(epoch) % 60:02d}:00",
        "uptime_seconds": epoch,
        "cpu_percent": cpu,
        "memory_percent": memory,
        "swap_percent": 12.5,
        "disk_read_bps": read_bps,
        "disk_write_bps": write_bps,
        "running_containers": 2,
        "total_containers": 3,
        "top_cpu": [
            {"pid": 4242, "command": "example-worker", "host_percent": 74.0}
        ],
        "top_memory": [
            {"pid": 4343, "command": "example-memory", "rss_mb": 4096.0, "memory_percent": 25.0}
        ],
        "containers": [
            {"name": "running-app", "state": "running", "image": "example:1"},
            {"name": "stopped-job", "state": "exited", "image": "job:1"},
            {"name": "zimabrain-ce", "state": "running", "image": "zimabrain:1"},
        ],
        "mounts": [
            {"target": "/DATA", "source": "/dev/sda8", "fstype": "ext4", "read_only": False}
        ],
        "collector_status": "ok",
        "events": events or [],
    }


with tempfile.TemporaryDirectory() as tmp:
    db_path = os.path.join(tmp, "trends.sqlite")
    first = health_memory.record_monitor_sample(
        sample("boot-a", 1000, 35.0, 45.0, 1024, 2048),
        db_path=db_path,
    )
    require(first["ok"], "first monitor sample failed")

    second = health_memory.record_monitor_sample(
        sample(
            "boot-a",
            1060,
            99.0,
            97.0,
            20 * 1024 * 1024,
            30 * 1024 * 1024,
            events=[{
                "kind": "oom",
                "severity": "critical",
                "message": "Kernel OOM activity was recorded.",
                "evidence": "kernel: Killed process 4242 (example-worker)",
                "fingerprint": "test-oom-boot-a",
            }],
        ),
        db_path=db_path,
    )
    require(second["ok"], "second monitor sample failed")

    health_memory.record_monitor_boot_evidence({
        "boot_id": "boot-b",
        "observed_at": "2026-07-29 11:01:00",
        "previous_boot_id": "boot-a",
        "journal_available": True,
        "clean_shutdown": False,
        "kernel_panic": False,
        "manual_reboot": False,
        "update_reboot": False,
        "update_activity": False,
        "oom_before_reboot": True,
        "abrupt_shutdown_possible": True,
        "details": {"oom": ["kernel: Killed process 4242 (example-worker)"]},
    }, db_path=db_path)
    current = health_memory.record_monitor_sample(
        sample("boot-b", 1120, 5.0, 30.0, 100, 200),
        db_path=db_path,
    )
    require(current["boot_changed"], "host boot transition was not recorded")

    context = health_memory.monitor_restart_context(
        db_path=db_path, current_boot_id="boot-b"
    )
    require(context["previous_boot_id"] == "boot-a", "previous boot ID mismatch")
    require(context["previous"]["sample_count"] == 2, "previous sample count mismatch")
    require(
        context["previous"]["peak_cpu"]["cpu_percent"] == 99.0,
        "peak CPU was not retained",
    )
    require(
        context["previous"]["peak_memory"]["memory_percent"] == 97.0,
        "peak memory was not retained",
    )
    require(
        any(event["kind"] == "oom" for event in context["previous_events"]),
        "pre-reboot OOM event was not retained",
    )

    answer = host_restart.answer(
        "Why did my NAS restart?",
        {
            "same_report_evidence": {"boot_id": "boot-b"},
            "health_memory_db_path": db_path,
        },
    )
    require("@@VERIFY:VERIFIED@@" in answer, "verified host reboot answer missing")
    require("boot-a" in answer and "boot-b" in answer, "boot transition missing")
    require("Peak host CPU: 99.0%" in answer, "pre-reboot CPU peak missing")
    require("Peak memory use: 97.0%" in answer, "pre-reboot memory peak missing")
    require("example-worker" in answer, "top CPU process missing")
    require("OOM event was captured before the reboot" in answer, "OOM correlation missing")
    require("does not by itself prove" in answer, "OOM causality limitation missing")
    require("Abrupt power loss or a hard reset remains possible" in answer, "power-loss limitation missing")

print("RESULT: PASS (host reboot routing, journal evidence, rolling pre-reboot history)")
