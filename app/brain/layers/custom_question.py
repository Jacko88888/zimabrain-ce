import os
import re

from brain import health_memory


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


AREA_RULES = [
    {
        "name": "Storage paths and mounts",
        "keywords": {
            "access", "appdata", "bind", "directory", "disk", "drive",
            "external", "folder", "library", "media", "mount", "path",
            "permission", "share", "storage", "volume",
        },
        "sources": ("mounts", "media_paths", "lsblk", "disk_identity"),
    },
    {
        "name": "Containers and applications",
        "keywords": {
            "app", "application", "container", "docker", "health",
            "immich", "jellyfin", "nextcloud", "plex", "restart",
            "stopped", "unhealthy",
        },
        "sources": ("docker_states", "docker_ps", "docker_access"),
    },
    {
        "name": "Services and operating system",
        "keywords": {
            "boot", "failed", "helper", "package", "packaging", "reboot",
            "regression", "service", "systemd", "update", "upgrade", "zimaos",
        },
        "sources": (
            "failed_units", "service_hotlist", "active_services", "host_os",
            "kernel", "rauc", "uptime",
        ),
    },
    {
        "name": "Networking and DNS",
        "keywords": {
            "connection", "dns", "firewall", "internet", "lan", "network",
            "port", "route", "routing", "tailscale",
        },
        "sources": (
            "port_reachability", "zfw_status", "zfw_chains", "zfw_files",
            "docker_ps",
        ),
    },
    {
        "name": "Performance and temperature",
        "keywords": {
            "cpu", "hot", "io", "i/o", "load", "memory", "performance",
            "pressure", "slow", "swap", "temperature",
        },
        "sources": (
            "cpu_usage", "memory", "loadavg", "process_top", "io_top",
            "iostat_brief", "sensors", "thermal_zones",
        ),
    },
    {
        "name": "Disk health and hardware",
        "keywords": {
            "crc", "disk", "drive", "hardware", "media", "nvme", "sector",
            "smart", "temperature",
        },
        "sources": ("smart", "nvme_smart", "disk_identity", "lsblk", "sensors"),
    },
    {
        "name": "Security exposure",
        "keywords": {
            "audit", "exposed", "firewall", "open", "port", "privileged",
            "protect", "security", "socket",
        },
        "sources": (
            "self_docker_security", "auditd", "port_reachability", "zfw_status",
            "zfw_chains",
        ),
    },
]


STOP_WORDS = {
    "about", "after", "again", "against", "also", "because", "before",
    "being", "could", "does", "from", "have", "into", "just", "last",
    "lost", "might", "please", "should", "since", "system", "that", "their",
    "there", "these", "they", "this", "what", "when", "where", "which",
    "while", "with", "would", "your", "why", "access", "app", "application",
    "boot", "container", "directory", "disk", "docker", "drive", "external",
    "failed", "folder", "library", "media", "mount", "network", "path",
    "permission", "port", "reboot", "restart", "route", "service", "share",
    "storage", "update", "volume", "zimaos", "check", "condition", "current",
    "determine", "diagnose", "diagnostic", "evidence", "explain", "finding",
    "fictional", "imaginary", "nonexistent", "madeup",
    "give", "provide", "show", "tell",
    "health", "healthy", "infer", "issue", "problem", "report", "running",
    "restarting", "state", "status", "symptom", "verify", "zimabrain",
}


CAUSAL_WORDS = {
    "after", "because", "cause", "caused", "lost", "regression", "since", "why",
}


def _tokens(text):
    return re.findall(r"[a-z0-9][a-z0-9_.-]{1,}", (text or "").lower())


def _areas(question):
    tokens = set(_tokens(question))
    matched = []
    for rule in AREA_RULES:
        overlap = sorted(tokens & rule["keywords"])
        if overlap:
            matched.append((rule, overlap))

    if not matched:
        matched = [
            (AREA_RULES[1], ["custom question"]),
            (AREA_RULES[2], ["custom question"]),
        ]
    return matched


def _entity_tokens(question):
    result = []
    for token in _tokens(question):
        if len(token) < 4 or token in STOP_WORDS or token.isdigit():
            continue
        if token not in result:
            result.append(token)
    return result[:6]


def _compact(value, limit=240):
    value = " ".join(str(value or "").split())
    if len(value) > limit:
        return value[: limit - 1] + "…"
    return value


def _line_score(line, entity_tokens, question_tokens):
    low = line.lower()
    entity_hits = sum(1 for token in entity_tokens if token in low)
    if entity_hits:
        return 10 + entity_hits
    return sum(1 for token in question_tokens if len(token) >= 4 and token in low)


def _matching_evidence(question, bundle, matched_areas, limit=12):
    evidence = bundle.get("same_report_evidence", {}) or {}
    question_tokens = set(_tokens(question))
    entity_tokens = _entity_tokens(question)
    source_names = []
    for rule, _overlap in matched_areas:
        for source in rule["sources"]:
            if source not in source_names:
                source_names.append(source)

    matches = []
    seen = set()

    for finding in bundle.get("critical_findings", []) or []:
        joined = " | ".join(
            str(finding.get(key, "") or "")
            for key in ("title", "detail", "why")
        )
        score = _line_score(joined, entity_tokens, question_tokens)
        minimum = 10 if entity_tokens else 2
        if score >= minimum:
            text = _compact(
                f"{finding.get('level', 'INFO')}: "
                f"{finding.get('title', 'Local finding')} — "
                f"{finding.get('detail', '')}"
            )
            key = ("critical_findings", text)
            if key not in seen:
                seen.add(key)
                matches.append((score + 20, "critical_findings", text))

    for source in source_names:
        raw = str(evidence.get(source, "") or "")
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            score = _line_score(line, entity_tokens, question_tokens)
            minimum = 10 if entity_tokens else 2
            if score < minimum:
                continue
            text = _compact(line)
            key = (source, text)
            if key in seen:
                continue
            seen.add(key)
            matches.append((score, source, text))

    timeline_available = False
    if os.path.isfile(TREND_DB_PATH):
        try:
            events = health_memory.latest_events(TREND_DB_PATH, limit=500)
            timeline_available = bool(events)
            for event in events:
                joined = " | ".join(
                    str(event.get(key, "") or "")
                    for key in (
                        "entity_name", "metric", "classification", "message",
                        "previous_text", "current_text",
                    )
                )
                score = _line_score(joined, entity_tokens, question_tokens)
                minimum = 10 if entity_tokens else 2
                if score < minimum:
                    continue
                text = _compact(event.get("message") or joined)
                key = ("health_timeline", text)
                if key in seen:
                    continue
                seen.add(key)
                matches.append((score + 10, "health_timeline", text))
        except Exception:
            timeline_available = False

    matches.sort(key=lambda item: (-item[0], item[1], item[2]))
    available = [name for name in source_names if str(evidence.get(name, "") or "").strip()]
    if timeline_available:
        available.append("health_timeline")
    return matches[:limit], available, entity_tokens


def _next_step(matched_areas, entity_tokens):
    names = {rule["name"] for rule, _overlap in matched_areas}
    entity = entity_tokens[0] if entity_tokens else "the affected application"

    if "Storage paths and mounts" in names:
        return (
            f"Verify {entity}'s current container state and exact bind-mount source, "
            "then confirm that source with findmnt before editing paths, permissions, "
            "AppData, or the external library."
        )
    if "Containers and applications" in names:
        return (
            f"Inspect {entity}'s current state, health, restart count, bind mounts, and "
            "recent logs before recreating or reinstalling it."
        )
    if "Services and operating system" in names:
        return (
            "Check the exact failed unit and its recent journal, then compare when the "
            "fault first appeared against the local ZimaOS version timeline."
        )
    if "Networking and DNS" in names:
        return (
            "Verify the listening socket, route, DNS result, and firewall reachability "
            "from the same interface before changing network configuration."
        )
    if "Performance and temperature" in names:
        return (
            "Repeat the scan while the symptom is active and compare the responsible "
            "CPU, memory, I/O process, and temperature evidence."
        )
    if "Security exposure" in names:
        return (
            "Confirm the exact listening port, bind address, privilege setting, and "
            "Docker socket access before changing exposure or firewall rules."
        )
    return "Collect a fresh report while the symptom is active and verify the affected component directly."


def answer(question, bundle):
    matched_areas = _areas(question)
    matches, available, entity_tokens = _matching_evidence(
        question, bundle, matched_areas
    )
    causal = bool(set(_tokens(question)) & CAUSAL_WORDS)

    lines = ["- Custom question accepted; it was not restricted to a prepared prompt."]
    lines.extend(["", "#### Relevant diagnostic areas"])
    for rule, overlap in matched_areas:
        lines.append(f"- {rule['name']} — matched: {', '.join(overlap)}")

    lines.extend(["", "#### Evidence checked"])
    if available:
        lines.append(f"- Available local evidence sources: {', '.join(available)}")
    else:
        lines.append("- No relevant local evidence source was captured in this report.")

    lines.extend(["", "#### What is verified"])
    if matches:
        for _score, source, text in matches:
            lines.append(f"- [{source}] {text}")
    else:
        lines.append("- No matching same-report evidence was found for the named symptom or component.")

    lines.extend(["", "#### What remains unverified"])
    if not matches:
        lines.append("- The affected component, its current state, and the cause remain unverified.")
    elif causal:
        lines.append("- Matching current evidence was found, but the reported cause or timing needs extra verification.")
        lines.append("- The report does not prove that the preceding reboot, update, or change caused the symptom.")
    else:
        lines.append("- No additional causal claim was required by this question.")

    next_step = _next_step(matched_areas, entity_tokens)

    if not matches:
        trust_state = "NOT VERIFIED"
        trust_title = "❌ NOT VERIFIED FROM CURRENT REPORT"
        trust_detail = "Relevant diagnostic areas were identified, but no matching local evidence verified the named symptom or component."
    elif causal:
        trust_state = "PARTIALLY VERIFIED"
        trust_title = "⚠️ PARTIALLY VERIFIED"
        trust_detail = "Matching local evidence was found, but the cause or timing still requires confirmation."
    else:
        trust_state = "VERIFIED"
        trust_title = "✅ VERIFIED FROM SAME-REPORT EVIDENCE"
        trust_detail = "The answer is based on matching evidence in the current local report."

    areas_text = ", ".join(rule["name"] for rule, _overlap in matched_areas)
    forum_summary = (
        f"ZimaBrain accepted the custom question and checked {areas_text}. "
        f"It found {len(matches)} matching local evidence item(s); facts not present "
        "in the report remain explicitly unverified."
    )

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
        "trust_state": trust_state,
        "trust_title": trust_title,
        "trust_detail": trust_detail,
        "matched_areas": [rule["name"] for rule, _overlap in matched_areas],
        "match_count": len(matches),
    }
