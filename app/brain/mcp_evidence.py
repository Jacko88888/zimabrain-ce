"""Question-scoped, verifier-first MCP evidence adapter for ZimaBrain CE."""

from __future__ import annotations

import copy
import os
import re
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from brain.mcp_client import ALLOWED_TOOLS, McpClientError, ZimaBrainMcpClient


_CACHE_LOCK = threading.Lock()
_BASE_CACHE = None
_BASE_CACHE_AT = 0.0
_BASE_CACHE_TTL = 15.0
STORAGE_TOOLS = frozenset(
    {
        "storage_inventory",
        "filesystem_usage",
        "smart_health",
        "nvme_health",
        "btrfs_health",
        "raid_health",
    }
)


def _items(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        return value["items"]
    return []


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def _format_evidence_time(value):
    """Render an ISO timestamp in the operator's configured local timezone."""
    raw = str(value or "").strip()
    if not raw:
        return "unknown"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        local_zone = ZoneInfo(os.environ.get("TZ", "Australia/Sydney"))
        return parsed.astimezone(local_zone).strftime("%Y-%m-%d %H:%M:%S %Z")
    except (ValueError, ZoneInfoNotFoundError):
        return f"{raw} UTC" if "+00:00" in raw or raw.endswith("Z") else raw


def _empty_snapshot(error="MCP is not configured or unavailable"):
    return {
        "status": "unavailable",
        "mode": "hybrid-transition",
        "readOnly": True,
        "generatedAt": _iso_now(),
        "availableTools": [],
        "calls": [],
        "results": {},
        "error": str(error),
    }


def collect_base_evidence(force=False):
    global _BASE_CACHE, _BASE_CACHE_AT
    with _CACHE_LOCK:
        if not force and _BASE_CACHE is not None and time.monotonic() - _BASE_CACHE_AT < _BASE_CACHE_TTL:
            return copy.deepcopy(_BASE_CACHE)

        snapshot = _empty_snapshot()
        try:
            with ZimaBrainMcpClient() as client:
                available = sorted(tool["name"] for tool in client.list_tools())
                results = {}
                calls = []
                for tool, arguments in (
                    ("system_info", {}),
                    ("storage_mounts", {}),
                    ("docker_ps", {}),
                    ("system_processes", {"sort": "cpu", "limit": 25}),
                ):
                    if tool not in available:
                        continue
                    results[tool] = client.call_tool(tool, arguments)
                    calls.append(tool)
                snapshot = {
                    "status": "connected",
                    "mode": "hybrid-transition",
                    "readOnly": True,
                    "generatedAt": _iso_now(),
                    "availableTools": available,
                    "calls": calls,
                    "results": results,
                    "error": "",
                }
        except Exception as error:
            snapshot = _empty_snapshot(error)

        _BASE_CACHE = snapshot
        _BASE_CACHE_AT = time.monotonic()
        return copy.deepcopy(snapshot)


def _question_terms(question):
    return {part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in question).split() if len(part) > 2}


def _matching_container(question, containers):
    q = question.lower()
    exact = []
    fuzzy = []
    for container in containers:
        name = str(container.get("name", ""))
        image = str(container.get("image", ""))
        if name and name.lower() in q:
            exact.append(container)
        elif any(term in (name + " " + image).lower() for term in _question_terms(question)):
            fuzzy.append(container)
    candidates = exact or fuzzy
    return candidates[0] if len(candidates) == 1 else None


def _asks_filesystem_capacity(question):
    q = (question or "").lower()
    if any(
        phrase in q
        for phrase in (
            "filesystem usage",
            "disk usage",
            "storage usage",
            "free space",
            "capacity",
            "full filesystem",
            "100% used",
        )
    ):
        return True
    capacity_words = ("full", "usage", "used", "space")
    storage_words = ("filesystem", "filesystems", "disk", "disks", "storage", "mount", "mounts", "media")
    return any(word in q for word in capacity_words) and any(word in q for word in storage_words)


def collect_question_evidence(question, base=None):
    snapshot = copy.deepcopy(base or collect_base_evidence())
    if snapshot.get("status") != "connected":
        return snapshot

    q = (question or "").lower()
    snapshot["calls"] = []
    refresh = []
    if any(word in q for word in ("operating system", " cpu", "processor", "memory", " ram", "hardware")):
        refresh.append(("system_info", {}))
    if any(word in q for word in ("container", "docker", "app", "image")):
        refresh.append(("docker_ps", {}))
    if any(word in q for word in ("process", "cpu pressure", "cpu load", "high cpu", "memory pressure")):
        refresh.append(("system_processes", {"sort": "memory" if "memory" in q and "cpu" not in q else "cpu", "limit": 25}))
    if any(word in q for word in ("storage", "mount", "filesystem", "disk path")):
        refresh.append(("storage_mounts", {}))

    broad_storage_health = any(
        phrase in q
        for phrase in (
            "storage health",
            "disk health",
            "drive health",
            "check all storage",
            "storage problems",
            "disk problems",
            "drive problems",
        )
    )
    if broad_storage_health:
        refresh.extend((tool, {}) for tool in sorted(STORAGE_TOOLS))
    else:
        if any(phrase in q for phrase in ("storage inventory", "disk inventory", "list disks", "physical disks", "partitions")):
            refresh.append(("storage_inventory", {}))
        if _asks_filesystem_capacity(q):
            refresh.append(("filesystem_usage", {}))
        if any(word in q for word in ("smart", "sata", "hdd", "crc", "sector", "reallocated", "pending sector")):
            refresh.append(("smart_health", {}))
        if any(word in q for word in ("nvme", "ssd", "media error", "endurance")):
            refresh.append(("nvme_health", {}))
        if any(word in q for word in ("btrfs", "corruption", "generation error", "filesystem error")):
            refresh.append(("btrfs_health", {}))
        if any(word in q for word in ("raid", "mdraid", "zfs", "storage pool")):
            refresh.append(("raid_health", {}))

    containers = _items(snapshot.get("results", {}).get("docker_ps"))
    target = _matching_container(question, containers)
    needs_inspect = target and any(word in q for word in ("inspect", "fail", "error", "stopp", "unhealthy", "restart", "misconfig", "mount", "path", "open", "port", "permission", "running", "healthy", "privileged"))
    needs_logs = target and any(word in q for word in ("log", "error", "fail", "crash", "not open", "not loading"))

    try:
        with ZimaBrainMcpClient() as client:
            available = {tool["name"] for tool in client.list_tools()}
            for tool, arguments in refresh:
                if tool in available and tool not in snapshot["calls"]:
                    snapshot["results"][tool] = client.call_tool(tool, arguments)
                    snapshot["calls"].append(tool)

            containers = _items(snapshot.get("results", {}).get("docker_ps"))
            target = _matching_container(question, containers)
            snapshot["target"] = target.get("name") if target else None
            needs_inspect = target and any(word in q for word in ("inspect", "fail", "error", "stopp", "unhealthy", "restart", "misconfig", "mount", "path", "open", "port", "permission", "running", "healthy", "privileged"))
            needs_logs = target and any(word in q for word in ("log", "error", "fail", "crash", "not open", "not loading"))
            if not target:
                snapshot["generatedAt"] = _iso_now()
                return snapshot
            target_name = target["name"]
            if needs_inspect and "docker_inspect" in available:
                snapshot["results"]["docker_inspect"] = client.call_tool("docker_inspect", {"container": target_name})
                snapshot["calls"].append("docker_inspect")
            if needs_logs and "docker_logs" in available:
                snapshot["results"]["docker_logs"] = client.call_tool("docker_logs", {"container": target_name, "tail": 80})
                snapshot["calls"].append("docker_logs")
    except Exception as error:
        snapshot["targetedError"] = str(error)
    snapshot["generatedAt"] = _iso_now()
    return snapshot


def _gib(value):
    try:
        return f"{float(value) / (1024 ** 3):.2f} GiB"
    except (TypeError, ValueError):
        return "unknown"


def _verified_log_errors(logs):
    markers = re.compile(r"\b(error|fatal|panic|exception|failed|failure|critical)\b", re.IGNORECASE)
    errors = []
    for value in logs.get("lines", []) if isinstance(logs, dict) else []:
        line = str(value).strip()
        if markers.search(line):
            errors.append(line[:500])
    return errors


def render_mcp_direct_answer(snapshot, question):
    if snapshot.get("status") != "connected":
        return ""
    q = (question or "").lower()
    results = snapshot.get("results", {})
    lines = []

    system = results.get("system_info")
    if isinstance(system, dict) and any(word in q for word in ("operating system", " cpu", "processor", "memory", " ram", "hardware")):
        lines.extend(
            (
                f'- Your ZimaCube is running {system.get("os", "an unknown operating system")}.',
                f'- It has a {system.get("cpuModel", "CPU model that was not reported")} with {system.get("cpuCount", "?")} logical threads.',
                f'- It has {_gib(system.get("totalMemoryBytes"))} of memory in total, with {_gib(system.get("availableMemoryBytes"))} available when I checked.',
            )
        )

    containers = _items(results.get("docker_ps"))
    if containers and "container" in q and any(word in q for word in ("stopped", "unhealthy", "running", "restart")):
        stopped = [item for item in containers if item.get("state") not in {"running", "restarting"}]
        restarting = [item for item in containers if item.get("state") == "restarting"]
        unhealthy = [item for item in containers if item.get("health") == "unhealthy"]
        lines.append(f'- I found {len(containers)} containers: {len(stopped)} stopped, {len(restarting)} restarting and {len(unhealthy)} unhealthy.')
        if restarting:
            lines.append("- Restarting: " + ", ".join(str(item.get("name")) for item in restarting[:10]) + ".")
        if unhealthy:
            lines.append("- Unhealthy: " + ", ".join(str(item.get("name")) for item in unhealthy[:10]) + ".")

    processes = results.get("system_processes")
    if isinstance(processes, dict) and "cpu" in q and any(word in q for word in ("process", "pressure", "load", "high")):
        host_cpu = processes.get("hostCpuBusyPercent")
        sample_ms = processes.get("sampleWindowMs")
        items = _items(processes)[:5]
        lines.append(f'- I measured the CPU over {sample_ms} ms. The whole system was {host_cpu}% busy during that sample.')
        if items:
            lines.append("- Highest CPU processes in that sample:")
            for item in items:
                lines.append(
                    f'  - PID {item.get("pid")} `{item.get("name", "unknown")}`: '
                    f'{item.get("cpuPercentOfHost", 0)}% of host capacity '
                    f'({item.get("cpuPercentOfCore", 0)}% of one logical core).'
                )
        if isinstance(host_cpu, (int, float)):
            if host_cpu >= 80:
                lines.append("- Yes, the system was under high CPU pressure during that sample.")
            else:
                lines.append("- No, the system was not under high CPU pressure during that sample.")

    return "\n".join(lines)


def render_targeted_process_answer(snapshot, question):
    """Answer current CPU-process questions directly from the sampled MCP result."""
    if snapshot.get("status") != "connected":
        return ""
    q = (question or "").lower()
    if "cpu" not in q or not any(word in q for word in ("process", "pressure", "load", "high")):
        return ""

    processes = snapshot.get("results", {}).get("system_processes")
    if not isinstance(processes, dict):
        return ""

    host_cpu = processes.get("hostCpuBusyPercent")
    sample_ms = processes.get("sampleWindowMs")
    items = _items(processes)[:5]
    direct = [
        f"- I measured CPU activity over {sample_ms} ms. The whole system was {host_cpu}% busy during that sample."
    ]
    if items:
        direct.append("- The processes using the most CPU were:")
        for item in items:
            direct.append(
                f'  - PID {item.get("pid")} `{item.get("name", "unknown")}`: '
                f'{item.get("cpuPercentOfHost", 0)}% of total host capacity '
                f'({item.get("cpuPercentOfCore", 0)}% of one logical core).'
            )
    else:
        direct.append("- MCP did not return any process rows for this sample.")

    if isinstance(host_cpu, (int, float)):
        if host_cpu >= 80:
            direct.append("- Yes, this sample shows high host CPU pressure.")
            conclusion = "High CPU pressure was measured during the bounded MCP sample."
        else:
            direct.append("- No, this sample does not show high host CPU pressure.")
            conclusion = "No high CPU pressure was measured during the bounded MCP sample."
    else:
        direct.append("- Host CPU pressure could not be classified because MCP did not return a host-wide percentage.")
        conclusion = "Host CPU pressure could not be classified from the returned MCP sample."

    return "\n".join(
        [
            "### ZimaBrain Answer",
            "",
            "## ❓ Question asked",
            f"### {question.strip()}",
            "",
            "#### Verification status",
            "@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM LIVE BOUNDED MCP EVIDENCE",
            "- Current host and process CPU activity was sampled through the read-only MCP boundary.",
            "- Active layer: MCP Process Evidence Layer",
            "- Layer file: `app/brain/mcp_evidence.py`",
            "",
            "#### Plain-English answer",
            *direct,
            "",
            render_answer_evidence(snapshot),
            "#### Next safest step",
            "- If the CPU load returns, run this check while the slowdown is happening and compare whether the same process remains at the top.",
            "",
            "#### Forum-ready summary",
            conclusion,
        ]
    )


def _storage_device_line(device, kind):
    status = device.get("status", "unknown")
    model = device.get("model") or "unknown model"
    path = device.get("device", "unknown device")
    temperature = device.get("temperatureC")
    temperature_text = f" at {temperature}°C" if temperature is not None else ""
    if kind == "SMART":
        smart_state = "passed" if device.get("smartPassed") is True else "did not pass" if device.get("smartPassed") is False else "was unavailable"
        return (
            f'- `{path}` ({model}) is {status}{temperature_text}: SMART {smart_state}; '
            f'reallocated={device.get("reallocatedSectors", 0)}, pending={device.get("pendingSectors", 0)}, '
            f'offline-uncorrectable={device.get("offlineUncorrectable", 0)}, CRC={device.get("crcErrors", 0)}.'
        )
    if device.get("healthVerified") is not True:
        online = "online" if device.get("controllerState") == "live" else f'controller state={device.get("controllerState", "unknown")}'
        return (
            f'- `{path}` ({model}) is {online}{temperature_text}. Temperature and controller state are live, but '
            "endurance, media-error and critical-warning counters are not verified through the safe read-only boundary."
        )
    return (
        f'- `{path}` ({model}) is {status}{temperature_text}: critical warning={device.get("criticalWarning", 0)}, '
        f'media errors={device.get("mediaErrors", 0)}, endurance used={device.get("percentageUsed", "unknown")}%.'
    )


def _human_storage_size(value):
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        return "unknown size"
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024


def render_targeted_storage_answer(snapshot, question):
    """Render concise storage evidence from the fixed read-only collector."""
    if snapshot.get("status") != "connected":
        return ""
    q = (question or "").lower()
    storage_words = ("storage", "disk", "drive", "filesystem", "mount", "media", "capacity", "space", "smart", "nvme", "btrfs", "raid", "zfs", "crc", "sector")
    if not any(word in q for word in storage_words):
        return ""

    results = snapshot.get("results", {})
    requested = [tool for tool in snapshot.get("calls", []) if tool in STORAGE_TOOLS]
    available = [tool for tool in requested if isinstance(results.get(tool), dict)]
    if not available:
        return ""

    direct = []
    attention = []
    unverified = []

    inventory = results.get("storage_inventory")
    if isinstance(inventory, dict):
        disks = inventory.get("disks", []) if isinstance(inventory.get("disks"), list) else []
        direct.append(f'- I found {len(disks)} physical storage device(s):')
        for disk in disks:
            filesystems = []
            if disk.get("filesystem"):
                filesystems.append(str(disk.get("filesystem")))
            for partition in disk.get("partitions", []) if isinstance(disk.get("partitions"), list) else []:
                if partition.get("filesystem"):
                    filesystems.append(str(partition.get("filesystem")))
            filesystem_text = ", ".join(dict.fromkeys(filesystems)) if filesystems else "no filesystem reported"
            direct.append(
                f'  - `{disk.get("path", "unknown")}`: {disk.get("model") or "unknown model"}, '
                f'{_human_storage_size(disk.get("sizeBytes"))}, {filesystem_text}.'
            )

    usage = results.get("filesystem_usage")
    if isinstance(usage, dict):
        filesystems = usage.get("filesystems", []) if isinstance(usage.get("filesystems"), list) else []
        flagged = [item for item in filesystems if item.get("status") in ("attention", "critical")]
        informational = [item for item in filesystems if item.get("status") == "informational"]
        direct.append(f'- I checked {len(filesystems)} approved filesystem mount(s); {len(flagged)} require capacity attention.')
        for item in flagged[:8]:
            direct.append(f'- `{item.get("target")}` is {item.get("usedPercent")}% used ({item.get("status")}).')
            attention.append(f'{item.get("target")} capacity')
        for item in informational[:8]:
            direct.append(
                f'- `{item.get("target")}` is read-only {item.get("filesystem")} media. Its {item.get("usedPercent")}% figure is normal and is not a capacity warning.'
            )

    smart = results.get("smart_health")
    if isinstance(smart, dict):
        devices = smart.get("devices", []) if isinstance(smart.get("devices"), list) else []
        direct.append(f'- SMART checked {len(devices)} SATA/USB disk(s).')
        for device in devices:
            direct.append(_storage_device_line(device, "SMART"))
            for finding in device.get("findings", []) if isinstance(device.get("findings"), list) else []:
                direct.append(f'  - {finding.get("message", "Storage finding reported.")}')
                if finding.get("code") == "crc_errors":
                    direct.append("  - A CRC count usually points to the SATA cable, connector or backplane path. It is not evidence of disk-media failure by itself.")
            if device.get("status") != "healthy":
                attention.append(f'{device.get("device")} SMART')

    nvme = results.get("nvme_health")
    if isinstance(nvme, dict):
        devices = nvme.get("devices", []) if isinstance(nvme.get("devices"), list) else []
        direct.append(f'- NVMe evidence checked {len(devices)} controller(s).')
        for device in devices:
            direct.append(_storage_device_line(device, "NVMe"))
            for finding in device.get("findings", []) if isinstance(device.get("findings"), list) else []:
                if finding.get("code") != "nvme_smart_unavailable":
                    direct.append(f'  - {finding.get("message", "NVMe finding reported.")}')
            if device.get("healthVerified") is not True:
                unverified.append(f'{device.get("device")} NVMe SMART health')
            elif device.get("status") != "healthy":
                attention.append(f'{device.get("device")} NVMe')

    btrfs = results.get("btrfs_health")
    if isinstance(btrfs, dict):
        direct.append(
            f'- Btrfs reports {btrfs.get("observedFilesystems", 0)} filesystem(s), '
            f'{btrfs.get("multiDeviceFilesystems", 0)} multi-device, with {btrfs.get("errorCount", 0)} persistent device error(s).'
        )
        if btrfs.get("status") != "healthy":
            attention.append("Btrfs device errors")

    raid = results.get("raid_health")
    if isinstance(raid, dict):
        if raid.get("configured"):
            direct.append(f'- RAID/storage-pool evidence is configured and currently classified as {raid.get("status", "unknown")}.')
            if raid.get("status") != "healthy":
                attention.append("RAID/storage pool")
        else:
            zfs_loaded = bool((raid.get("zfs") or {}).get("kernelLoaded"))
            zfs_note = " The ZFS kernel module is loaded, but no configured ZFS pool was observed." if zfs_loaded else " No configured ZFS pool was observed."
            direct.append("- No active MD RAID or multi-device Btrfs filesystem was observed." + zfs_note + " RAID is not configured, so this is not reported as a health pass.")

    partially_verified = bool(snapshot.get("targetedError")) or len(available) != len(requested) or bool(unverified)
    status_state = "PARTIALLY VERIFIED" if partially_verified else "VERIFIED"
    status_title = "⚠️ PARTIALLY VERIFIED FROM LIVE MCP STORAGE EVIDENCE" if partially_verified else "✅ VERIFIED FROM LIVE MCP STORAGE EVIDENCE"
    status_detail = (
        "Some requested storage evidence was unavailable or blocked by the safe read-only boundary; only returned evidence is described."
        if partially_verified
        else "The requested storage evidence was collected through fixed read-only device and path allow-lists."
    )
    if attention:
        conclusion = "Storage evidence requires attention: " + ", ".join(dict.fromkeys(attention)) + "."
        next_step = "Review the named finding first. Do not replace or repair a disk solely from one counter; compare it with current SMART/NVMe health and whether the value increases."
    elif unverified:
        conclusion = "No critical NVMe finding was verified, but full NVMe SMART health remains unverified for: " + ", ".join(dict.fromkeys(unverified)) + "."
        next_step = "Do not grant the container write or broad administrative access merely to obtain these counters. Use a bounded host-side read-only collector if full NVMe SMART verification is required."
    else:
        conclusion = "No critical storage-health finding was returned by the requested MCP checks."
        next_step = "No repair is justified by this evidence. Repeat the same checks if a storage symptom appears or a counter changes."

    return "\n".join(
        [
            "### ZimaBrain Answer",
            "",
            "## ❓ Question asked",
            f"### {question.strip()}",
            "",
            "#### Verification status",
            f"@@VERIFY:{status_state}@@ {status_title}",
            f"- {status_detail}",
            "- Active layer: MCP Storage and Disk Health Layer",
            "- Layer file: `app/brain/mcp_evidence.py`",
            "",
            "#### Plain-English answer",
            *direct,
            f"- {conclusion}",
            "",
            render_answer_evidence(snapshot),
            "#### Next safest step",
            f"- {next_step}",
            "",
            "#### Forum-ready summary",
            conclusion,
        ]
    )


def mark_hybrid_mcp_verification(answer):
    """Correct legacy headings when a direct live MCP answer is inserted."""
    replacements = {
        "✅ VERIFIED FROM SAME-REPORT HOST EVIDENCE": "✅ VERIFIED FROM LIVE MCP AND SAME-REPORT HOST EVIDENCE",
        "- This answer uses current local host evidence.": "- This answer combines current read-only MCP host facts with current local verifier metrics.",
        "✅ VERIFIED FROM SAME-REPORT EVIDENCE": "✅ VERIFIED FROM LIVE MCP AND SAME-REPORT EVIDENCE",
        "- This answer is based on evidence found in the current report.": "- This answer combines current read-only MCP evidence with the existing local verifier.",
        "- The answer uses current same-report Docker inspect evidence.": "- The answer uses current read-only MCP Docker evidence.",
    }
    for old, new in replacements.items():
        answer = answer.replace(old, new, 1)
    return answer


def render_targeted_container_answer(snapshot, question):
    results = snapshot.get("results", {})
    inspect = results.get("docker_inspect")
    logs = results.get("docker_logs")
    if not isinstance(inspect, dict):
        return ""

    q = (question or "").lower()
    state = inspect.get("state", {})
    security = inspect.get("security", {})
    health = (state.get("health") or {}).get("status", "not reported")
    running_text = "running" if state.get("running", False) else f'not running; its state is {state.get("status", "unknown")}'
    health_text = f" and Docker reports it as {health}" if health != "not reported" else ", although it does not publish a Docker health status"
    privilege_text = "It is privileged" if security.get("privileged", False) else "It is not privileged"
    direct = [
        f'- `{inspect.get("name", "unknown")}` is {running_text}{health_text}.',
        f'- {privilege_text}, and it has restarted {inspect.get("restartCount", 0)} time(s).',
    ]
    status_state = "VERIFIED"
    status_title = "✅ VERIFIED FROM BOUNDED MCP EVIDENCE"
    status_detail = "The named container was inspected through the read-only MCP boundary."
    next_step = "No action is indicated by the requested container state alone. Review bounded logs only if a symptom is present."
    summary = f'MCP verified `{inspect.get("name", "unknown")}` state, health, privilege mode and restart count.'

    if "log" in q and isinstance(logs, dict):
        errors = _verified_log_errors(logs)
        direct.append(f'- I checked its recent logs. MCP safely returned {logs.get("returnedLines", 0)} redacted line(s) from the requested tail of {logs.get("requestedTail", 0)}.')
        if errors:
            direct.append(f'- I found {len(errors)} line(s) containing a verified error marker:')
            direct.extend(f'  - `{line}`' for line in errors[:5])
            next_step = "Start with the first verified error line, correlate it with container state, then inspect configuration without exposing secrets."
            summary = f'MCP found {len(errors)} error-marker line(s) in the bounded redacted log tail for `{inspect.get("name", "unknown")}`.'
        else:
            direct.append("- I did not find an error marker in the returned log lines.")
            direct.append("- That only covers this recent bounded log sample; it does not prove that older logs are error-free.")
            status_state = "PARTIALLY VERIFIED"
            status_title = "⚠️ VERIFIED BOUNDED LOG OBSERVATION"
            status_detail = "The returned MCP log tail was checked; evidence outside that bounded tail was not measured."
            next_step = "No repair is justified from this log tail. Recheck while the reported symptom is occurring if necessary."
            summary = f'No error marker was found in the bounded redacted MCP log tail for `{inspect.get("name", "unknown")}`.'

    return "\n".join(
        [
            "### ZimaBrain Answer",
            "",
            "## ❓ Question asked",
            f"### {question.strip()}",
            "",
            "#### Verification status",
            f"@@VERIFY:{status_state}@@ {status_title}",
            f"- {status_detail}",
            "- Active layer: MCP Container Evidence Layer",
            "- Layer file: `app/brain/mcp_evidence.py`",
            "",
            "#### Plain-English answer",
            *direct,
            "",
            render_answer_evidence(snapshot),
            "#### Next safest step",
            f"- {next_step}",
            "",
            "#### Forum-ready summary",
            summary,
        ]
    )


def legacy_overrides(snapshot):
    """Translate safe MCP results into formats used by established Brain layers."""
    if snapshot.get("status") != "connected":
        return {}
    results = snapshot.get("results", {})
    containers = _items(results.get("docker_ps"))
    mounts = _items(results.get("storage_mounts"))
    processes = _items(results.get("system_processes"))

    docker_lines = []
    for container in containers:
        ports = []
        for port in container.get("ports", []):
            private = port.get("private")
            public = port.get("public")
            protocol = port.get("type") or "tcp"
            if public:
                ports.append(f"{port.get('ip') or '0.0.0.0'}:{public}->{private}/{protocol}")
            elif private:
                ports.append(f"{private}/{protocol}")
        docker_lines.append("|".join((str(container.get("name", "")), str(container.get("image", "")), str(container.get("status", "")), ", ".join(ports))))

    mount_lines = []
    for mount in mounts:
        options = ",".join(str(value) for value in mount.get("options", []))
        mount_lines.append(
            f'SOURCE="{mount.get("source", "")}" TARGET="{mount.get("target", "")}" '
            f'FSTYPE="{mount.get("filesystem", "")}" OPTIONS="{options}"'
        )

    process_lines = ["PID PPID COMMAND STAT CPU_TICKS RSS_BYTES"]
    for process in processes:
        process_lines.append(
            f'{process.get("pid", 0)} {process.get("parentPid", 0)} {process.get("name", "unknown")} '
            f'{process.get("state", "?")} {process.get("cpuTicks", 0)} {process.get("residentMemoryBytes", 0)}'
        )
    return {
        "docker_ps": "\n".join(docker_lines),
        # Keep these under MCP-specific keys until their semantics reach full
        # parity with findmnt and instantaneous ps %CPU used by legacy layers.
        "mcp_storage_mounts": "\n".join(mount_lines),
        "mcp_processes": "\n".join(process_lines),
    }


def render_answer_evidence(snapshot):
    if snapshot.get("status") != "connected":
        return "\n".join(
            (
                "#### Live MCP evidence",
                "- Status: unavailable; the existing local verifier supplied this answer.",
                f'- Detail: {snapshot.get("error", "connection failed")}',
                "- Safety mode: hybrid transition; no MCP action tool was called.",
            )
        )

    results = snapshot.get("results", {})
    system = results.get("system_info", {})
    containers = _items(results.get("docker_ps"))
    mounts = _items(results.get("storage_mounts"))
    lines = [
        "#### Live MCP evidence",
        f'- Status: connected · read-only · {len(snapshot.get("availableTools", []))} allow-listed tools discovered.',
        f'- Evidence time: {_format_evidence_time(snapshot.get("generatedAt"))}.',
        f'- Host: {system.get("hostname", "unknown")} · {system.get("os", "OS unknown")} · {system.get("cpuCount", "?")} CPU threads.',
        f'- Current inventory: {len(containers)} containers and {len(mounts)} approved host mounts observed.',
        f'- Tools called for this evidence: {", ".join(snapshot.get("calls", [])) or "none"}.',
    ]
    if any(tool in STORAGE_TOOLS for tool in snapshot.get("calls", [])):
        lines.append("- Storage boundary: fixed device/path allow-lists in an isolated collector; the main MCP server has no `/dev` access.")
    inspect = results.get("docker_inspect")
    if isinstance(inspect, dict):
        state = inspect.get("state", {})
        health = (state.get("health") or {}).get("status", "not reported")
        lines.append(
            f'- Target `{inspect.get("name", "unknown")}`: state {state.get("status", "unknown")}, '
            f'health {health}, restarts {inspect.get("restartCount", 0)}, privileged {inspect.get("security", {}).get("privileged", False)}.'
        )
    logs = results.get("docker_logs")
    if isinstance(logs, dict):
        lines.append(
            f'- Redacted log evidence: {logs.get("returnedLines", 0)} of at most {logs.get("requestedTail", 0)} requested lines returned.'
        )
    if snapshot.get("targetedError"):
        lines.append(f'- Targeted MCP evidence was incomplete: {snapshot["targetedError"]}.')
    lines.append("- Audit: every MCP tool call is retained in the append-only MCP ledger.")
    lines.append("- Transition note: unsupported evidence still uses the existing local verifier until MCP parity is complete.")
    return "\n".join(lines)


def status_summary(snapshot=None):
    snapshot = snapshot or collect_base_evidence()
    return {
        "status": snapshot.get("status", "unavailable"),
        "mode": snapshot.get("mode", "hybrid-transition"),
        "readOnly": bool(snapshot.get("readOnly", True)),
        "availableTools": len(snapshot.get("availableTools", [])),
        "generatedAt": snapshot.get("generatedAt"),
        "error": snapshot.get("error", ""),
    }
