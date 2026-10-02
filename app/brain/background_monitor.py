import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
from datetime import datetime

from brain import health_memory


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"
HOST_PROC_ROOT = Path("/host/proc")
HOST_SYS_ROOT = Path("/host/sys")
DOCKER_SOCKET = "/var/run/docker.sock"

_START_LOCK = threading.Lock()
_THREAD = None
_STATUS_LOCK = threading.Lock()
_STATUS = {
    "enabled": False,
    "running": False,
    "last_sample_at": "",
    "last_error": "",
    "sample_id": None,
}


def _set_status(**values):
    with _STATUS_LOCK:
        _STATUS.update(values)


def status():
    with _STATUS_LOCK:
        return dict(_STATUS)


def _env_bool(name, default=True):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}


def _env_int(name, default, minimum, maximum):
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _boot_id():
    return _read_text(HOST_PROC_ROOT / "sys/kernel/random/boot_id").strip()


def _uptime_seconds():
    try:
        return float(_read_text(HOST_PROC_ROOT / "uptime").split()[0])
    except (IndexError, TypeError, ValueError):
        return None


def _cpu_snapshot():
    line = next(
        (line for line in _read_text(HOST_PROC_ROOT / "stat").splitlines()
         if line.startswith("cpu ")),
        "",
    )
    parts = line.split()[1:]
    try:
        values = [int(value) for value in parts[:10]]
    except ValueError:
        return None
    if len(values) < 5:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return {"total": sum(values), "idle": idle}


def _memory_snapshot():
    values = {}
    for line in _read_text(HOST_PROC_ROOT / "meminfo").splitlines():
        match = re.match(r"^(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+(\d+)", line)
        if match:
            values[match.group(1)] = int(match.group(2))
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    return {
        "total_kb": total,
        "memory_percent": round((total - available) * 100 / total, 1) if total else None,
        "swap_percent": round((swap_total - swap_free) * 100 / swap_total, 1)
        if swap_total else 0.0,
    }


def _disk_snapshot():
    block_root = HOST_SYS_ROOT / "block"
    try:
        devices = {
            name for name in os.listdir(block_root)
            if re.match(r"^(sd[a-z]+|hd[a-z]+|nvme\d+n\d+|mmcblk\d+)$", name)
        }
    except Exception:
        devices = set()
    read_bytes = 0
    write_bytes = 0
    for line in _read_text(HOST_PROC_ROOT / "diskstats").splitlines():
        parts = line.split()
        if len(parts) < 14 or parts[2] not in devices:
            continue
        try:
            read_bytes += int(parts[5]) * 512
            write_bytes += int(parts[9]) * 512
        except ValueError:
            continue
    if not devices:
        return None
    return {"read_bytes": read_bytes, "write_bytes": write_bytes}


def _process_snapshot():
    result = {}
    try:
        entries = list(HOST_PROC_ROOT.iterdir())
    except Exception:
        return result
    for entry in entries:
        if not entry.name.isdigit():
            continue
        stat = _read_text(entry / "stat").strip()
        match = re.match(r"^(\d+) \((.*)\) ([A-Za-z]) (.*)$", stat)
        if not match:
            continue
        fields = match.group(4).split()
        if len(fields) < 21:
            continue
        try:
            ticks = int(fields[10]) + int(fields[11])
            start_time = int(fields[18])
        except ValueError:
            continue
        status_text = _read_text(entry / "status")
        rss_match = re.search(r"^VmRSS:\s+(\d+)\s+kB", status_text, re.M)
        rss_kb = int(rss_match.group(1)) if rss_match else 0
        command = (
            _read_text(entry / "comm").strip() or match.group(2)
        ).strip()[:120]
        result[(int(entry.name), start_time)] = {
            "pid": int(entry.name),
            "command": command,
            "ticks": ticks,
            "rss_kb": rss_kb,
        }
    return result


def _decode_mount_path(value):
    def replace(match):
        try:
            return chr(int(match.group(1), 8))
        except ValueError:
            return match.group(0)
    return re.sub(r"\\([0-7]{3})", replace, value or "")


def _mount_snapshot():
    mounts = []
    for line in _read_text(HOST_PROC_ROOT / "1/mountinfo").splitlines():
        parts = line.split()
        if "-" not in parts or len(parts) < 10:
            continue
        separator = parts.index("-")
        if separator + 2 >= len(parts):
            continue
        target = _decode_mount_path(parts[4])
        if not (
            target == "/"
            or target == "/DATA"
            or target.startswith("/DATA/")
            or target == "/media"
            or target.startswith("/media/")
        ):
            continue
        options = set(parts[5].split(","))
        mounts.append({
            "target": target,
            "source": _decode_mount_path(parts[separator + 2]),
            "fstype": parts[separator + 1],
            "read_only": "ro" in options,
        })
    return sorted(mounts, key=lambda item: item["target"])


def _decode_chunked(body):
    output = b""
    position = 0
    while True:
        line_end = body.find(b"\r\n", position)
        if line_end < 0:
            return body
        try:
            size = int(body[position:line_end].split(b";", 1)[0], 16)
        except ValueError:
            return body
        position = line_end + 2
        if size == 0:
            return output
        output += body[position:position + size]
        position += size + 2


def _docker_get(path):
    if not Path(DOCKER_SOCKET).exists():
        raise FileNotFoundError("Docker socket is not available")
    request = (
        f"GET {path} HTTP/1.1\r\nHost: docker\r\nConnection: close\r\n\r\n"
    ).encode()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(4)
        sock.connect(DOCKER_SOCKET)
        sock.sendall(request)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    data = b"".join(chunks)
    header, separator, body = data.partition(b"\r\n\r\n")
    if not separator or not re.search(rb"HTTP/1\.[01] 2\d\d", header.split(b"\r\n", 1)[0]):
        raise RuntimeError("Docker API returned a non-success response")
    if b"transfer-encoding: chunked" in header.lower():
        body = _decode_chunked(body)
    parsed = json.loads(body.decode("utf-8", errors="replace"))
    if not isinstance(parsed, list):
        raise RuntimeError("Docker API returned an unexpected response")
    return parsed


def _container_snapshot():
    rows = []
    for item in _docker_get("/containers/json?all=1"):
        names = item.get("Names") or []
        rows.append({
            "name": (names[0].lstrip("/") if names else str(item.get("Id", ""))[:12]),
            "state": str(item.get("State", "unknown") or "unknown").lower(),
            "image": str(item.get("Image", "unknown") or "unknown")[:200],
        })
    return sorted(rows, key=lambda item: item["name"])


def _run_host(command, timeout=10):
    try:
        return subprocess.check_output(
            [
                "nsenter", "-t", "1", "-m", "-u", "-n", "-i", "--",
                "sh", "-lc", command,
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        ).strip()
    except subprocess.CalledProcessError as error:
        return (error.output or "").strip()
    except Exception as error:
        return f"ERROR: {error}"


def _matching_lines(text, patterns, limit=12):
    compiled = [re.compile(pattern, re.I) for pattern in patterns]
    matches = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line and any(pattern.search(line) for pattern in compiled):
            matches.append(line[:600])
    return matches[-limit:]


def assess_previous_boot_journal(current_boot_id, boot_list, kernel_log, journal_log):
    previous_boot_id = ""
    for line in str(boot_list or "").splitlines():
        match = re.match(r"^\s*(-?\d+)\s+([0-9a-fA-F-]{16,})\b", line)
        if match and int(match.group(1)) == -1:
            previous_boot_id = match.group(2)
            break

    combined = "\n".join([str(kernel_log or ""), str(journal_log or "")])
    unavailable_markers = (
        "no journal files were found",
        "no entries for boot",
        "failed to look up boot",
        "no persistent journal",
        "journalctl: not found",
    )
    combined_lower = combined.lower().strip()
    journal_available = bool(combined_lower) and not any(
        marker in combined_lower for marker in unavailable_markers
    ) and not combined_lower.startswith("error:")

    panic_lines = _matching_lines(combined, (
        r"kernel panic", r"panic - not syncing", r"not syncing:.*panic",
    ))
    clean_lines = _matching_lines(journal_log, (
        r"systemd-shutdown", r"reboot: restarting system",
        r"reached target (system reboot|power-off|shutdown)",
        r"shutting down", r"powering off",
    ))
    manual_lines = _matching_lines(journal_log, (
        r"systemd-logind.*power key", r"reboot requested by",
        r"systemctl.*reboot", r"shutdown.*requested by",
    ))
    update_reboot_lines = _matching_lines(journal_log, (
        r"(?:rauc|zimaos[- ]?updater|casaos[- ]?installer).*(?:trigger|request|initiat).*reboot",
        r"reboot.*(?:rauc|zimaos[- ]?update|os update)",
    ))
    update_lines = _matching_lines(journal_log, (
        r"\brauc\b", r"zimaos[- ]?updater",
        r"casaos[- ]?installer.*(?:update|upgrade)",
    ))
    oom_lines = _matching_lines(combined, (
        r"out of memory", r"oom-kill", r"oom_reaper", r"killed process \d+",
    ))

    clean_shutdown = bool(clean_lines)
    kernel_panic = bool(panic_lines)
    manual_reboot = bool(manual_lines)
    update_reboot = bool(update_reboot_lines)
    abrupt_possible = bool(
        previous_boot_id and journal_available and not clean_shutdown
        and not kernel_panic and not update_reboot
    )

    return {
        "boot_id": str(current_boot_id or ""),
        "observed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "previous_boot_id": previous_boot_id,
        "journal_available": journal_available,
        "clean_shutdown": clean_shutdown,
        "kernel_panic": kernel_panic,
        "manual_reboot": manual_reboot,
        "update_reboot": update_reboot,
        "update_activity": bool(update_lines),
        "oom_before_reboot": bool(oom_lines),
        "abrupt_shutdown_possible": abrupt_possible,
        "details": {
            "panic": panic_lines,
            "clean_shutdown": clean_lines,
            "manual_reboot": manual_lines,
            "update_reboot": update_reboot_lines,
            "update_activity": update_lines,
            "oom": oom_lines,
        },
    }


def inspect_previous_boot():
    current = _boot_id()
    boot_list = _run_host("journalctl --list-boots --no-pager 2>/dev/null | tail -6", 10)
    kernel_log = _run_host(
        "journalctl -b -1 -k --no-pager -n 600 -o short-iso 2>/dev/null",
        15,
    )
    journal_log = _run_host(
        "journalctl -b -1 --no-pager -n 900 -o short-iso 2>/dev/null",
        20,
    )
    return assess_previous_boot_journal(
        current, boot_list, kernel_log, journal_log
    )


def _kernel_events():
    output = _run_host(
        "journalctl -k -b --since '-2 minutes' --no-pager -o short-iso "
        "2>/dev/null | tail -500",
        10,
    )
    patterns = {
        "oom": (
            "critical",
            re.compile(r"out of memory|oom-kill|oom_reaper|killed process \d+", re.I),
            "Kernel OOM activity was recorded.",
        ),
        "filesystem_error": (
            "attention",
            re.compile(
                r"I/O error|buffer I/O|EXT4-fs error|BTRFS.*error|XFS.*error|"
                r"remounting filesystem read-only",
                re.I,
            ),
            "A kernel filesystem or block-I/O error was recorded.",
        ),
        "kernel_panic": (
            "critical",
            re.compile(r"kernel panic|panic - not syncing", re.I),
            "Kernel panic evidence was recorded.",
        ),
    }
    events = []
    for raw in output.splitlines():
        line = raw.strip()
        for kind, (severity, pattern, message) in patterns.items():
            if not pattern.search(line):
                continue
            digest = hashlib.sha256(line.encode("utf-8", errors="replace")).hexdigest()
            events.append({
                "kind": kind,
                "severity": severity,
                "message": message,
                "evidence": line,
                "fingerprint": f"journal:{digest}",
            })
            break
    return events


class BackgroundMonitor:
    def __init__(self, db_path=TREND_DB_PATH, interval=60, retention_days=7):
        self.db_path = db_path
        self.interval = max(15, int(interval))
        self.retention_days = max(1, min(int(retention_days), 30))
        self.stop_event = threading.Event()
        self.previous_cpu = None
        self.previous_processes = {}
        self.previous_disk = None
        self.previous_epoch = None
        self.previous_sample = None

    def _rate(self, current, previous, key, elapsed):
        if not current or not previous or not elapsed or elapsed <= 0:
            return None
        return round(max(float(current[key]) - float(previous[key]), 0.0) / elapsed, 1)

    def collect(self):
        now = time.time()
        boot_id = _boot_id()
        cpu = _cpu_snapshot()
        memory = _memory_snapshot()
        disk = _disk_snapshot()
        processes = _process_snapshot()
        mounts = _mount_snapshot()
        try:
            containers = _container_snapshot()
            docker_error = ""
        except Exception as error:
            containers = []
            docker_error = f"docker inventory unavailable: {error}"

        elapsed = now - self.previous_epoch if self.previous_epoch else None
        cpu_percent = None
        total_delta = None
        if cpu and self.previous_cpu:
            total_delta = cpu["total"] - self.previous_cpu["total"]
            idle_delta = cpu["idle"] - self.previous_cpu["idle"]
            if total_delta > 0:
                cpu_percent = round(
                    max(0.0, min(100.0, (total_delta - idle_delta) * 100 / total_delta)),
                    1,
                )

        top_cpu = []
        if total_delta and total_delta > 0:
            for key, item in processes.items():
                previous = self.previous_processes.get(key)
                if not previous:
                    continue
                delta = item["ticks"] - previous["ticks"]
                if delta <= 0:
                    continue
                top_cpu.append({
                    "pid": item["pid"],
                    "command": item["command"],
                    "host_percent": round(delta * 100 / total_delta, 1),
                })
            top_cpu.sort(key=lambda item: item["host_percent"], reverse=True)
            top_cpu = top_cpu[:5]

        mem_total = memory.get("total_kb", 0)
        top_memory = sorted(
            ({
                "pid": item["pid"],
                "command": item["command"],
                "rss_mb": round(item["rss_kb"] / 1024, 1),
                "memory_percent": round(item["rss_kb"] * 100 / mem_total, 1)
                if mem_total else None,
            } for item in processes.values() if item["rss_kb"] > 0),
            key=lambda item: item["rss_mb"],
            reverse=True,
        )[:5]

        events = _kernel_events()
        previous = self.previous_sample if (
            self.previous_sample and self.previous_sample.get("boot_id") == boot_id
        ) else None
        if previous:
            for metric, threshold, kind, label in (
                ("cpu_percent", 95, "high_cpu", "Host CPU reached the critical threshold."),
                ("memory_percent", 90, "high_memory", "Host memory use reached the critical threshold."),
            ):
                current_value = cpu_percent if metric == "cpu_percent" else memory[metric]
                previous_value = previous.get(metric)
                if (
                    current_value is not None and current_value >= threshold
                    and (previous_value is None or previous_value < threshold)
                ):
                    events.append({
                        "kind": kind,
                        "severity": "attention",
                        "message": f"{label} Current value: {current_value:.1f}%.",
                        "evidence": json.dumps(top_cpu if metric == "cpu_percent" else top_memory),
                        "fingerprint": f"{boot_id}:{kind}:{int(now // 600)}",
                    })

            previous_mounts = {
                (item.get("target"), item.get("source"), item.get("read_only"))
                for item in previous.get("mounts", [])
            }
            current_mounts = {
                (item.get("target"), item.get("source"), item.get("read_only"))
                for item in mounts
            }
            if previous_mounts != current_mounts:
                changed = sorted(previous_mounts.symmetric_difference(current_mounts))
                digest = hashlib.sha256(repr(changed).encode()).hexdigest()
                events.append({
                    "kind": "filesystem_mount_change",
                    "severity": "attention" if any(item[2] for item in current_mounts) else "information",
                    "message": "A tracked host filesystem mount changed.",
                    "evidence": repr(changed)[:4000],
                    "fingerprint": f"mount:{boot_id}:{digest}",
                })

            previous_states = {
                item.get("name"): item.get("state")
                for item in previous.get("containers", [])
            }
            current_states = {
                item.get("name"): item.get("state") for item in containers
            }
            if previous_states != current_states:
                changes = {
                    name: {"previous": previous_states.get(name), "current": current_states.get(name)}
                    for name in sorted(set(previous_states) | set(current_states))
                    if previous_states.get(name) != current_states.get(name)
                }
                digest = hashlib.sha256(json.dumps(changes, sort_keys=True).encode()).hexdigest()
                events.append({
                    "kind": "container_state_change",
                    "severity": "information",
                    "message": f"Container state changed for {len(changes)} container(s).",
                    "evidence": json.dumps(changes, sort_keys=True)[:4000],
                    "fingerprint": f"container:{boot_id}:{digest}",
                })

        read_only = [item["target"] for item in mounts if item["read_only"]]
        status_parts = []
        if not boot_id:
            status_parts.append("host boot ID unavailable")
        if docker_error:
            status_parts.append(docker_error)
        if not mounts:
            status_parts.append("host mount inventory unavailable")
        if read_only:
            status_parts.append("read-only tracked mounts: " + ", ".join(read_only))

        sample = {
            "created_at": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S"),
            "created_epoch": now,
            "boot_id": boot_id,
            "uptime_seconds": _uptime_seconds(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.get("memory_percent"),
            "swap_percent": memory.get("swap_percent"),
            "disk_read_bps": self._rate(disk, self.previous_disk, "read_bytes", elapsed),
            "disk_write_bps": self._rate(disk, self.previous_disk, "write_bytes", elapsed),
            "running_containers": sum(item["state"] == "running" for item in containers),
            "total_containers": len(containers),
            "top_cpu": top_cpu,
            "top_memory": top_memory,
            "containers": containers,
            "mounts": mounts,
            "collector_status": "; ".join(status_parts) if status_parts else "ok",
            "events": events,
        }

        self.previous_cpu = cpu
        self.previous_processes = processes
        self.previous_disk = disk
        self.previous_epoch = now
        self.previous_sample = sample
        return sample

    def sample_once(self):
        sample = self.collect()
        result = health_memory.record_monitor_sample(
            sample,
            db_path=self.db_path,
            retention_days=self.retention_days,
            max_samples=max(120, int(86400 / self.interval) * self.retention_days),
        )
        _set_status(
            running=True,
            last_sample_at=sample.get("created_at", ""),
            last_error="" if result.get("ok") else result.get("error", "unknown error"),
            sample_id=result.get("sample_id"),
        )
        return result

    def run(self):
        _set_status(enabled=True, running=True)
        try:
            evidence = inspect_previous_boot()
            health_memory.record_monitor_boot_evidence(
                evidence, db_path=self.db_path
            )
        except Exception as error:
            _set_status(last_error=f"boot evidence: {error}")

        while not self.stop_event.is_set():
            try:
                self.sample_once()
            except Exception as error:
                _set_status(running=True, last_error=str(error)[:500])
            self.stop_event.wait(self.interval)
        _set_status(running=False)


def start_background_monitor(db_path=TREND_DB_PATH):
    global _THREAD
    enabled = _env_bool("ZIMABRAIN_MONITOR_ENABLED", True)
    _set_status(enabled=enabled)
    if not enabled:
        return None
    with _START_LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return _THREAD
        interval = _env_int(
            "ZIMABRAIN_MONITOR_INTERVAL_SECONDS", 60, 15, 3600
        )
        retention_days = _env_int(
            "ZIMABRAIN_MONITOR_RETENTION_DAYS", 7, 1, 30
        )
        monitor = BackgroundMonitor(
            db_path=db_path,
            interval=interval,
            retention_days=retention_days,
        )
        _THREAD = threading.Thread(
            target=monitor.run,
            name="zimabrain-background-monitor",
            daemon=True,
        )
        _THREAD.monitor = monitor
        _THREAD.start()
        return _THREAD
