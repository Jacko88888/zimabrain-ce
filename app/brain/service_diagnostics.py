import re
import shlex


UNIT_SUFFIXES = ("service", "timer", "mount", "socket")
HELPER_SUFFIXES = (
    "watchdog",
    "helper",
    "monitor",
    "healthcheck",
    "health-check",
    "delay",
)
RELATION_PROPERTIES = (
    "PartOf",
    "BindsTo",
    "Requires",
    "Requisite",
    "Wants",
)
EXEC_PROPERTIES = ("ExecStartPre", "ExecStart", "ExecStartPost")
OS_MANAGED_PREFIXES = (
    "/usr/libexec/",
    "/usr/lib/systemd/",
    "/usr/bin/",
    "/usr/sbin/",
    "/lib/systemd/",
)


def parse_systemctl_show(text):
    result = {}
    for raw in str(text or "").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def failed_unit_names(text):
    names = []
    for raw in str(text or "").splitlines():
        clean = raw.replace("●", " ").strip()
        if not clean or clean.startswith("ERROR:"):
            continue
        if "0 loaded units listed" in clean.lower() or "no units listed" in clean.lower():
            continue
        for token in clean.split():
            token = token.strip()
            if token.endswith(tuple("." + suffix for suffix in UNIT_SUFFIXES)):
                if token not in names:
                    names.append(token)
                break
    return names


def _unit_tokens(value):
    return [
        token
        for token in re.split(r"\s+", str(value or "").strip())
        if token.endswith(".service")
    ]


def _stem(unit):
    return re.sub(r"\.service$", "", str(unit or "").lower())


def related_service_candidates(unit, properties=None):
    unit = str(unit or "").strip()
    properties = properties if isinstance(properties, dict) else {}
    candidates = []

    stem = _stem(unit)
    for suffix in HELPER_SUFFIXES:
        marker = "-" + suffix
        if stem.endswith(marker):
            candidates.append(stem[:-len(marker)] + ".service")
            break

    relation_candidates = []
    for key in RELATION_PROPERTIES:
        relation_candidates.extend(_unit_tokens(properties.get(key, "")))

    base_words = set(re.split(r"[-_.@]+", stem)) - set(HELPER_SUFFIXES)
    relation_candidates.sort(
        key=lambda candidate: (
            -len(base_words & set(re.split(r"[-_.@]+", _stem(candidate)))),
            RELATION_PROPERTIES.index(
                next(
                    key for key in RELATION_PROPERTIES
                    if candidate in _unit_tokens(properties.get(key, ""))
                )
            ),
            candidate,
        )
    )
    candidates.extend(relation_candidates)

    result = []
    for candidate in candidates:
        if candidate and candidate != unit and candidate not in result:
            result.append(candidate)
    return result


def related_service_name(unit, properties=None):
    candidates = related_service_candidates(unit, properties)
    return candidates[0] if candidates else ""


def _absolute_paths(value):
    paths = []
    for match in re.findall(r"(?<![\w.-])/(?:[A-Za-z0-9._@:+-]+/?)+", str(value or "")):
        path = match.rstrip(" ;,}\"'")
        if path and path not in paths:
            paths.append(path)
    return paths


def referenced_paths(properties):
    records = []

    fragment = str(properties.get("FragmentPath", "") or "").strip()
    if fragment:
        records.append({
            "path": fragment,
            "source": "FragmentPath",
            "requires_executable": False,
        })

    for phase in EXEC_PROPERTIES:
        value = str(properties.get(phase, "") or "")
        executable_paths = set(
            match.rstrip(" ;,}\"'")
            for match in re.findall(r"(?:^|[;{ ])path=([^ ;}]+)", value)
        )
        paths = _absolute_paths(value)
        if not executable_paths and paths:
            executable_paths.add(paths[0])
        for path in paths:
            records.append({
                "path": path,
                "source": phase,
                "requires_executable": path in executable_paths,
            })

    unique = []
    by_path = {}
    for record in records:
        existing = by_path.get(record["path"])
        if existing:
            existing["requires_executable"] = (
                existing["requires_executable"]
                or record["requires_executable"]
            )
            if record["source"] not in existing["source"].split(","):
                existing["source"] += "," + record["source"]
            continue
        item = dict(record)
        by_path[item["path"]] = item
        unique.append(item)
    return unique


def _run(run_command, command, timeout):
    try:
        return str(run_command(command, timeout=timeout) or "").strip()
    except TypeError:
        return str(run_command(command, timeout) or "").strip()
    except Exception as error:
        return f"ERROR: {error}"


def _path_state(run_command, record):
    path = record["path"]
    quoted = shlex.quote(path)
    command = (
        f"p={quoted}; "
        "if [ -e \"$p\" ]; then "
        "printf 'exists=yes\\n'; "
        "if [ -x \"$p\" ]; then printf 'executable=yes\\n'; "
        "else printf 'executable=no\\n'; fi; "
        "if [ -r \"$p\" ]; then printf 'readable=yes\\n'; "
        "else printf 'readable=no\\n'; fi; "
        "stat -c 'mode=%A (%a) owner=%U:%G type=%F' \"$p\" 2>/dev/null || true; "
        "elif [ -L \"$p\" ]; then printf 'exists=no\\nbroken_symlink=yes\\n'; "
        "else printf 'exists=no\\n'; fi"
    )
    output = _run(run_command, command, 5)
    values = parse_systemctl_show(output)
    item = dict(record)
    item.update({
        "exists": values.get("exists") == "yes",
        "executable": values.get("executable") == "yes",
        "readable": values.get("readable") == "yes",
        "broken_symlink": values.get("broken_symlink") == "yes",
        "stat": values.get("mode", ""),
        "evidence": output,
        "evidence_available": bool(output) and not output.startswith("ERROR:"),
    })
    return item


SHOW_PROPERTIES = (
    "Id LoadState ActiveState SubState Result FragmentPath UnitFileState "
    "ExecMainStatus ExecMainCode StatusErrno StateChangeTimestamp "
    "ActiveEnterTimestamp InactiveEnterTimestamp Description "
    "ExecStartPre ExecStart ExecStartPost PartOf BindsTo Requires Requisite Wants"
)


def _show_command(unit, properties=SHOW_PROPERTIES):
    flags = " ".join("-p " + item for item in properties.split())
    return f"systemctl show {shlex.quote(unit)} {flags} --no-pager 2>&1 || true"


def collect_failed_unit_details(failed_units_text, run_command):
    details = []
    for unit in failed_unit_names(failed_units_text):
        show = _run(run_command, _show_command(unit), 12)
        properties = parse_systemctl_show(show)
        status = _run(
            run_command,
            f"systemctl status {shlex.quote(unit)} --no-pager -n 40 2>&1 || true",
            12,
        )
        journal = _run(
            run_command,
            f"journalctl -u {shlex.quote(unit)} -n 80 -o short-iso --no-pager 2>&1 || true",
            12,
        )
        paths = [
            _path_state(run_command, record)
            for record in referenced_paths(properties)
        ]

        primary = None
        candidates = related_service_candidates(unit, properties)
        for candidate in candidates:
            primary_show = _run(run_command, _show_command(
                candidate,
                "Id LoadState ActiveState SubState Result FragmentPath StateChangeTimestamp",
            ), 8)
            primary_props = parse_systemctl_show(primary_show)
            candidate_record = {
                "unit": candidate,
                "properties": primary_props,
                "raw_show": primary_show,
                "evidence_available": bool(primary_props.get("Id")),
            }
            if primary is None:
                primary = candidate_record
            if (
                primary_props.get("Id")
                and primary_props.get("LoadState", "").lower() != "not-found"
            ):
                primary = candidate_record
                break

        details.append({
            "unit": unit,
            "failed_line": next(
                (line.strip() for line in str(failed_units_text).splitlines() if unit in line),
                unit,
            ),
            "properties": properties,
            "raw_show": show,
            "status": status,
            "journal": journal,
            "paths": paths,
            "primary_candidates": candidates,
            "primary": primary,
            "evidence_available": bool(properties.get("Id")),
        })
    return details


def _journal_missing_path(journal):
    low = str(journal or "").lower()
    return any(marker in low for marker in (
        "no such file or directory",
        "failed to locate executable",
        "failed at step exec",
        "unable to locate executable",
    ))


def assess_detail(detail):
    properties = detail.get("properties", {}) or {}
    paths = detail.get("paths", []) or []
    primary = detail.get("primary") or {}
    primary_props = primary.get("properties", {}) or {}

    missing = [item for item in paths if item.get("evidence_available") and not item.get("exists")]
    non_executable = [
        item for item in paths
        if item.get("evidence_available")
        and item.get("exists")
        and item.get("requires_executable")
        and not item.get("executable")
    ]
    missing_fragments = [item for item in missing if "FragmentPath" in item["source"].split(",")]
    missing_references = [item for item in missing if item not in missing_fragments]
    missing_system = [
        item for item in missing_references
        if item["path"].startswith(OS_MANAGED_PREFIXES)
    ]
    missing_data = [
        item for item in missing_references
        if item["path"].startswith("/DATA/")
    ]
    missing_other = [
        item for item in missing_references
        if item not in missing_system and item not in missing_data
    ]

    execution_text = "\n".join((
        str(detail.get("status", "") or ""),
        str(detail.get("journal", "") or ""),
    )).lower()
    status_203 = (
        str(properties.get("ExecMainStatus", "")) == "203"
        or "status=203/exec" in execution_text
    )
    journal_missing = _journal_missing_path(detail.get("journal", ""))
    status_missing = _journal_missing_path(detail.get("status", ""))
    is_helper = bool(detail.get("primary_candidates"))
    primary_available = bool(primary.get("evidence_available"))
    primary_state = str(primary_props.get("ActiveState", "") or "unknown").lower()
    primary_substate = str(primary_props.get("SubState", "") or "unknown").lower()
    path_evidence_complete = all(
        item.get("evidence_available") for item in paths
    )

    if is_helper and primary_available and primary_state == "active":
        outage = "no"
        severity = "LOWERED WARNING"
        verification = "VERIFIED"
    elif is_helper and primary_available and (
        primary_state == "failed" or primary_substate == "failed"
    ):
        outage = "yes"
        severity = "HIGH"
        verification = "VERIFIED"
    elif is_helper:
        outage = "not verified"
        severity = "UNCONFIRMED"
        verification = "PARTIALLY VERIFIED"
    else:
        outage = "not applicable"
        severity = "HIGH" if status_203 or missing or non_executable else "WARNING"
        verification = "VERIFIED" if detail.get("evidence_available") else "PARTIALLY VERIFIED"

    if not detail.get("evidence_available") or not path_evidence_complete:
        verification = "PARTIALLY VERIFIED"

    fragment = str(properties.get("FragmentPath", "") or "")
    os_managed_unit = fragment.startswith(("/usr/lib/systemd/", "/lib/systemd/"))
    possible_packaging_regression = bool(
        missing_system and os_managed_unit
        and (status_203 or journal_missing or status_missing)
    )

    return {
        "unit": detail.get("unit", ""),
        "is_helper": is_helper,
        "primary_unit": primary.get("unit", "") if is_helper else "",
        "primary_available": primary_available,
        "primary_state": primary_state,
        "primary_substate": primary_substate,
        "current_outage": outage,
        "severity": severity,
        "verification": verification,
        "path_evidence_complete": path_evidence_complete,
        "missing": missing,
        "missing_fragments": missing_fragments,
        "missing_system": missing_system,
        "missing_data": missing_data,
        "missing_other": missing_other,
        "non_executable": non_executable,
        "status_203": status_203,
        "journal_missing_path": journal_missing,
        "status_missing_path": status_missing,
        "possible_packaging_regression": possible_packaging_regression,
        "fragment_path": fragment,
    }


def assess_details(details):
    return [assess_detail(detail) for detail in (details or [])]


def critical_finding(assessment):
    if assessment["is_helper"] and assessment["current_outage"] == "no":
        title = "Failed helper unit; primary service remains active"
        why = "No current primary-service outage was verified, so this helper failure has reduced severity."
        level = "YELLOW"
    elif assessment["is_helper"] and assessment["current_outage"] == "yes":
        title = "Helper and related primary service are both failed"
        why = "The primary-service failure indicates a current outage, so severity remains high."
        level = "RED"
    elif assessment["is_helper"]:
        title = "Failed helper unit; primary-service state is unconfirmed"
        why = "The helper failure is verified, but current primary-service evidence is incomplete."
        level = "YELLOW"
    elif assessment["missing_system"]:
        title = "Missing ZimaOS-managed helper/executable detected"
        why = "A possible packaging regression or stale service definition needs version-aware confirmation."
        level = "YELLOW"
    elif assessment["missing_data"]:
        title = "Failed unit references a missing local /DATA script or file"
        why = "The failed unit contains a broken or stale local path reference."
        level = "YELLOW"
    elif assessment["non_executable"]:
        title = "Required service executable lacks executable permission"
        why = "The referenced file exists but systemd cannot execute it with its current mode."
        level = "YELLOW"
    else:
        title = "Failed systemd unit detected"
        why = "A failed host unit can indicate a broken scheduled task, service, or maintenance layer."
        level = "YELLOW"

    return {
        "level": level,
        "title": title,
        "detail": (
            f"unit={assessment['unit']} primary={assessment['primary_unit'] or 'n/a'} "
            f"primary_state={assessment['primary_state']}/{assessment['primary_substate']} "
            f"outage={assessment['current_outage']}"
        ),
        "why": why,
        "next": "Inspect the Failed Units Layer evidence before changing or restarting services.",
    }
