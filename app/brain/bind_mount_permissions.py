import json
import re
import shlex


NON_POSIX_PERMISSION_FILESYSTEMS = {
    "exfat", "vfat", "msdos", "fat", "ntfs", "ntfs3", "fuseblk"
}
WRITE_ACTION_WORDS = {
    "write", "writable", "create", "rename", "delete", "remove", "move"
}


def _run(run_command, command, timeout=12):
    try:
        return str(run_command(command, timeout=timeout) or "").strip()
    except TypeError:
        return str(run_command(command, timeout) or "").strip()
    except Exception as error:
        return f"ERROR: {error}"


def parse_pairs(line):
    try:
        return {
            key: value
            for token in shlex.split(str(line or ""))
            if "=" in token
            for key, value in [token.split("=", 1)]
        }
    except ValueError:
        return {}


def parse_docker_access(text):
    rows = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        mounts = []
        for value in parts[1].split(";"):
            value = value.strip()
            if not value or "->" not in value:
                continue
            try:
                source_dest, rw = value.rsplit(":", 1)
                source, destination = source_dest.split("->", 1)
            except ValueError:
                continue
            mounts.append({
                "source": source.strip(),
                "destination": destination.strip(),
                "bind_rw": rw.strip().lower() == "true",
            })
        rows.append({
            "container": parts[0].lstrip("/"),
            "mounts": mounts,
        })
    return rows


def _storage_source(path):
    path = str(path or "")
    return (
        path == "/DATA" or path.startswith("/DATA/")
        or path == "/media" or path.startswith("/media/")
        or path == "/mnt" or path.startswith("/mnt/")
        or path == "/srv" or path.startswith("/srv/")
        or path == "/var/lib/casaos_data/.media"
        or path.startswith("/var/lib/casaos_data/.media/")
    )


def _mount_role(source, destination):
    low = f"{source} {destination}".lower()
    if any(item in low for item in (
        "/config", "appdata", "/database", "/db", "/cache"
    )):
        return "configuration"
    if any(item in low for item in (
        "/media", "/movies", "/tv", "/music", "/photos", "/downloads"
    )):
        return "media"
    return "storage"


def _inspect_containers(rows, run_command):
    names = sorted({row["container"] for row in rows if row.get("container")})
    if not names:
        return {}, ""
    command = "docker inspect --format '{{json .}}' " + " ".join(
        shlex.quote(name) for name in names
    ) + " 2>/dev/null || true"
    output = _run(run_command, command, 20)
    result = {}
    for raw in output.splitlines():
        try:
            item = json.loads(raw)
        except (TypeError, ValueError):
            continue
        name = str(item.get("Name", "") or "").lstrip("/")
        if not name:
            continue
        config = item.get("Config") or {}
        state = item.get("State") or {}
        env = {}
        for value in config.get("Env") or []:
            if "=" in str(value):
                key, env_value = str(value).split("=", 1)
                if key in {"PUID", "PGID", "USER_ID", "GROUP_ID", "UMASK", "UMASK_SET"}:
                    env[key] = env_value
        result[name] = {
            "configured_user": str(config.get("User", "") or ""),
            "environment": env,
            "pid": int(state.get("Pid") or 0),
        }

    pids = sorted({item["pid"] for item in result.values() if item["pid"] > 0})
    if pids:
        status_command = ""
        for pid in pids:
            status_command += (
                f"printf '===PID {pid}===\\n'; "
                f"sed -n '/^Uid:/p;/^Gid:/p;/^Groups:/p' /proc/{pid}/status "
                "2>/dev/null || true; "
            )
        status_output = _run(run_command, status_command, 12)
        current = 0
        runtime = {}
        for line in status_output.splitlines():
            marker = re.match(r"^===PID (\d+)===$", line.strip())
            if marker:
                current = int(marker.group(1))
                runtime[current] = {}
                continue
            if not current or ":" not in line:
                continue
            key, value = line.split(":", 1)
            numbers = [int(x) for x in re.findall(r"\d+", value)]
            if key == "Uid" and numbers:
                runtime[current]["uid"] = numbers[1] if len(numbers) > 1 else numbers[0]
            elif key == "Gid" and numbers:
                runtime[current]["gid"] = numbers[1] if len(numbers) > 1 else numbers[0]
            elif key == "Groups":
                runtime[current]["groups"] = numbers
        for item in result.values():
            item.update(runtime.get(item["pid"], {}))
    return result, output


def _path_snapshot(path, run_command):
    quoted = shlex.quote(path)
    command = (
        f"p={quoted}; "
        "printf '%s\\n' '---STAT---'; "
        "if [ -e \"$p\" ] || [ -L \"$p\" ]; then "
        "stat -Lc 'exists=yes mode=%a symbolic=%A uid=%u gid=%g type=%F' -- \"$p\" 2>/dev/null || true; "
        "else printf '%s\\n' 'exists=no'; fi; "
        "printf '%s\\n' '---FINDMNT---'; "
        "findmnt -T \"$p\" -P -n -o SOURCE,TARGET,FSTYPE,OPTIONS 2>/dev/null || true; "
        "printf '%s\\n' '---ACL---'; "
        "if command -v getfacl >/dev/null 2>&1; then "
        "printf '%s\\n' 'tool=available'; getfacl -cpn -- \"$p\" 2>/dev/null | head -30; "
        "else printf '%s\\n' 'tool=unavailable'; fi"
    )
    output = _run(run_command, command, 8)
    sections = {"stat": [], "findmnt": [], "acl": []}
    current = ""
    for line in output.splitlines():
        marker = line.strip()
        if marker == "---STAT---":
            current = "stat"
        elif marker == "---FINDMNT---":
            current = "findmnt"
        elif marker == "---ACL---":
            current = "acl"
        elif current:
            sections[current].append(line)

    stat = parse_pairs(sections["stat"][0] if sections["stat"] else "")
    mount = parse_pairs(sections["findmnt"][0] if sections["findmnt"] else "")
    acl_lines = sections["acl"]
    acl_available = any(line.strip() == "tool=available" for line in acl_lines)
    named_acl = any(re.match(r"^(default:)?(user|group):[^:]", line.strip()) for line in acl_lines)
    return {
        "path": path,
        "stat": {
            "evidence_available": stat.get("exists") == "yes",
            "exists": stat.get("exists") == "yes",
            "mode": stat.get("mode", ""),
            "symbolic": stat.get("symbolic", ""),
            "uid": _integer(stat.get("uid")),
            "gid": _integer(stat.get("gid")),
            "type": stat.get("type", ""),
        },
        "mount": {
            "evidence_available": bool(mount.get("TARGET")),
            "source": mount.get("SOURCE", ""),
            "target": mount.get("TARGET", ""),
            "fstype": mount.get("FSTYPE", "").lower(),
            "options": mount.get("OPTIONS", ""),
        },
        "acl": {
            "available": acl_available,
            "named_entries": named_acl,
            "text": "\n".join(
                line for line in acl_lines if not line.startswith("tool=")
            )[:2000],
        },
        "raw": output[:5000],
        "evidence_available": bool(output) and not output.startswith("ERROR:"),
    }


def _integer(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _configured_identity(identity):
    env = identity.get("environment", {}) or {}
    puid = _integer(env.get("PUID", env.get("USER_ID")))
    pgid = _integer(env.get("PGID", env.get("GROUP_ID")))
    if puid is not None and pgid is not None:
        return puid, pgid, "PUID/PGID environment"

    configured = str(identity.get("configured_user", "") or "").strip()
    match = re.match(r"^(\d+)(?::(\d+))?$", configured)
    if match and match.group(2) is not None:
        return int(match.group(1)), int(match.group(2)), "Docker Config.User"

    uid = _integer(identity.get("uid"))
    gid = _integer(identity.get("gid"))
    if uid is not None and gid is not None:
        return uid, gid, "container init process"
    return None, None, "unavailable"


def _persistence_snapshot(mount, run_command):
    target = mount.get("target", "")
    source = mount.get("source", "")
    candidates = [
        "/etc/fstab",
        "/var/lib/casaos/local-storage/local-storage.json",
        "/var/lib/casaos/local-storage/storage.json",
        "/var/lib/casaos_data/local-storage/local-storage.json",
    ]
    if target:
        candidates.append(target.rstrip("/") + "/.zimaos_storage.json")
    command = ""
    for path in candidates:
        quoted_path = shlex.quote(path)
        command += (
            f"p={quoted_path}; if [ -f \"$p\" ]; then "
            f"printf 'FILE|%s\\n' \"$p\"; "
            f"grep -F -e {shlex.quote(target)} -e {shlex.quote(source)} \"$p\" "
            "2>/dev/null | head -12 || true; fi; "
        )
    output = _run(run_command, command, 8)
    searched = []
    matches = []
    current = ""
    for raw in output.splitlines():
        if raw.startswith("FILE|"):
            current = raw.split("|", 1)[1]
            searched.append(current)
        elif current and raw.strip():
            matches.append({"path": current, "evidence": raw.strip()})
    return {
        "searched": searched,
        "matches": matches,
        "source_verified": bool(matches),
        "raw": output[:3000],
    }


def _active_users_snapshot(mount, run_command):
    target = mount.get("target", "")
    if not target:
        return {"collected": False, "text": ""}
    output = _run(
        run_command,
        f"fuser -vm {shlex.quote(target)} 2>&1 | head -40 || true",
        8,
    )
    return {
        "collected": bool(output) and not output.startswith("ERROR:"),
        "text": output[:4000],
    }


def collect_bind_mount_permission_evidence(docker_access, run_command, limit=80):
    rows = parse_docker_access(docker_access)
    bindings = []
    for row in rows:
        for mount in row["mounts"]:
            if _storage_source(mount["source"]):
                bindings.append({
                    "container": row["container"],
                    **mount,
                    "role": _mount_role(mount["source"], mount["destination"]),
                })
    truncated = len(bindings) > limit
    bindings = bindings[:limit]
    identities, raw_inspect = _inspect_containers(rows, run_command)
    snapshots = {}
    for source in sorted({item["source"] for item in bindings}):
        snapshots[source] = _path_snapshot(source, run_command)

    mount_extras = {}
    for snapshot in snapshots.values():
        mount = snapshot.get("mount", {})
        key = mount.get("target", "")
        if not key or key in mount_extras:
            continue
        fstype = mount.get("fstype", "")
        mount_extras[key] = {
            "persistence": _persistence_snapshot(mount, run_command),
            "active_users": (
                _active_users_snapshot(mount, run_command)
                if fstype in NON_POSIX_PERMISSION_FILESYSTEMS
                else {"collected": False, "text": ""}
            ),
        }

    records = []
    for binding in bindings:
        identity = identities.get(binding["container"], {})
        uid, gid, identity_source = _configured_identity(identity)
        snapshot = snapshots.get(binding["source"], {})
        mount = snapshot.get("mount", {})
        extras = mount_extras.get(mount.get("target", ""), {})
        records.append({
            **binding,
            "configured_user": identity.get("configured_user", ""),
            "environment": identity.get("environment", {}),
            "runtime_uid": identity.get("uid"),
            "runtime_gid": identity.get("gid"),
            "runtime_groups": identity.get("groups", []),
            "effective_uid": uid,
            "effective_gid": gid,
            "identity_source": identity_source,
            "stat": snapshot.get("stat", {}),
            "mount": mount,
            "acl": snapshot.get("acl", {}),
            "persistence": extras.get("persistence", {}),
            "active_users": extras.get("active_users", {}),
            "live_remount": {"attempted": False, "result": "not tested"},
            "write_test": {"attempted": False, "result": "not tested"},
            "evidence_available": bool(snapshot.get("evidence_available")),
        })

    return {
        "collected": True,
        "records": records,
        "truncated": truncated,
        "raw_inspect_available": bool(raw_inspect) and not raw_inspect.startswith("ERROR:"),
        "limitations": (["Storage bind evidence was truncated."] if truncated else []),
    }


def _mode_write_access(mode, owner_uid, owner_gid, uid, gid, groups=None):
    try:
        numeric_mode = int(str(mode), 8)
    except (TypeError, ValueError):
        return None, "unknown"
    if uid == 0:
        return True, "root"
    groups = set(groups or []) | ({gid} if gid is not None else set())
    if uid is not None and uid == owner_uid:
        return bool(numeric_mode & 0o200), "owner"
    if owner_gid is not None and owner_gid in groups:
        return bool(numeric_mode & 0o020), "group"
    return bool(numeric_mode & 0o002), "other"


def _option_set(options):
    return {item.strip().lower() for item in str(options or "").split(",") if item.strip()}


def assess_record(record):
    mount = record.get("mount", {}) or {}
    stat = record.get("stat", {}) or {}
    acl = record.get("acl", {}) or {}
    options = _option_set(mount.get("options", ""))
    fstype = mount.get("fstype", "").lower()
    uid = _integer(record.get("effective_uid"))
    gid = _integer(record.get("effective_gid"))
    identity_source = record.get("identity_source", "")
    identity_groups = (
        record.get("runtime_groups", [])
        if identity_source == "container init process"
        else []
    )
    write_allowed, permission_class = _mode_write_access(
        stat.get("mode"), stat.get("uid"), stat.get("gid"), uid, gid,
        identity_groups,
    )
    write_test = record.get("write_test", {}) or {}
    write_result = str(write_test.get("result", "not tested") or "").lower()
    host_ro = "ro" in options and "rw" not in options
    bind_ro = not bool(record.get("bind_rw"))
    non_posix = fstype in NON_POSIX_PERMISSION_FILESYSTEMS
    classification = "evidence_incomplete"
    severity = "INCOMPLETE"
    verification = "PARTIALLY VERIFIED"
    explanation = "The exact container write path is not fully verified."

    if host_ro:
        classification = "host_mount_read_only"
        severity = "HIGH"
        verification = (
            "VERIFIED"
            if write_result in {"denied", "permission denied", "failed"}
            or identity_source in {"Docker Config.User", "container init process"}
            else "PARTIALLY VERIFIED"
        )
        explanation = "The host filesystem itself is mounted read-only."
    elif bind_ro:
        classification = "docker_bind_read_only"
        severity = "HIGH"
        verification = "VERIFIED"
        explanation = "The host mount is available, but this Docker bind is read-only."
    elif uid is None or gid is None or not stat.get("evidence_available") or not mount.get("evidence_available"):
        explanation = "Container identity, host ownership or active mount evidence is incomplete."
    elif write_result in {"success", "passed", "writable"}:
        classification = "application_level_restriction_possible"
        severity = "WARNING"
        verification = "PARTIALLY VERIFIED"
        explanation = (
            "The direct container-identity write/remove probe passed. A remaining delete "
            "failure is more likely application-level, but app configuration still needs verification."
        )
    elif write_allowed is False and non_posix:
        classification = "filesystem_mount_mask_restriction"
        severity = "HIGH" if write_result in {"denied", "permission denied", "failed"} else "WARNING"
        verification = "VERIFIED" if write_result in {"denied", "permission denied", "failed"} else "PARTIALLY VERIFIED"
        explanation = (
            f"The {fstype} mount is read/write, but its synthesized ownership/mode does not "
            "grant write access to the container identity."
        )
    elif write_allowed is False and acl.get("available") and not acl.get("named_entries"):
        classification = (
            "numeric_uid_gid_mismatch"
            if uid != stat.get("uid") and gid != stat.get("gid")
            else "directory_mode_blocks_container"
        )
        severity = "HIGH" if write_result in {"denied", "permission denied", "failed"} else "WARNING"
        verification = (
            "VERIFIED"
            if write_result in {"denied", "permission denied", "failed"}
            else "PARTIALLY VERIFIED"
        )
        explanation = "Host directory mode and numeric ownership block this container identity."
    elif write_allowed is False:
        classification = "acl_or_directory_permission_restriction"
        severity = "WARNING"
        explanation = (
            "Directory mode does not grant write access, but ACL evidence is unavailable or "
            "contains named entries, so the exact permission gate is incomplete."
        )
    elif write_result in {"denied", "permission denied", "failed"}:
        classification = "permission_denied_unresolved"
        severity = "WARNING"
        explanation = (
            "The write probe failed even though mount and basic mode evidence appear writable; "
            "ACL, namespace or another access-control layer still needs verification."
        )
    elif write_allowed is True:
        classification = "mode_allows_write_not_tested"
        severity = "INFORMATION"
        verification = "PARTIALLY VERIFIED"
        explanation = (
            "Mount and basic mode evidence allow write access, but an actual harmless write/remove "
            "probe has not been run."
        )

    return {
        **record,
        "classification": classification,
        "severity": severity,
        "verification": verification,
        "explanation": explanation,
        "host_read_only": host_ro,
        "bind_read_only": bind_ro,
        "filesystem_uses_mount_permissions": non_posix,
        "mode_write_allowed": write_allowed,
        "permission_class": permission_class,
        "issue": classification not in {
            "mode_allows_write_not_tested", "application_level_restriction_possible",
            "evidence_incomplete",
        },
    }


def assess_evidence(evidence):
    source = evidence if isinstance(evidence, dict) else {}
    records = [assess_record(item) for item in source.get("records", [])]
    return {
        **source,
        "records": records,
    }


def question_selection(assessment, question, candidate_limit=5):
    records = assessment.get("records", []) or []
    low = str(question or "").lower()
    container_exact = []
    path_exact = []
    for item in records:
        name = item.get("container", "").lower()
        if not name:
            continue
        meaningful_parts = [
            part for part in re.split(r"[-_.]+", name)
            if len(part) >= 3 and part not in {"app", "server", "container"}
        ]
        source = str(item.get("source", "") or "").lower()
        destination = str(item.get("destination", "") or "").lower()
        explicit_path = any(
            path and path != "/" and path in low
            for path in (source, destination)
        )
        if name in low or any(
            re.search(rf"\b{re.escape(part)}\b", low)
            for part in meaningful_parts
        ):
            container_exact.append(item)
        if explicit_path:
            path_exact.append(item)
    exact = path_exact or container_exact
    if exact:
        return {
            "records": exact,
            "focused": True,
            "candidate_count": len(exact),
        }

    actionable = [
        item for item in records
        if item.get("role") in {"media", "storage"} and item.get("issue")
    ]
    severity_order = {"CRITICAL": 0, "HIGH": 1, "WARNING": 2, "INCOMPLETE": 3}
    actionable.sort(key=lambda item: (
        severity_order.get(item.get("severity"), 9),
        item.get("container", ""),
        item.get("source", ""),
    ))
    return {
        "records": actionable[:candidate_limit],
        "focused": False,
        "candidate_count": len(actionable),
    }


def records_for_question(assessment, question):
    return question_selection(assessment, question)["records"]


def permission_fingerprint(record):
    mount = record.get("mount", {}) or {}
    stat = record.get("stat", {}) or {}
    return "|".join(str(value or "") for value in (
        record.get("classification"), record.get("source"), record.get("destination"),
        record.get("bind_rw"), mount.get("fstype"), mount.get("options"),
        stat.get("mode"), stat.get("uid"), stat.get("gid"),
        record.get("effective_uid"), record.get("effective_gid"),
    ))


def safe_probe_command(record):
    if (
        record.get("role") != "media"
        or not record.get("container")
        or not str(record.get("destination", "")).startswith("/")
        or record.get("effective_uid") is None
        or record.get("effective_gid") is None
    ):
        return ""
    destination = record["destination"].rstrip("/")
    test_path = destination + "/.zimabrain-permission-test"
    script = (
        f"testfile={shlex.quote(test_path)}; "
        "trap 'rm -f \"$testfile\"' EXIT; "
        "touch \"$testfile\" && rm -f \"$testfile\""
    )
    return (
        f"docker exec -u {record['effective_uid']}:{record['effective_gid']} "
        f"{shlex.quote(record['container'])} sh -c {shlex.quote(script)}"
    )
