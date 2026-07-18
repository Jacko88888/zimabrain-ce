import re
import shlex
import sqlite3
from datetime import datetime


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"

COUNTER_METRICS = {
    "reallocated_sectors",
    "pending_sectors",
    "uncorrectable_sectors",
    "crc_errors",
    "unsafe_shutdowns",
    "media_errors",
    "error_log_entries",
    "restart_count",
}


def _observation(category, entity_key, entity_name, metric, *, kind="state",
                 numeric_value=None, text_value=None, unit="", issue=False,
                 evidence=""):
    return {
        "category": category,
        "entity_key": str(entity_key or "unknown"),
        "entity_name": str(entity_name or entity_key or "unknown"),
        "metric": metric,
        "kind": kind,
        "numeric_value": numeric_value,
        "text_value": None if text_value is None else str(text_value),
        "unit": unit,
        "issue": 1 if issue else 0,
        "evidence": str(evidence or "")[:1000],
    }


def _pairs(line):
    values = {}
    try:
        for token in shlex.split(line or ""):
            if "=" in token:
                key, value = token.split("=", 1)
                values[key] = value
    except ValueError:
        return {}
    return values


def _disk_identities(text):
    identities = {}
    for raw in (text or "").splitlines():
        values = _pairs(raw)
        name = values.get("NAME", "").strip()
        if not name or values.get("TYPE", "disk") != "disk":
            continue
        serial = values.get("SERIAL", "").strip()
        model = values.get("MODEL", "").strip()
        identities[f"/dev/{name}"] = {
            "key": serial or f"device:{name}",
            "name": " ".join(x for x in [model, f"({name})"] if x).strip(),
            "serial": serial,
            "model": model,
        }
    return identities


def _sections(text, heading):
    result = []
    current_device = None
    current_lines = []
    pattern = re.compile(rf"^=====\s+{re.escape(heading)}\s+(/dev/\S+)\s+=====$", re.I)
    for raw in (text or "").splitlines():
        match = pattern.match(raw.strip())
        if match:
            if current_device is not None:
                result.append((current_device, current_lines))
            current_device = match.group(1)
            current_lines = []
        elif current_device is not None:
            current_lines.append(raw)
    if current_device is not None:
        result.append((current_device, current_lines))
    return result


def _last_integer(line):
    match = re.search(r"(-?\d+)\s*$", line or "")
    return int(match.group(1)) if match else None


def _smart_observations(evidence, identities):
    observations = []
    attributes = {
        "Reallocated_Sector_Ct": "reallocated_sectors",
        "Current_Pending_Sector": "pending_sectors",
        "Offline_Uncorrectable": "uncorrectable_sectors",
        "UDMA_CRC_Error_Count": "crc_errors",
    }
    for device, lines in _sections(evidence.get("smart", ""), "SMART"):
        identity = identities.get(device, {})
        serial = identity.get("serial", "")
        model = identity.get("model", "")
        for line in lines:
            if line.lower().startswith("serial number:") and not serial:
                serial = line.split(":", 1)[1].strip()
            if (line.lower().startswith("device model:") or
                    line.lower().startswith("model family:")) and not model:
                model = line.split(":", 1)[1].strip()
        entity_key = serial or identity.get("key") or f"device:{device.rsplit('/', 1)[-1]}"
        entity_name = identity.get("name") or " ".join(x for x in [model, f"({device})"] if x)
        for line in lines:
            for attribute, metric in attributes.items():
                if re.search(rf"\b{re.escape(attribute)}\b", line, re.I):
                    value = _last_integer(line)
                    if value is not None:
                        observations.append(_observation(
                            "smart", entity_key, entity_name, metric,
                            kind="counter", numeric_value=value,
                            unit="count", issue=value > 0, evidence=line.strip(),
                        ))
                    break
        health_line = next((x.strip() for x in lines if
                            "overall-health self-assessment test result" in x.lower()), "")
        if health_line:
            health = health_line.rsplit(":", 1)[-1].strip().upper()
            observations.append(_observation(
                "smart", entity_key, entity_name, "health",
                text_value=health, issue=health not in {"PASSED", "OK"},
                evidence=health_line,
            ))
    return observations


def _nvme_number(value):
    match = re.search(r"-?\d[\d,]*", value or "")
    return int(match.group(0).replace(",", "")) if match else None


def _temperature_c(value):
    kelvin = re.search(r"\((\d+(?:\.\d+)?)\s*K\)", value or "", re.I)
    if kelvin:
        return round(float(kelvin.group(1)) - 273.15, 1)
    celsius = re.search(r"(-?\d+(?:\.\d+)?)\s*°?C\b", value or "", re.I)
    if celsius:
        return float(celsius.group(1))
    fahrenheit = re.search(r"(-?\d+(?:\.\d+)?)\s*°?F\b", value or "", re.I)
    if fahrenheit:
        return round((float(fahrenheit.group(1)) - 32) * 5 / 9, 1)
    return None


def _nvme_observations(evidence, identities):
    observations = []
    fields = {
        "critical_warning": ("critical_warning", "state"),
        "unsafe_shutdowns": ("unsafe_shutdowns", "counter"),
        "media_errors": ("media_errors", "counter"),
        "num_err_log_entries": ("error_log_entries", "counter"),
    }
    for device, lines in _sections(evidence.get("nvme_smart", ""), "NVME"):
        identity = identities.get(device, {})
        entity_key = identity.get("key") or f"device:{device.rsplit('/', 1)[-1]}"
        entity_name = identity.get("name") or device
        for line in lines:
            if ":" not in line:
                continue
            key, value_text = [x.strip() for x in line.split(":", 1)]
            normalized = key.lower().replace(" ", "_")
            if normalized in fields:
                metric, kind = fields[normalized]
                value = _nvme_number(value_text)
                if value is not None:
                    observations.append(_observation(
                        "nvme", entity_key, entity_name, metric,
                        kind=kind, numeric_value=value, unit="count",
                        issue=value > 0, evidence=line.strip(),
                    ))
            elif normalized == "temperature":
                value = _temperature_c(value_text)
                if value is not None:
                    observations.append(_observation(
                        "nvme", entity_key, entity_name, "temperature",
                        kind="gauge", numeric_value=value, unit="C",
                        issue=value >= 70, evidence=line.strip(),
                    ))
    return observations


def _container_observations(text):
    observations = []
    for raw in (text or "").splitlines():
        parts = raw.strip().split("|", 6)
        if len(parts) < 7:
            continue
        name, image, state, health, restarts, started, finished = parts
        name = name.lstrip("/")
        state = state.lower().strip()
        health = health.lower().strip() or "none"
        try:
            restart_count = int(restarts)
        except ValueError:
            restart_count = 0
        observations.extend([
            _observation("container", name, name, "state", text_value=state,
                         issue=state != "running", evidence=raw),
            _observation("container", name, name, "health", text_value=health,
                         issue=state == "running" and health == "unhealthy",
                         evidence=raw),
            _observation("container", name, name, "restart_count", kind="counter",
                         numeric_value=restart_count, unit="count",
                         issue=restart_count > 0, evidence=raw),
            _observation("container", name, name, "image", kind="identity",
                         text_value=image, evidence=raw),
        ])
    return observations


def _related_service_name(unit):
    if unit.endswith("-watchdog.service"):
        return unit.replace("-watchdog.service", ".service")
    if unit.endswith("-delay.service"):
        return unit.replace("-delay.service", ".service")
    return ""


def _service_observations(evidence):
    states = {}
    observations = []

    for raw in (evidence.get("active_services", "") or "").splitlines():
        parts = raw.strip().split(None, 4)
        if len(parts) < 4:
            continue
        unit, load, active, sub = parts[:4]
        if not re.search(r"\.(service|timer|mount|socket)$", unit):
            continue
        states[unit] = {
            "active": active.lower(),
            "sub": sub.lower(),
            "evidence": raw.strip(),
        }

    current_unit = ""
    current_lines = []

    def save_hotlist_block():
        if not current_unit:
            return
        props = {}
        is_active = ""
        for line in current_lines:
            stripped = line.strip()
            if "=" in stripped:
                key, value = stripped.split("=", 1)
                props[key] = value
            elif stripped and not is_active:
                is_active = stripped
        active = (props.get("ActiveState") or is_active or "unknown").lower()
        sub = (props.get("SubState") or active).lower()
        states[current_unit] = {
            "active": active,
            "sub": sub,
            "evidence": " | ".join(x.strip() for x in current_lines if x.strip()),
        }

    for raw in (evidence.get("service_hotlist", "") or "").splitlines():
        match = re.match(r"^=====\s+([^=]+?)\s+=====$", raw.strip())
        if match:
            save_hotlist_block()
            current_unit = match.group(1).strip()
            current_lines = []
        elif current_unit:
            current_lines.append(raw)
    save_hotlist_block()

    for raw in (evidence.get("failed_units", "") or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("ERROR:") or " loaded failed failed " not in f" {line} ":
            continue
        unit = line.split()[0]
        if not re.search(r"\.(service|timer|mount|socket)$", unit):
            continue
        observations.append(_observation(
            "service", unit, unit, "failed", numeric_value=1,
            kind="state", unit="boolean", issue=True, evidence=line,
        ))
        states[unit] = {
            "active": "failed",
            "sub": "failed",
            "evidence": line,
        }

    for unit, state in states.items():
        active = state["active"]
        sub = state["sub"]
        observations.append(_observation(
            "service", unit, unit, "state", text_value=f"{active}/{sub}",
            kind="state", issue=active == "failed" or sub == "failed",
            evidence=state["evidence"],
        ))
        primary = _related_service_name(unit)
        if primary:
            observations.extend([
                _observation(
                    "service", unit, unit, "role", kind="identity",
                    text_value="helper", evidence=f"related_service={primary}",
                ),
                _observation(
                    "service", unit, unit, "primary_service", kind="identity",
                    text_value=primary, evidence=f"related_service={primary}",
                ),
            ])
    return observations


def _mount_observations(text):
    observations = []
    for raw in (text or "").splitlines():
        values = _pairs(raw)
        target = values.get("TARGET", "")
        if not target:
            continue
        source = values.get("SOURCE", "")
        fstype = values.get("FSTYPE", "")
        options = values.get("OPTIONS", "")
        signature = f"{source}|{fstype}|{options}"
        observations.extend([
            _observation("mount", target, target, "present", numeric_value=1,
                         kind="state", unit="boolean", evidence=raw),
            _observation("mount", target, target, "signature", kind="identity",
                         text_value=signature, evidence=raw),
        ])
    return observations


def _io_process_observations(text):
    aggregated = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line.startswith("Average:"):
            continue
        if "Command" in line or "UID" in line:
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            read_rate = float(parts[3])
            write_rate = float(parts[4])
        except (TypeError, ValueError):
            continue
        command = " ".join(parts[7:]).strip()
        total_rate = read_rate + write_rate
        if not command or total_rate <= 0:
            continue
        key = command.lower()
        item = aggregated.setdefault(key, {
            "command": command,
            "read_rate": 0.0,
            "write_rate": 0.0,
            "evidence": [],
        })
        item["read_rate"] += read_rate
        item["write_rate"] += write_rate
        item["evidence"].append(line)

    observations = []
    ranked = sorted(
        aggregated.values(),
        key=lambda item: item["read_rate"] + item["write_rate"],
        reverse=True,
    )
    for item in ranked[:20]:
        total_rate = item["read_rate"] + item["write_rate"]
        observations.append(_observation(
            "performance",
            f"io-process:{item['command'].lower()}",
            item["command"],
            "disk_io_kb_s",
            kind="activity",
            numeric_value=round(total_rate, 2),
            text_value=(
                f"read={item['read_rate']:.2f}|"
                f"write={item['write_rate']:.2f}"
            ),
            unit="kB/s",
            issue=False,
            evidence="\n".join(item["evidence"]),
        ))
    return observations


def _system_observations(evidence):
    observations = []
    boot_id = (evidence.get("boot_id", "") or "").strip()
    if boot_id and not boot_id.startswith("ERROR:"):
        observations.append(_observation(
            "system", "host", "ZimaOS host", "boot_id",
            kind="identity", text_value=boot_id, evidence=boot_id,
        ))
    os_values = {}
    for raw in (evidence.get("host_os", "") or "").splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            os_values[key] = value.strip().strip('"')
    os_version = os_values.get("VERSION_ID") or os_values.get("PRETTY_NAME")
    if os_version:
        observations.append(_observation(
            "system", "host", "ZimaOS host", "os_version",
            kind="identity", text_value=os_version, evidence=os_values.get("PRETTY_NAME", os_version),
        ))
    build_date = os_values.get("BUILD_DATE", "").strip()
    if build_date:
        observations.append(_observation(
            "system", "host", "ZimaOS host", "build_date",
            kind="identity", text_value=build_date, evidence=build_date,
        ))
    rauc = evidence.get("rauc", "") or ""
    booted_match = re.search(
        r"^Booted from:\s*(.+?)\s*$", rauc, re.MULTILINE
    )
    if booted_match:
        booted_slot = booted_match.group(1).strip()
        observations.append(_observation(
            "system", "host", "ZimaOS host", "rauc_booted_slot",
            kind="identity", text_value=booted_slot,
            evidence=booted_match.group(0).strip(),
        ))
    kernel = (evidence.get("kernel", "") or "").strip()
    if kernel and not kernel.startswith("ERROR:"):
        observations.append(_observation(
            "system", "host", "ZimaOS host", "kernel",
            kind="identity", text_value=kernel, evidence=kernel,
        ))

    mem = {}
    for raw in (evidence.get("memory", "") or "").splitlines():
        match = re.match(r"^(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+(\d+)", raw.strip())
        if match:
            mem[match.group(1)] = int(match.group(2))
    if mem.get("MemTotal"):
        used = max(mem["MemTotal"] - mem.get("MemAvailable", 0), 0)
        pct = round(used * 100 / mem["MemTotal"], 1)
        observations.append(_observation(
            "performance", "host", "ZimaOS host", "memory_used_percent",
            kind="gauge", numeric_value=pct, unit="percent", issue=pct >= 90,
            evidence=f"MemTotal={mem['MemTotal']}kB MemAvailable={mem.get('MemAvailable', 0)}kB",
        ))
    if mem.get("SwapTotal"):
        used = max(mem["SwapTotal"] - mem.get("SwapFree", 0), 0)
        pct = round(used * 100 / mem["SwapTotal"], 1)
        observations.append(_observation(
            "performance", "host", "ZimaOS host", "swap_used_percent",
            kind="gauge", numeric_value=pct, unit="percent", issue=pct >= 75,
            evidence=f"SwapTotal={mem['SwapTotal']}kB SwapFree={mem.get('SwapFree', 0)}kB",
        ))

    cpu_match = re.search(r"CPU_USAGE_PERCENT=([\d.]+)", evidence.get("cpu_usage", "") or "")
    if cpu_match:
        value = float(cpu_match.group(1))
        observations.append(_observation(
            "performance", "host", "ZimaOS host", "cpu_used_percent",
            kind="gauge", numeric_value=value, unit="percent", issue=value >= 95,
            evidence=cpu_match.group(0),
        ))

    temperatures = []
    for raw in ((evidence.get("thermal_zones", "") or "") + "\n" +
                (evidence.get("sensors", "") or "")).splitlines():
        current_reading = raw.split("(", 1)[0]
        match = re.search(
            r"(?<!\d)(-?\d+(?:\.\d+)?)\s*°?C\b",
            current_reading,
            re.I,
        )
        if match:
            value = float(match.group(1))
            if -20 <= value <= 150:
                temperatures.append((value, raw.strip()))
    if temperatures:
        value, raw = max(temperatures, key=lambda x: x[0])
        observations.append(_observation(
            "performance", "host", "ZimaOS host", "max_temperature",
            kind="gauge", numeric_value=value, unit="C", issue=value >= 85,
            evidence=raw,
        ))
    return observations


def _path_observations(text):
    observations = []
    for raw in (text or "").splitlines():
        parts = raw.strip().split("|")
        if len(parts) < 2:
            continue
        path = parts[0].strip()
        if not path.startswith("/"):
            continue
        values = {}
        for item in parts[1:]:
            if "=" in item:
                key, value = item.split("=", 1)
                values[key] = value
        present = values.get("present") == "1"
        observations.append(_observation(
            "path", path, path, "present",
            kind="state", numeric_value=1 if present else 0,
            unit="boolean", issue=not present, evidence=raw,
        ))
        if present:
            signature = "|".join([
                f"type={values.get('type', 'unknown')}",
                f"target={values.get('target', '')}",
                f"mode={values.get('mode', 'unknown')}",
                f"owner={values.get('owner', 'unknown')}",
            ])
            observations.append(_observation(
                "path", path, path, "signature",
                kind="identity", text_value=signature, evidence=raw,
            ))
    return observations


def _security_observations(evidence):
    observations = []

    zfw_status = (evidence.get("zfw_status", "") or "").strip().splitlines()
    zfw_state = zfw_status[0].strip() if zfw_status else "unknown"
    observations.append(_observation(
        "security", "zfw", "ZFW firewall", "state",
        kind="state", text_value=zfw_state,
        issue=zfw_state != "active", evidence=zfw_state,
    ))

    zfw_files = evidence.get("zfw_files", "") or ""
    expected_files = (
        "/var/lib/extensions/zfw.raw",
        "/DATA/zfw/zfw",
        "/DATA/zfw/rules.json",
    )
    for expected_path in expected_files:
        matching = next(
            (
                raw.strip() for raw in zfw_files.splitlines()
                if expected_path in raw
            ),
            "",
        )
        present = bool(matching)
        observations.append(_observation(
            "security", f"zfw-file:{expected_path}", expected_path,
            "present", kind="state",
            numeric_value=1 if present else 0,
            unit="boolean",
            issue=zfw_state == "active" and not present,
            evidence=matching or f"Missing: {expected_path}",
        ))

    chains = sorted(
        raw.strip()
        for raw in (evidence.get("zfw_chains", "") or "").splitlines()
        if raw.strip()
    )
    observations.append(_observation(
        "security", "zfw", "ZFW firewall", "chain_signature",
        kind="identity", text_value=" | ".join(chains) or "<none>",
        evidence="\n".join(chains),
    ))

    audit_text = evidence.get("auditd", "") or ""
    audit_lines = [raw.strip() for raw in audit_text.splitlines() if raw.strip()]
    audit_state = audit_lines[0] if audit_lines else "unknown"
    observations.append(_observation(
        "security", "auditd", "auditd", "state",
        kind="state", text_value=audit_state,
        issue=audit_state != "active", evidence=audit_state,
    ))

    audit_signature = []
    in_paths = False
    for raw in audit_text.splitlines():
        line = raw.strip()
        if line == "---AUDIT_PATHS---":
            in_paths = True
            continue
        if not in_paths or "/var/log/audit" not in line:
            continue
        parts = line.split()
        if len(parts) >= 4:
            audit_signature.append(
                f"{parts[-1]}:{parts[0]}:{parts[2]}:{parts[3]}"
            )
    observations.append(_observation(
        "security", "auditd", "auditd", "path_signature",
        kind="identity",
        text_value=" | ".join(sorted(audit_signature)) or "<not captured>",
        evidence="\n".join(audit_signature),
    ))

    for raw in (evidence.get("docker_security", "") or "").splitlines():
        parts = raw.strip().split("|")
        if len(parts) < 2:
            continue
        name = parts[0].lstrip("/").strip()
        if not name:
            continue
        values = {}
        for item in parts[1:]:
            if "=" in item:
                key, value = item.split("=", 1)
                values[key] = value
        privileged = values.get("Privileged", "").lower() == "true"
        socket_access = bool(values.get("DockerSock", "").strip())
        posture = "|".join([
            f"User={values.get('User', '')}",
            f"PidMode={values.get('PidMode', '')}",
            f"SecurityOpt={values.get('SecurityOpt', '')}",
            f"CapAdd={values.get('CapAdd', '')}",
        ])
        observations.extend([
            _observation(
                "security", f"container:{name}", name, "docker_posture",
                kind="identity", text_value=posture, evidence=raw,
            ),
            _observation(
                "security", f"container:{name}", name, "privileged",
                kind="state", numeric_value=1 if privileged else 0,
                unit="boolean", issue=False, evidence=raw,
            ),
            _observation(
                "security", f"container:{name}", name, "docker_socket",
                kind="state", numeric_value=1 if socket_access else 0,
                unit="boolean", issue=False, evidence=raw,
            ),
        ])

    return observations


def _port_observations(text):
    observations = []
    for raw in (text or "").splitlines():
        if not raw.strip() or raw.startswith("HOST_LAN_IP="):
            continue
        parts = raw.strip().split("|")
        if len(parts) < 4:
            continue
        name, port = parts[0], parts[1]
        values = {}
        for item in parts[2:]:
            if "=" in item:
                key, value = item.split("=", 1)
                values[key] = value
        lan = values.get("lan", "unknown")
        local = values.get("localhost", "unknown")
        observations.append(_observation(
            "network", f"{name}:{port}", f"{name} port {port}", "reachability",
            kind="state", text_value=f"localhost={local}|lan={lan}",
            evidence=raw,
        ))
    return observations


def collect_observations(evidence):
    evidence = evidence if isinstance(evidence, dict) else {}
    identities = _disk_identities(evidence.get("disk_identity", ""))
    observations = []
    observations.extend(_smart_observations(evidence, identities))
    observations.extend(_nvme_observations(evidence, identities))
    observations.extend(_container_observations(evidence.get("docker_states", "")))
    observations.extend(_service_observations(evidence))
    observations.extend(_mount_observations(evidence.get("mounts", "")))
    observations.extend(_path_observations(evidence.get("path_state", "")))
    observations.extend(_io_process_observations(evidence.get("io_top", "")))
    observations.extend(_system_observations(evidence))
    observations.extend(_security_observations(evidence))
    observations.extend(_port_observations(evidence.get("port_reachability", "")))
    return observations


def _init_db(con):
    con.executescript("""
        CREATE TABLE IF NOT EXISTS health_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            app_version TEXT NOT NULL,
            observation_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS health_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            entity_key TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            kind TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT NOT NULL DEFAULT '',
            issue INTEGER NOT NULL DEFAULT 0,
            evidence TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(scan_id) REFERENCES health_scans(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS health_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            entity_key TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            classification TEXT NOT NULL,
            previous_numeric REAL,
            current_numeric REAL,
            previous_text TEXT,
            current_text TEXT,
            delta REAL,
            occurrence_count INTEGER NOT NULL DEFAULT 1,
            message TEXT NOT NULL,
            FOREIGN KEY(scan_id) REFERENCES health_scans(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_health_observation_signal
            ON health_observations(category, entity_key, metric, scan_id DESC);
        CREATE INDEX IF NOT EXISTS idx_health_event_scan
            ON health_events(scan_id, classification, category);
    """)


def _previous(con, obs):
    return con.execute("""
        SELECT numeric_value, text_value, issue, kind
        FROM health_observations
        WHERE category = ? AND entity_key = ? AND metric = ?
        ORDER BY scan_id DESC
        LIMIT 1
    """, (obs["category"], obs["entity_key"], obs["metric"])).fetchone()


def _occurrences(con, obs):
    row = con.execute("""
        SELECT COUNT(*)
        FROM health_observations
        WHERE category = ? AND entity_key = ? AND metric = ? AND issue = 1
    """, (obs["category"], obs["entity_key"], obs["metric"])).fetchone()
    return int(row[0]) + (1 if obs["issue"] else 0)


def _classify(obs, previous):
    if previous is None:
        return "historical_baseline" if obs["issue"] else "baseline", None

    if (obs["category"] == "performance" and
            obs["metric"] == "disk_io_kb_s"):
        return "stable", None

    prev_numeric, prev_text, prev_issue, _ = previous
    current_issue = bool(obs["issue"])
    previous_issue = bool(prev_issue)
    delta = None

    if obs["kind"] == "counter" and obs["numeric_value"] is not None and prev_numeric is not None:
        delta = float(obs["numeric_value"]) - float(prev_numeric)
        if delta > 0:
            return "worsening", delta
        if delta < 0:
            return "counter_reset", delta
        if float(obs["numeric_value"]) > 0:
            return "historical_stable", 0.0
        return "stable", 0.0

    if current_issue and previous_issue:
        return "persistent", delta
    if current_issue and not previous_issue:
        return "new_issue", delta
    if not current_issue and previous_issue:
        return "recovered", delta

    if obs["numeric_value"] is not None and prev_numeric is not None:
        delta = float(obs["numeric_value"]) - float(prev_numeric)
        return ("stable" if delta == 0 else "changed"), delta
    if obs["text_value"] == prev_text:
        return "stable", delta
    return "changed", delta


def _message(obs, classification, previous, delta):
    label = f"{obs['entity_name']} {obs['metric'].replace('_', ' ')}"
    current = obs["numeric_value"] if obs["numeric_value"] is not None else obs["text_value"]
    previous_value = None
    if previous is not None:
        previous_value = previous[0] if previous[0] is not None else previous[1]
    if classification == "worsening":
        return f"{label} increased from {previous_value} to {current}."
    if classification == "historical_stable":
        return f"{label} remains at {current}. No increase detected."
    if classification == "historical_baseline":
        return f"{label} is {current}. Saved as the first local baseline."
    if classification == "new_issue":
        return f"{label} changed from {previous_value} to {current}. New issue detected."
    if classification == "persistent":
        return f"{label} remains in an issue state: {current}."
    if classification == "recovered":
        return f"{label} recovered from {previous_value} to {current}."
    if classification == "counter_reset":
        return f"{label} decreased from {previous_value} to {current}; the device or counter may have reset."
    if classification == "changed":
        return f"{label} changed from {previous_value} to {current}."
    if classification == "baseline":
        return f"{label} saved as baseline: {current}."
    return f"{label} is unchanged at {current}."


def _add_missing_states(con, observations):
    current = {(x["category"], x["entity_key"], x["metric"]) for x in observations}
    rows = con.execute("""
        SELECT o.category, o.entity_key, o.entity_name, o.metric
        FROM health_observations o
        JOIN (
            SELECT category, entity_key, metric, MAX(scan_id) AS max_scan
            FROM health_observations
            WHERE (category = 'service' AND metric = 'failed')
               OR (category = 'mount' AND metric = 'present')
            GROUP BY category, entity_key, metric
        ) latest
          ON latest.category = o.category
         AND latest.entity_key = o.entity_key
         AND latest.metric = o.metric
         AND latest.max_scan = o.scan_id
        WHERE o.numeric_value = 1
    """).fetchall()
    for category, entity_key, entity_name, metric in rows:
        key = (category, entity_key, metric)
        if key not in current:
            observations.append(_observation(
                category, entity_key, entity_name, metric,
                numeric_value=0, kind="state", unit="boolean", issue=False,
                evidence="Not present in the current failed-service or mount list.",
            ))


def record_health_scan(evidence, app_version, db_path=TREND_DB_PATH, created_at=None):
    observations = collect_observations(evidence)
    timestamp = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(db_path, timeout=10) as con:
        _init_db(con)
        _add_missing_states(con, observations)
        cursor = con.execute(
            "INSERT INTO health_scans (created_at, app_version, observation_count) VALUES (?, ?, 0)",
            (timestamp, app_version),
        )
        scan_id = cursor.lastrowid
        classifications = {}
        for obs in observations:
            previous = _previous(con, obs)
            classification, delta = _classify(obs, previous)
            occurrences = _occurrences(con, obs)
            message = _message(obs, classification, previous, delta)
            con.execute("""
                INSERT INTO health_observations (
                    scan_id, category, entity_key, entity_name, metric, kind,
                    numeric_value, text_value, unit, issue, evidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id, obs["category"], obs["entity_key"], obs["entity_name"],
                obs["metric"], obs["kind"], obs["numeric_value"], obs["text_value"],
                obs["unit"], obs["issue"], obs["evidence"],
            ))
            con.execute("""
                INSERT INTO health_events (
                    scan_id, category, entity_key, entity_name, metric, classification,
                    previous_numeric, current_numeric, previous_text, current_text,
                    delta, occurrence_count, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id, obs["category"], obs["entity_key"], obs["entity_name"],
                obs["metric"], classification,
                previous[0] if previous else None, obs["numeric_value"],
                previous[1] if previous else None, obs["text_value"],
                delta, occurrences, message,
            ))
            classifications[classification] = classifications.get(classification, 0) + 1
        con.execute(
            "UPDATE health_scans SET observation_count = ? WHERE id = ?",
            (len(observations), scan_id),
        )
        con.commit()

    smart_positive = sum(
        1 for x in observations
        if x["category"] == "smart" and x["metric"] in COUNTER_METRICS
        and x["numeric_value"] is not None and x["numeric_value"] > 0
    )
    nvme_critical = sum(
        1 for x in observations
        if x["category"] == "nvme" and x["metric"] in {"critical_warning", "media_errors"}
        and x["numeric_value"] is not None and x["numeric_value"] > 0
    )
    return {
        "ok": True,
        "scan_id": scan_id,
        "observation_count": len(observations),
        "classifications": classifications,
        "smart_positive_signals": smart_positive,
        "nvme_critical_signals": nvme_critical,
    }


def latest_events(db_path=TREND_DB_PATH, limit=100):
    if not db_path:
        return []
    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        row = con.execute("SELECT MAX(id) FROM health_scans").fetchone()
        if not row or row[0] is None:
            return []
        return [dict(x) for x in con.execute("""
            SELECT category, entity_key, entity_name, metric, classification,
                   previous_numeric, current_numeric, previous_text, current_text,
                   delta, occurrence_count, message
            FROM health_events
            WHERE scan_id = ?
            ORDER BY
              CASE classification
                WHEN 'worsening' THEN 1 WHEN 'new_issue' THEN 2
                WHEN 'persistent' THEN 3 WHEN 'recovered' THEN 4
                WHEN 'historical_stable' THEN 5 ELSE 6
              END,
              category, entity_name, metric
            LIMIT ?
        """, (row[0], limit))]


def latest_scan(db_path=TREND_DB_PATH):
    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        row = con.execute("""
            SELECT id, created_at, app_version, observation_count
            FROM health_scans
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()
        return dict(row) if row else None


def recent_scans(db_path=TREND_DB_PATH, limit=8):
    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        return [dict(x) for x in con.execute("""
            SELECT id, created_at, app_version, observation_count
            FROM health_scans
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))]


def entity_history(category, entity_key, metric, db_path=TREND_DB_PATH, limit=10):
    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        rows = con.execute("""
            SELECT o.scan_id, s.created_at, o.entity_name, o.numeric_value,
                   o.text_value, o.issue, o.evidence
            FROM health_observations o
            JOIN health_scans s ON s.id = o.scan_id
            WHERE o.category = ? AND o.entity_key = ? AND o.metric = ?
            ORDER BY o.scan_id DESC
            LIMIT ?
        """, (category, entity_key, metric, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]


def _container_window_status(states):
    issue_states = {"exited", "restarting", "dead", "paused", "created"}
    lowered = [(state or "unknown").lower() for state in states]
    issues = [state in issue_states for state in lowered]
    issue_count = sum(issues)
    running_count = sum(state == "running" for state in lowered)
    current = lowered[-1] if lowered else "unknown"
    trailing_issues = 0
    for is_issue in reversed(issues):
        if not is_issue:
            break
        trailing_issues += 1

    if not lowered:
        classification = "no_history"
        message = "No container history is available."
    elif issue_count == 0 and running_count == len(lowered):
        classification = "stable"
        message = f"Running in all {len(lowered)} recorded reports."
    elif issue_count >= 3 and issue_count * 2 >= len(lowered):
        classification = "persistent_fault"
        if current == "running":
            message = (
                "Intermittent persistent container fault: running during this scan, "
                f"but issue states occurred in {issue_count} of {len(lowered)} reports."
            )
        else:
            message = (
                f"Persistent container fault: currently {current}, with issue states "
                f"in {issue_count} of {len(lowered)} reports."
            )
    elif current == "running" and issue_count == 1 and running_count >= 2:
        classification = "temporary_interruption"
        message = "Temporary interruption detected; the container normally remains running."
    elif current == "running" and issue_count:
        classification = "recovered_interruption"
        message = (
            f"Recovered and currently running after {issue_count} interruption(s) "
            f"in {len(lowered)} reports."
        )
    elif current in issue_states and trailing_issues >= 3:
        classification = "persistent_fault"
        message = (
            f"Persistent container fault: {current} in {trailing_issues} "
            "consecutive reports."
        )
    elif current in issue_states and any(not value for value in issues[:-1]):
        classification = "new_interruption"
        message = (
            f"Current interruption detected ({current}); previous reports include "
            "a running state."
        )
    elif current in issue_states and len(lowered) >= 2:
        classification = "persistent_fault"
        message = f"Persistent container fault: {current} across the available reports."
    else:
        classification = "mixed_history"
        message = "Mixed container states detected; more reports are needed for classification."

    return {
        "classification": classification,
        "message": message,
        "current_state": current,
        "issue_count": issue_count,
        "running_count": running_count,
        "trailing_issue_count": trailing_issues,
    }


def container_state_histories(db_path=TREND_DB_PATH, limit=10):
    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        rows = con.execute("""
            WITH ranked AS (
                SELECT o.scan_id, s.created_at, o.entity_key, o.entity_name,
                       o.text_value,
                       ROW_NUMBER() OVER (
                           PARTITION BY o.entity_key ORDER BY o.scan_id DESC
                       ) AS position
                FROM health_observations o
                JOIN health_scans s ON s.id = o.scan_id
                WHERE o.category = 'container' AND o.metric = 'state'
            )
            SELECT scan_id, created_at, entity_key, entity_name, text_value
            FROM ranked
            WHERE position <= ?
            ORDER BY entity_name, scan_id
        """, (limit,)).fetchall()

    grouped = {}
    for row in rows:
        item = dict(row)
        entry = grouped.setdefault(item["entity_key"], {
            "entity_key": item["entity_key"],
            "entity_name": item["entity_name"],
            "reports": [],
        })
        entry["reports"].append({
            "scan_id": item["scan_id"],
            "created_at": item["created_at"],
            "state": item["text_value"] or "unknown",
        })

    results = []
    for entry in grouped.values():
        states = [item["state"] for item in entry["reports"]]
        entry["states"] = states
        entry.update(_container_window_status(states))
        results.append(entry)

    priority = {
        "persistent_fault": 0,
        "new_interruption": 1,
        "temporary_interruption": 2,
        "recovered_interruption": 3,
        "mixed_history": 4,
        "stable": 5,
        "no_history": 6,
    }
    return sorted(
        results,
        key=lambda item: (
            priority.get(item["classification"], 99),
            item["entity_name"].lower(),
        ),
    )


def _io_window_status(rates):
    observed = [float(value or 0) > 0 for value in rates]
    observed_count = sum(observed)
    current_rate = float(rates[-1] or 0) if rates else 0.0
    trailing = 0
    for value in reversed(observed):
        if not value:
            break
        trailing += 1

    if not rates or observed_count == 0:
        classification = "no_history"
        message = "No measurable disk I/O was captured."
    elif observed[-1] and observed_count == 1:
        classification = "observed_this_report_only"
        message = "Observed during this report only; likely temporary activity."
    elif observed[-1] and trailing >= 3:
        classification = "persistent_activity"
        message = (
            f"Observed in {trailing} consecutive reports; "
            "persistent disk activity detected."
        )
    elif observed[-1]:
        classification = "recurring_activity"
        message = (
            f"Observed in {observed_count} of {len(rates)} reports; "
            "activity is recurring but not continuous."
        )
    elif observed_count == 1:
        classification = "temporary_activity"
        message = "Observed once previously and not in the current report."
    else:
        classification = "no_longer_observed"
        message = (
            f"Observed in {observed_count} earlier reports but not in "
            "the current report."
        )

    return {
        "classification": classification,
        "message": message,
        "observed_count": observed_count,
        "current_rate": current_rate,
        "trailing_observed_count": trailing,
    }


def disk_io_process_histories(db_path=TREND_DB_PATH, limit=10):
    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        scans = list(con.execute("""
            SELECT id, created_at
            FROM health_scans
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)))
        scans.reverse()
        if not scans:
            return []

        scan_ids = [row["id"] for row in scans]
        placeholders = ",".join("?" for _ in scan_ids)
        rows = con.execute(f"""
            SELECT scan_id, entity_key, entity_name, numeric_value,
                   text_value, evidence
            FROM health_observations
            WHERE category = 'performance'
              AND metric = 'disk_io_kb_s'
              AND scan_id IN ({placeholders})
            ORDER BY entity_name, scan_id
        """, scan_ids).fetchall()

    grouped = {}
    for row in rows:
        item = dict(row)
        entry = grouped.setdefault(item["entity_key"], {
            "entity_key": item["entity_key"],
            "entity_name": item["entity_name"],
            "observations": {},
        })
        entry["observations"][item["scan_id"]] = item

    results = []
    for entry in grouped.values():
        reports = []
        rates = []
        for scan in scans:
            observation = entry["observations"].get(scan["id"])
            rate = (
                float(observation["numeric_value"] or 0)
                if observation else 0.0
            )
            rates.append(rate)
            reports.append({
                "scan_id": scan["id"],
                "created_at": scan["created_at"],
                "observed": bool(observation),
                "rate_kb_s": rate,
            })
        entry.pop("observations")
        entry["reports"] = reports
        entry["rates"] = rates
        entry.update(_io_window_status(rates))
        results.append(entry)

    priority = {
        "persistent_activity": 0,
        "recurring_activity": 1,
        "observed_this_report_only": 2,
        "temporary_activity": 3,
        "no_longer_observed": 4,
        "no_history": 5,
    }
    return sorted(
        results,
        key=lambda item: (
            priority.get(item["classification"], 99),
            -item["current_rate"],
            item["entity_name"].lower(),
        ),
    )


def _drift_value(row):
    if row["numeric_value"] is not None:
        value = float(row["numeric_value"])
        return int(value) if value.is_integer() else value
    return row["text_value"]


def _drift_status(category, entity_key, metric, previous, current):
    if category == "path" and metric == "present":
        if previous == 1 and current == 0:
            return "path_missing", "attention"
        if previous == 0 and current == 1:
            return "path_restored", "recovery"
    if category == "path" and metric == "signature":
        return "path_signature_changed", "attention"

    if category == "mount" and metric == "present":
        if previous == 1 and current == 0:
            return "mount_missing", "attention"
        if previous == 0 and current == 1:
            return "mount_restored", "recovery"
    if category == "mount" and metric == "signature":
        return "mount_signature_changed", "attention"

    if category == "network" and metric == "reachability":
        previous_lan = "lan=open" in str(previous or "")
        current_lan = "lan=open" in str(current or "")
        if previous is None and current is not None:
            return (
                "new_lan_exposure" if current_lan else "port_added",
                "attention" if current_lan else "information",
            )
        if previous is not None and current is None:
            return "port_removed", "information"
        if not previous_lan and current_lan:
            return "new_lan_exposure", "attention"
        if previous_lan and not current_lan:
            return "lan_exposure_restricted", "recovery"
        return "reachability_changed", "information"

    if category == "security":
        if entity_key == "zfw" and metric == "state":
            if previous == "active" and current != "active":
                return "firewall_not_active", "attention"
            if previous != "active" and current == "active":
                return "firewall_restored", "recovery"
        if entity_key == "auditd" and metric == "state":
            if previous == "active" and current != "active":
                return "auditd_not_active", "attention"
            if previous != "active" and current == "active":
                return "auditd_restored", "recovery"
        if metric == "present":
            if previous == 1 and current == 0:
                return "security_file_missing", "attention"
            if previous == 0 and current == 1:
                return "security_file_restored", "recovery"
        if metric == "privileged":
            if previous == 0 and current == 1:
                return "container_privilege_enabled", "attention"
            if previous == 1 and current == 0:
                return "container_privilege_removed", "recovery"
        if metric == "docker_socket":
            if previous == 0 and current == 1:
                return "docker_socket_added", "attention"
            if previous == 1 and current == 0:
                return "docker_socket_removed", "recovery"
        if metric == "docker_posture":
            if previous is None:
                return "container_security_baseline_added", "information"
            if current is None:
                return "container_security_baseline_removed", "information"
            return "container_security_posture_changed", "attention"
        if metric in ("chain_signature", "path_signature"):
            return "security_signature_changed", "attention"

    return "configuration_changed", "information"


def configuration_drift_history(db_path=TREND_DB_PATH, limit=10):
    categories = ("path", "mount", "network", "security")

    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        scans = list(con.execute("""
            SELECT id, created_at
            FROM health_scans
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)))
        scans.reverse()
        if not scans:
            return {"drifts": [], "current": {}}

        scan_ids = [row["id"] for row in scans]
        scan_placeholders = ",".join("?" for _ in scan_ids)
        category_placeholders = ",".join("?" for _ in categories)
        rows = con.execute(f"""
            SELECT scan_id, category, entity_key, entity_name, metric,
                   numeric_value, text_value
            FROM health_observations
            WHERE scan_id IN ({scan_placeholders})
              AND category IN ({category_placeholders})
            ORDER BY scan_id, category, entity_name, metric
        """, tuple(scan_ids) + categories).fetchall()

    maps = {scan_id: {} for scan_id in scan_ids}
    names = {}
    for row in rows:
        item = dict(row)
        key = (
            item["category"],
            item["entity_key"],
            item["metric"],
        )
        maps[item["scan_id"]][key] = _drift_value(item)
        names[key] = item["entity_name"]

    drifts = []
    for previous_scan, current_scan in zip(scans, scans[1:]):
        previous_map = maps[previous_scan["id"]]
        current_map = maps[current_scan["id"]]
        previous_categories = {key[0] for key in previous_map}
        current_categories = {key[0] for key in current_map}

        for category in previous_categories & current_categories:
            keys = {
                key for key in set(previous_map) | set(current_map)
                if key[0] == category
            }
            for key in keys:
                _, entity_key, metric = key
                previous = previous_map.get(key)
                current = current_map.get(key)
                if previous == current:
                    continue

                if category in ("path", "mount") and metric == "signature":
                    presence_key = (category, entity_key, "present")
                    if (
                        previous_map.get(presence_key) != 1
                        or current_map.get(presence_key) != 1
                    ):
                        continue

                if (
                    category == "security"
                    and entity_key.startswith("container:")
                    and metric in ("privileged", "docker_socket")
                    and (previous is None or current is None)
                ):
                    continue

                classification, severity = _drift_status(
                    category, entity_key, metric, previous, current
                )
                old = str(previous)[:180] if previous is not None else "not recorded"
                new = str(current)[:180] if current is not None else "not recorded"
                drifts.append({
                    "from_scan": previous_scan["id"],
                    "to_scan": current_scan["id"],
                    "created_at": current_scan["created_at"],
                    "category": category,
                    "entity_key": entity_key,
                    "entity_name": names.get(key, entity_key),
                    "metric": metric,
                    "previous": previous,
                    "current": current,
                    "classification": classification,
                    "severity": severity,
                    "message": (
                        f"{names.get(key, entity_key)} {metric.replace('_', ' ')} "
                        f"changed from {old} to {new}."
                    ),
                })

    severity_order = {
        "attention": 0,
        "recovery": 1,
        "information": 2,
    }
    drifts.sort(
        key=lambda item: (
            -item["to_scan"],
            severity_order.get(item["severity"], 9),
            item["category"],
            item["entity_name"].lower(),
            item["metric"],
        )
    )

    latest = maps[scan_ids[-1]]
    current = {
        "paths_tracked": sum(
            1 for key, value in latest.items()
            if key[0] == "path" and key[2] == "present"
        ),
        "paths_missing": sum(
            1 for key, value in latest.items()
            if key[0] == "path" and key[2] == "present" and value == 0
        ),
        "mounts_missing": sum(
            1 for key, value in latest.items()
            if key[0] == "mount" and key[2] == "present" and value == 0
        ),
        "lan_open_ports": sum(
            1 for key, value in latest.items()
            if key[0] == "network"
            and key[2] == "reachability"
            and "lan=open" in str(value or "")
        ),
        "privileged_containers": sum(
            1 for key, value in latest.items()
            if key[0] == "security"
            and key[2] == "privileged"
            and value == 1
        ),
        "docker_socket_containers": sum(
            1 for key, value in latest.items()
            if key[0] == "security"
            and key[2] == "docker_socket"
            and value == 1
        ),
        "zfw_state": latest.get(("security", "zfw", "state"), "unknown"),
        "auditd_state": latest.get(
            ("security", "auditd", "state"), "unknown"
        ),
    }

    return {
        "drifts": drifts,
        "current": current,
        "scan_count": len(scans),
    }


def system_update_history(db_path=TREND_DB_PATH, limit=10):
    tracked_metrics = (
        "os_version", "build_date", "kernel", "rauc_booted_slot"
    )
    labels = {
        "os_version": "ZimaOS version",
        "build_date": "OS build date",
        "kernel": "kernel",
        "rauc_booted_slot": "RAUC booted slot",
    }

    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)

        placeholders = ",".join("?" for _ in tracked_metrics)
        current_rows = con.execute(f"""
            WITH ranked AS (
                SELECT metric, text_value, scan_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY metric ORDER BY scan_id DESC
                       ) AS position
                FROM health_observations
                WHERE category = 'system'
                  AND entity_key = 'host'
                  AND metric IN ({placeholders})
            )
            SELECT metric, text_value, scan_id
            FROM ranked
            WHERE position = 1
        """, tracked_metrics).fetchall()

        transition_rows = con.execute(f"""
            SELECT e.scan_id, s.created_at, e.metric,
                   e.previous_text, e.current_text, e.message
            FROM health_events e
            JOIN health_scans s ON s.id = e.scan_id
            WHERE e.category = 'system'
              AND e.entity_key = 'host'
              AND e.metric IN ({placeholders})
              AND e.classification = 'changed'
            ORDER BY e.scan_id DESC, e.metric
        """, tracked_metrics).fetchall()

        grouped = {}
        for row in transition_rows:
            item = dict(row)
            entry = grouped.setdefault(item["scan_id"], {
                "scan_id": item["scan_id"],
                "created_at": item["created_at"],
                "changes": [],
            })
            entry["changes"].append({
                "metric": item["metric"],
                "label": labels.get(item["metric"], item["metric"]),
                "previous": item["previous_text"],
                "current": item["current_text"],
                "message": item["message"],
            })

        transitions = []
        for entry in list(grouped.values())[:limit]:
            next_row = con.execute(
                "SELECT MIN(id) FROM health_scans WHERE id > ?",
                (entry["scan_id"],),
            ).fetchone()
            scan_ids = [entry["scan_id"]]
            if next_row and next_row[0] is not None:
                scan_ids.append(next_row[0])

            event_placeholders = ",".join("?" for _ in scan_ids)
            related_rows = con.execute(f"""
                SELECT scan_id, category, entity_name, metric,
                       classification, message
                FROM health_events
                WHERE scan_id IN ({event_placeholders})
                  AND classification IN (
                      'new_issue', 'worsening', 'recovered'
                  )
                  AND NOT (
                      category = 'system'
                      AND metric IN ({placeholders})
                  )
                ORDER BY scan_id, category, entity_name, metric
            """, tuple(scan_ids) + tracked_metrics).fetchall()

            related = [dict(row) for row in related_rows]
            issues = [
                item for item in related
                if item["classification"] in ("new_issue", "worsening")
            ]
            recoveries = [
                item for item in related
                if item["classification"] == "recovered"
            ]

            if issues:
                classification = "post_update_attention"
                assessment = (
                    f"{len(issues)} new or worsening signal(s) appeared "
                    "in the transition scan or the immediately following scan."
                )
            elif recoveries:
                classification = "post_update_recovery"
                assessment = (
                    "No new or worsening signal was correlated; "
                    f"{len(recoveries)} recovery signal(s) were recorded."
                )
            else:
                classification = "no_regression_detected"
                assessment = (
                    "No new or worsening signal appeared in the transition "
                    "scan or the immediately following scan."
                )

            entry["classification"] = classification
            entry["assessment"] = assessment
            entry["correlated_scan_ids"] = scan_ids
            entry["issues"] = issues
            entry["recoveries"] = recoveries
            entry["causality_note"] = (
                "Temporal correlation only. This does not prove that the "
                "ZimaOS, kernel, build, or slot transition caused the signal."
            )
            transitions.append(entry)

    current = {
        row["metric"]: row["text_value"]
        for row in current_rows
    }
    return {
        "current": current,
        "transitions": transitions,
    }


def _service_window_status(states):
    lowered = [(state or "unknown/unknown").lower() for state in states]
    issues = [
        state.split("/", 1)[0] == "failed" or state.endswith("/failed")
        for state in lowered
    ]
    issue_count = sum(issues)
    current = lowered[-1] if lowered else "unknown/unknown"
    trailing_issues = 0
    for is_issue in reversed(issues):
        if not is_issue:
            break
        trailing_issues += 1

    if not lowered:
        classification = "no_history"
        message = "No boot-aware service history is available."
    elif issue_count == 0:
        classification = "stable"
        message = f"No failed state was recorded across {len(lowered)} distinct boot(s)."
    elif not issues[-1] and issue_count == 1:
        classification = "temporary_interruption"
        message = "A previous boot recorded one failure; the service is not currently failed."
    elif not issues[-1]:
        classification = "recovered_interruption"
        message = (
            f"The service is not currently failed after failures in {issue_count} "
            "previous boot(s)."
        )
    elif trailing_issues >= 2:
        classification = "persistent_fault"
        message = f"Failed across {trailing_issues} consecutive distinct boots."
    elif any(not value for value in issues[:-1]):
        classification = "new_issue"
        message = "Failed in the current boot after a non-failed state in an earlier boot."
    else:
        classification = "current_issue"
        message = "Failed in the current boot; more distinct boots are needed for persistence."

    return {
        "classification": classification,
        "message": message,
        "current_state": current,
        "issue_count": issue_count,
        "trailing_issue_count": trailing_issues,
    }


def service_boot_histories(db_path=TREND_DB_PATH, limit=20):
    with sqlite3.connect(db_path, timeout=5) as con:
        con.row_factory = sqlite3.Row
        _init_db(con)
        rows = con.execute("""
            WITH boot_scans AS (
                SELECT scan_id, text_value AS boot_id
                FROM health_observations
                WHERE category = 'system' AND entity_key = 'host'
                  AND metric = 'boot_id' AND text_value IS NOT NULL
            ),
            recent_boots AS (
                SELECT boot_id, MAX(scan_id) AS last_scan
                FROM boot_scans
                GROUP BY boot_id
                ORDER BY last_scan DESC
                LIMIT ?
            ),
            ranked AS (
                SELECT b.boot_id, rb.last_scan, o.scan_id, o.entity_key,
                       o.entity_name, o.text_value, o.issue, o.evidence,
                       ROW_NUMBER() OVER (
                           PARTITION BY b.boot_id, o.entity_key
                           ORDER BY o.scan_id DESC
                       ) AS position
                FROM boot_scans b
                JOIN recent_boots rb ON rb.boot_id = b.boot_id
                JOIN health_observations o ON o.scan_id = b.scan_id
                WHERE o.category = 'service' AND o.metric = 'state'
            )
            SELECT boot_id, last_scan, scan_id, entity_key, entity_name,
                   text_value, issue, evidence
            FROM ranked
            WHERE position = 1
            ORDER BY entity_name, last_scan
        """, (limit,)).fetchall()

    grouped = {}
    for row in rows:
        item = dict(row)
        entry = grouped.setdefault(item["entity_key"], {
            "entity_key": item["entity_key"],
            "entity_name": item["entity_name"],
            "boots": [],
        })
        entry["boots"].append({
            "boot_id": item["boot_id"],
            "scan_id": item["scan_id"],
            "state": item["text_value"] or "unknown/unknown",
            "issue": bool(item["issue"]),
            "evidence": item["evidence"],
        })

    results = []
    for entry in grouped.values():
        states = [item["state"] for item in entry["boots"]]
        entry["states"] = states
        entry.update(_service_window_status(states))
        results.append(entry)

    priority = {
        "persistent_fault": 0,
        "new_issue": 1,
        "current_issue": 2,
        "temporary_interruption": 3,
        "recovered_interruption": 4,
        "stable": 5,
        "no_history": 6,
    }
    return sorted(
        results,
        key=lambda item: (
            priority.get(item["classification"], 99),
            item["entity_name"].lower(),
        ),
    )


def helper_service_correlations(db_path=TREND_DB_PATH, limit=20):
    histories = service_boot_histories(db_path, limit)
    by_name = {item["entity_name"]: item for item in histories}
    results = []

    for helper in histories:
        primary_name = _related_service_name(helper["entity_name"])
        if not primary_name:
            continue
        primary = by_name.get(primary_name)
        helper_failed = helper["current_state"].startswith("failed/")
        primary_healthy = bool(
            primary and primary["current_state"].startswith("active/")
        )

        if helper_failed and primary_healthy:
            if helper["classification"] == "persistent_fault":
                classification = "known_historical_helper_issue"
                message = (
                    f"{helper['entity_name']} repeatedly failed across distinct boots, "
                    f"while {primary_name} remains active. Main service remains healthy."
                )
            else:
                classification = "helper_issue_primary_healthy"
                message = (
                    f"{helper['entity_name']} is failed, while {primary_name} remains "
                    "active. More distinct boots are needed before calling it historical."
                )
        elif helper_failed:
            classification = "helper_and_primary_attention"
            message = (
                f"{helper['entity_name']} is failed and {primary_name} is not verified "
                "as active in the same boot-aware history."
            )
        elif helper["issue_count"]:
            classification = "recovered_helper"
            message = f"{helper['entity_name']} previously failed but is not currently failed."
        else:
            classification = "stable_pair"
            message = f"{helper['entity_name']} and {primary_name} show no current helper fault."

        results.append({
            "helper": helper["entity_name"],
            "primary": primary_name,
            "classification": classification,
            "message": message,
            "helper_history": helper,
            "primary_history": primary,
        })

    return sorted(
        results,
        key=lambda item: (
            item["classification"] == "stable_pair",
            item["helper"].lower(),
        ),
    )
