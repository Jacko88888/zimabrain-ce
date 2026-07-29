#!/usr/bin/env python3
import sys
from pathlib import Path


sys.path.insert(0, "/app")
if "/app" not in Path(__file__).resolve().as_posix():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))

from brain import dashboard
from brain.layers import comprehensive_health

try:
    import flask_app
except ModuleNotFoundError as error:
    if error.name != "flask":
        raise
    flask_app = None


failures = []


def require(condition, message):
    if not condition:
        failures.append(message)


unusual_mount = (
    'SOURCE="/dev/sdb" '
    'TARGET="/media/HDD-Storage-/dev/sdb" '
    'FSTYPE="btrfs" OPTIONS="rw,relatime"'
)
normal_mount = (
    'SOURCE="/dev/sdb" '
    'TARGET="/media/HDD-Storage-sdb" '
    'FSTYPE="btrfs" OPTIONS="rw,relatime"'
)


def mount_findings(evaluator, mount_line):
    return evaluator({
        "failed_units": "",
        "lsblk": "",
        "mounts": mount_line,
        "docker_ps": "",
        "docker_access": "",
        "nvidia": "",
        "media_paths": (
            "/DATA/.media present\n"
            "/var/lib/casaos_data/.media present"
        ),
    })


def cpu_findings(evaluator, host_cpu_usage):
    return evaluator({
        "failed_units": "",
        "lsblk": "",
        "mounts": "",
        "docker_ps": "",
        "docker_access": "",
        "nvidia": "",
        "media_paths": (
            "/DATA/.media present\n"
            "/var/lib/casaos_data/.media present"
        ),
        "cpu_usage": f"CPU_USAGE_PERCENT={host_cpu_usage}",
        "process_top": (
            "PID PPID COMMAND STAT %CPU %MEM COMMAND\n"
            "123 1 python3 S 96.1 0.2 python3 healthcheck.py"
        ),
    })


evaluators = [("dashboard", dashboard.evaluate_critical_same_report)]
if flask_app is not None:
    evaluators.append(("flask", flask_app.evaluate_critical_same_report))

for name, evaluator in evaluators:
    unusual = mount_findings(evaluator, unusual_mount)
    matching = [
        finding for finding in unusual
        if finding.get("title") == "Unusual media mount target observed"
    ]
    require(
        len(matching) == 1,
        f"{name}: unusual target observation missing or duplicated",
    )
    if matching:
        require(
            matching[0].get("level") == "INFO",
            f"{name}: unusual target was promoted above INFO",
        )
        require(
            matching[0].get("detail") == unusual_mount,
            f"{name}: exact findmnt evidence was not preserved",
        )

    require(
        not any(
            finding.get("title")
            == "Files/AppData media mount naming issue detected"
            for finding in unusual
        ),
        f"{name}: legacy actionable mount title remains",
    )

    normal = mount_findings(evaluator, normal_mount)
    require(
        not any(
            finding.get("title") == "Unusual media mount target observed"
            for finding in normal
        ),
        f"{name}: normal media target was misclassified",
    )

    low_host_cpu = cpu_findings(evaluator, 5.2)
    low_cpu_matches = [
        finding for finding in low_host_cpu
        if finding.get("title")
        == "High per-process CPU value needs host-wide confirmation"
    ]
    require(
        len(low_cpu_matches) == 1,
        f"{name}: uncorroborated per-process CPU context missing",
    )
    if low_cpu_matches:
        require(
            low_cpu_matches[0].get("level") == "INFO",
            f"{name}: uncorroborated per-process CPU was actionable",
        )

    high_host_cpu = cpu_findings(evaluator, 92.5)
    high_cpu_matches = [
        finding for finding in high_host_cpu
        if finding.get("title")
        == "High CPU process corroborated by host-wide pressure"
    ]
    require(
        len(high_cpu_matches) == 1,
        f"{name}: corroborated host CPU pressure was not detected",
    )
    if high_cpu_matches:
        require(
            high_cpu_matches[0].get("level") == "YELLOW",
            f"{name}: corroborated host CPU pressure was not actionable",
        )


original_timeline = comprehensive_health._timeline
comprehensive_health._timeline = lambda: (
    {"id": 2},
    [{
        "classification": "persistent",
        "category": "container",
        "entity_name": "immich-machine-learning",
        "metric": "health",
        "current_text": "unhealthy",
        "message": (
            "immich-machine-learning health remains in an issue state: "
            "unhealthy."
        ),
    }],
    [],
    [],
    {},
    {
        "current": {},
        "transitions": [
            {"message": ""},
            {"message": "release changed from test-a to test-b."},
        ],
    },
)

try:
    report = comprehensive_health.answer({
        "same_report_evidence": {
            "docker_states": (
                "/immich-machine-learning|image|running|unhealthy|0||"
            ),
        },
        "critical_findings": [],
        "normalized": {"info_only": []},
    })
finally:
    comprehensive_health._timeline = original_timeline

text = "\n".join(report["lines"])
require(
    text.count("immich-machine-learning") == 1,
    "current unhealthy container was duplicated by timeline evidence",
)
require(
    "- Update transition: release changed from test-a to test-b." in text,
    "non-empty update transition was not rendered",
)
require(
    "- Update transition: \n" not in text,
    "blank update transition was rendered",
)


if failures:
    print(f"RESULT: FAIL ({len(failures)} failure(s))")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)

print(
    "RESULT: PASS "
    "(actionable deduplication, mount context, CPU corroboration, "
    "transition formatting)"
)
