from pathlib import Path
import json
import re

from brain import intent_policy

try:
    from brain.app_aliases import alias_tokens
except Exception:
    from app.brain.app_aliases import alias_tokens


ALL_FLAGS = [
    "comprehensive_health_question",
    "host_hardware_question",
    "trend_history_question",
    "smart_health_question",
    "hardware_compatibility_question",
    "dashboard_alert_question",
    "failed_unit_question",
    "crc_question",
    "usage_question",
    "exited_question",
    "container_question",
    "docker_daemon_question",
    "disk_health_question",
    "storage_mount_question",
    "docker_bind_mount_question",
    "container_bind_mount_permission_question",
    "app_storage_path_question",
    "app_runtime_diag_question",
    "app_setup_playbook_question",
    "third_party_app_store_question",
    "media_app_verified_guides_question",
    "manual_knowledge_question",
    "backup_borg_question",
    "smart_trend_question",
    "network_exposure_question",
    "zimaos_regression_question",
    "gpu_ai_runtime_question",
    "report_comparison_question",
    "disk_inventory_question",
    "forum_issue_intake_question",
    "read_only_storage_question",
    "install_boot_question",
    "raid_add_drive_question",
    "network_connectivity_question",
    "smb_shares_question",
    "permissions_ownership_question",
    "zimaos_update_safety_question",
    "log_intake_question",
    "repair_planner_question",
    "snapraid_question",
    "disk_command_question",
    "container_command_question",
    "system_command_question",
    "network_command_question",
]


APP_WORDS = alias_tokens()

DISK_WORDS = {"disk", "disks", "drive", "drives", "hdd", "ssd", "nvme", "storage", "capacity"}
MOUNT_WORDS = {"mount", "mounted", "mounts", "media", "path", "paths", "folder", "location", ".media"}
LIST_WORDS = {"list", "show", "what", "which", "current", "inventory", "installed", "many", "count"}
SIZE_WORDS = {"size", "sizes", "capacity", "total", "big", "space"}
HEALTH_WORDS = {"health", "healthy", "bad", "failing", "failed", "smart", "warning", "risk"}
SETUP_WORDS = {"setup", "install", "installed", "configure", "configuration", "update", "upgrade", "latest", "version"}
ISSUE_WORDS = {"not", "cannot", "cant", "can't", "failed", "broken", "working", "restart", "restarting", "problem", "issue"}
NETWORK_WORDS = {"port", "ports", "firewall", "exposed", "public", "remote", "cloudflare", "cloudflared", "tailscale", "tunnel", "proxy"}
DOCKER_WORDS = {"docker", "container", "containers", "daemon", "compose", "volume", "volumes", "bind"}
RAID_WORDS = {"raid", "pool", "snapraid", "mergerfs", "parity"}
ZIMA_WORDS = {"zimaos", "zima", "rauc", "kernel", "version", "update", "upgrade", "rollback", "regression"}
BACKUP_WORDS = {"backup", "backups", "borg", "borgmatic", "restore", "repo"}
GPU_WORDS = {"gpu", "nvidia", "cuda", "ollama", "webui", "openwebui", "ai", "llm"}
COMPARE_WORDS = {"compare", "baseline", "snapshot", "changed", "previous", "before", "after"}
COMMAND_WORDS = {"command", "commands", "cmd"}


def _normalise(text):
    text = (text or "").lower().strip()
    text = text.replace("zima os", "zimaos")
    text = text.replace("open web ui", "openwebui")
    text = text.replace("open webui", "openwebui")
    text = text.replace("open-web-ui", "openwebui")
    text = re.sub(r"\\b(qbit|qbitt)\\b", "qbittorrent", text)
    text = re.sub(r"[^a-z0-9_./%-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text):
    return set(_normalise(text).split())


def _contains_phrase(q, phrases):
    qn = _normalise(q)
    return any(_normalise(p) in qn for p in phrases)


def _score(flags, flag, score, reasons):
    flags.append({
        "flag": flag,
        "score": float(score),
        "matched": reasons[:8],
    })



MANUAL_INDEX_PATHS = [
    Path("/app/docs/zimaos-official/manual-index.json"),
    Path("docs/zimaos-official/manual-index.json"),
]

MANUAL_STOPWORDS = {
    "the", "and", "for", "with", "using", "use", "how", "to", "on", "in",
    "a", "an", "of", "is", "are", "zimaos", "zima", "device", "guide",
    "setup", "set", "up"
}

DIAGNOSTIC_PROBLEM_WORDS = {
    "not", "cannot", "can't", "failed", "fails", "failure", "error", "broken",
    "issue", "problem", "missing", "stuck", "slow", "slowly", "read-only",
    "readonly", "lockup", "locking", "crash", "crashing", "restart",
    "restarting", "down", "offline", "corrupt", "lost", "daemon"
}

def _manual_tokens(text):
    tokens = re.findall(r"[a-z0-9]+", str(text or "").lower())
    return [t for t in tokens if len(t) >= 3 and t not in MANUAL_STOPWORDS]

def _load_manual_pages():
    for path in MANUAL_INDEX_PATHS:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data.get("pages", [])
            except Exception:
                return []
    return []

def _read_manual_text(page, limit=6000):
    path = page.get("markdown") or ""
    candidates = [
        Path("/app") / path,
        Path(path),
    ]
    for c in candidates:
        if c.exists():
            try:
                return c.read_text(encoding="utf-8", errors="replace")[:limit].lower()
            except Exception:
                return ""
    return ""

def _best_manual_index_match(question):
    ql = str(question or "").lower().strip()
    q_tokens = set(_manual_tokens(ql))
    if not q_tokens:
        return {"score": 0, "title": "", "url": ""}

    best = {"score": 0, "title": "", "url": ""}
    for page in _load_manual_pages():
        title = str(page.get("title") or "")
        url = str(page.get("url") or "")
        tl = title.lower()
        ul = url.lower()
        title_tokens = set(_manual_tokens(title))
        url_tokens = set(_manual_tokens(url.replace("-", " ")))

        score = 0

        if ql == tl:
            score += 100
        elif ql in tl or tl in ql:
            score += 70

        title_hits = len(q_tokens & title_tokens)
        url_hits = len(q_tokens & url_tokens)

        if title_hits:
            score += title_hits * 14
        if url_hits:
            score += url_hits * 6

        if title_tokens:
            coverage = title_hits / max(len(q_tokens), 1)
            if coverage >= 0.80:
                score += 35
            elif coverage >= 0.55:
                score += 20

        # Content-level document understanding.
        # This lets the router understand a manual topic even when the user does not type the exact title.
        doc = _read_manual_text(page)
        if doc:
            phrase_hits = 0
            if ql and ql in doc:
                phrase_hits += 1
            content_hits = sum(1 for t in q_tokens if t in doc)
            score += min(content_hits * 2, 24)
            if phrase_hits:
                score += 30

        if score > best["score"]:
            best = {"score": score, "title": title, "url": url}

    return best


def classify(question):
    ql = str(question or "").lower()
    qn = _normalise(question)
    qt = _tokens(qn)
    candidates = []

    has_app = bool(qt & APP_WORDS)
    has_disk = bool(qt & DISK_WORDS)
    has_mount = bool(qt & MOUNT_WORDS)
    has_list = bool(qt & LIST_WORDS)
    has_size = bool(qt & SIZE_WORDS)
    has_health = bool(qt & HEALTH_WORDS)
    has_setup = bool(qt & SETUP_WORDS)
    has_issue = bool(qt & ISSUE_WORDS)
    has_network = bool(qt & NETWORK_WORDS)
    has_docker = bool(qt & DOCKER_WORDS)
    has_raid = bool(qt & RAID_WORDS)
    has_zima = bool(qt & ZIMA_WORDS)
    has_backup = bool(qt & BACKUP_WORDS)
    has_gpu = bool(qt & GPU_WORDS)
    has_compare = bool(qt & COMPARE_WORDS)
    has_command = bool(qt & COMMAND_WORDS)

    policy = intent_policy.classify(question)
    if policy["route_flag"]:
        _score(
            candidates,
            policy["route_flag"],
            300.0,
            [
                f"policy:domain={policy['domain']}",
                f"policy:task={policy['task']}",
                f"policy:entity={policy['entity']}",
            ],
        )

    # Router v1.6.5 quick-question correction gates.
    # Based on real quick-question terminal test failures.

    # CRC natural wording.
    if ("crc" in qt and ("sda" in qt or "sdb" in qt or "disk" in qt or "drive" in qt)) or ("disk" in qt and "dying" in qt):
        _score(candidates, "crc_question", 27.0, ["gate:quick-crc", "entity:disk-crc"])

    # App cannot see files/photos on storage should stay app runtime, not RAID planning.
    if (
        ("immich" in qt or "app" in qt or "jellyfin" in qt or "qbittorrent" in qt or "qbit" in qt)
        and ("cannot" in qt or "cant" in qt or "can't" in qt or "not" in qt)
        and ("see" in qt or "find" in qt or "access" in qt)
        and ("photos" in qt or "files" in qt or "storage" in qt or "drive" in qt or "media" in qt)
    ):
        _score(candidates, "app_runtime_diag_question", 28.0, ["gate:quick-app-storage", "entity:app-runtime"])

    # Mac recovery after install is install/boot, not manual.
    if ("macbook" in qt or "mac" in qt) and ("recovery" in qt or "efi" in qt or "boot" in qt) and ("install" in qt or "after" in qt):
        _score(candidates, "install_boot_question", 28.0, ["gate:quick-mac-install", "entity:install-boot"])

    # Bootable USB natural wording.
    if ("bootable" in qt and "usb" in qt and ("zimaos" in qt or "zima" in qt)) or ("create" in qt and "usb" in qt and ("zimaos" in qt or "zima" in qt)):
        _score(candidates, "manual_knowledge_question", 28.0, ["gate:quick-manual-usb", "source:zimaos-docs"])


    # Router v1.6.4 natural forum wording gates.
    # Based on public-release router-quality-test-v2 failures.
    # This handles short human wording, aliases, and safety phrasing.

    # Natural manual aliases.
    if (
        ("usb" in qt and ("installer" in qt or "install" in qt or "make" in qt) and ("zima" in qt or "zimaos" in qt))
        or ("network" in qt and "id" in qt and ("find" in qt or "where" in qt))
        or ("ssh" in qt and ("turn" in qt or "enable" in qt or "open" in qt or "on" in qt))
        or (("migrate" in qt or "migration" in qt) and ("data" in qt or "files" in qt))
        or ("rsync" in qt and ("clone" in qt or "backup" in qt))
    ):
        _score(candidates, "manual_knowledge_question", 26.0, ["gate:natural-manual-alias", "source:zimaos-docs"])

    # Natural short problem wording.
    if ("slow" in qt or "sluggish" in qt or "laggy" in qt) and ("zima" in qt or "zimaos" in qt or "system" in qt or "my" in qt):
        _score(candidates, "network_connectivity_question", 25.0, ["gate:natural-problem", "entity:slow-system"])

    if (
        ("app" in qt and ("cannot" in qt or "cant" in qt or "can't" in qt) and ("files" in qt or "file" in qt or "photos" in qt or "media" in qt))
        or (("qbit" in qt or "qbittorrent" in qt) and ("stuck" in qt or "download" in qt or "downloading" in qt))
    ):
        _score(candidates, "app_runtime_diag_question", 25.0, ["gate:natural-app-problem", "entity:app-runtime"])

    # Plain-English app open / tile / reachability wording.
    # Examples: "why plex not open", "jellyfin not opening", "cannot open immich",
    # "home assistant unreachable", "app tile not opening", "service not reachable".
    app_open_words = {"open", "opening", "load", "loading", "reachable", "unreachable", "access", "connect", "connecting"}
    # Route named apps and app/tile wording to app runtime.
    # Generic "service not reachable" without an app name should stay network/firewall.
    app_subject = has_app or {"app", "apps", "tile", "tiles"} & qt
    app_problem = has_issue or bool(app_open_words & qt) or {"down", "offline"} & qt

    if app_subject and app_problem:
        _score(candidates, "app_runtime_diag_question", 220.0, ["gate:natural-app-open", "entity:app-runtime"])
        _score(candidates, "network_exposure_question", 150.0, ["gate:natural-app-open-secondary", "entity:network-reachability"])

    # Permission wording must beat general SMB share route.
    if ("permission" in qt or "permissions" in qt or "denied" in qt) and ("smb" in qt or "samba" in qt or "share" in qt or "windows" in qt):
        _score(candidates, "permissions_ownership_question", 26.0, ["gate:natural-permission", "entity:permissions"])

    # Disk health wording must beat inventory when the word health is present.
    if ("health" in qt or "healthy" in qt) and ("disk" in qt or "disks" in qt or "drive" in qt or "drives" in qt):
        _score(candidates, "disk_health_question", 26.0, ["gate:natural-disk-health", "entity:disk-health"])

    # Safety phrasing without should/can.
    if ("docker" in qt and "prune" in qt and ("safe" in qt or "okay" in qt or "ok" in qt)):
        _score(candidates, "container_command_question", 26.0, ["gate:natural-safety", "entity:docker-prune"])

    if ("wipe" in qt or "erase" in qt or "format" in qt) and ("drive" in qt or "disk" in qt or "sda" in qt or "sdb" in qt):
        _score(candidates, "disk_command_question", 26.0, ["gate:natural-safety", "entity:disk-wipe"])


    # Router v1.6.3 scorecard correction gates.
    # These are based on public-release router-quality-test-v1 failures.

    safety_intent = bool(
        {"should", "can"} & qt
        and {"delete", "format", "prune", "repair", "expose"} & qt
    )

    # Safety gates must win early.
    if safety_intent and ("media" in qt or "/media" in ql or "folders" in qt):
        _score(candidates, "storage_mount_question", 24.0, ["gate:safety", "entity:storage-mounts"])
    if safety_intent and ("docker" in qt or "prune" in qt or "container" in qt or "containers" in qt):
        _score(candidates, "container_command_question", 24.0, ["gate:safety", "entity:docker-command"])
    if safety_intent and ("format" in qt or "disk" in qt or "drive" in qt):
        _score(candidates, "disk_command_question", 24.0, ["gate:safety", "entity:disk-command"])
    if safety_intent and ({"snapraid", "mergerfs", "parity", "pool", "protected", "protection"} & qt):
        _score(candidates, "snapraid_question", 24.0, ["gate:safety", "entity:snapraid-mergerfs"])

    # Protection question.
    if ("protected" in qt or "protection" in qt) and ("system" in qt or "my" in qt):
        _score(candidates, "snapraid_question", 23.0, ["gate:protection", "entity:snapraid-mergerfs"])

    # Disk inventory and disk health must beat practical command routing when wording asks for information.
    if ("inventory" in qt or ("show" in qt and ("disk" in qt or "disks" in qt))):
        _score(candidates, "disk_inventory_question", 23.0, ["gate:inventory", "entity:disk"])
    if ("healthy" in qt or "health" in qt) and ("disk" in qt or "disks" in qt or "drive" in qt or "drives" in qt):
        _score(candidates, "disk_health_question", 23.0, ["gate:health", "entity:disk-health"])

    # Failed systemd unit explain.
    if ("failed" in qt and ("unit" in qt or "systemd" in qt or "service" in qt)):
        _score(candidates, "failed_unit_question", 23.0, ["gate:evidence-explain", "entity:failed-unit"])

    service_execution_intent = bool(
        (
            {"helper", "helpers", "watchdog", "watchdogs"} & qt
            and {
                "failed", "failing", "degraded", "missing", "absent",
                "primary", "related", "outage", "recovered", "historical",
            } & qt
        )
        or (
            {"executable", "executables", "execstart", "script", "scripts", "exec"} & qt
            and {"missing", "absent", "broken", "failed", "failing", "permission", "permissions", "203"} & qt
        )
        or (
            {"executable", "executables", "execstart", "script", "scripts"} & qt
            and any(phrase in ql for phrase in (
                "not found", "cannot be found", "can't be found",
                "cannot locate", "can't locate",
            ))
        )
        or ("203" in qt and ("exec" in qt or "systemd" in qt or "service" in qt))
    )
    if service_execution_intent:
        _score(
            candidates,
            "failed_unit_question",
            28.0,
            ["gate:service-execution", "entity:failed-helper-executable"],
        )

    rauc_action_intent = bool(
        {"safe", "safety", "rollback", "reinstall", "mark", "switch", "change"} & qt
    )
    rauc_slot_intent = bool(
        "rauc" in qt
        or (
            {"slot", "slots"} & qt
            and (
                {"update", "boot", "booted", "activated", "rootfs", "kernel"} & qt
                or (
                    {
                        "active", "inactive", "good", "bad", "missing",
                        "present", "health", "healthy", "status",
                    } & qt
                    and {"zimaos", "os"} & qt
                )
            )
        )
    )
    if rauc_slot_intent and not rauc_action_intent:
        _score(
            candidates,
            "zimaos_regression_question",
            34.0,
            ["gate:rauc-slot-status", "entity:rauc-slots"],
        )

    # General slow ZimaOS diagnostic.
    if ("slow" in qt or "sluggish" in qt or "lag" in qt) and ("zimaos" in qt or "system" in qt):
        _score(candidates, "network_connectivity_question", 20.0, ["gate:general-diagnostic", "entity:slow-system"])

    # Install cannot find disk must be install/boot before add-drive planning.
    if ("install" in qt or "installer" in qt) and ("cannot" in qt or "can't" in qt or "no" in qt or "find" in qt) and ("disk" in qt or "drive" in qt):
        _score(candidates, "install_boot_question", 24.0, ["gate:install-disk-detection", "entity:install-boot"])


    # Router v2 hard gates.
    # These decide the main intent before the broad diagnostic scoring below.
    command_intent = bool(
        {"command", "commands", "cmd", "terminal", "cli"} & qt
        or ql.startswith("command to ")
        or ql.startswith("commands to ")
    )

    explain_intent = bool(
        {"explain", "why", "what"} & qt
        or ql.startswith("explain ")
        or ql.startswith("why ")
        or ql.startswith("what ")
    )

    manual_match = _best_manual_index_match(question)
    diagnostic_intent = bool(DIAGNOSTIC_PROBLEM_WORDS & qt)

    # Gate 1: command questions.
    if command_intent and (has_network or "network" in ql or "dns" in ql or "gateway" in ql or "ping" in ql):
        _score(candidates, "network_command_question", 20.0, ["gate:command", "entity:network"])
    elif command_intent and (has_disk or "disk" in ql or "disks" in ql or "drive" in ql or "drives" in ql or "smart" in ql):
        _score(candidates, "disk_command_question", 20.0, ["gate:command", "entity:disk"])
    elif command_intent and ("docker" in ql or "container" in ql or "containers" in ql):
        _score(candidates, "container_command_question", 20.0, ["gate:command", "entity:container"])
    elif command_intent:
        _score(candidates, "system_command_question", 16.0, ["gate:command", "entity:system"])

    # Gate 2: explain existing same-report evidence.
    if explain_intent and ("crc" in qt or "errors" in qt) and ("sda" in qt or has_disk):
        _score(candidates, "crc_question", 20.0, ["gate:evidence-explain", "entity:disk-crc"])
    if explain_intent and ("filesystem" in qt or "usage" in qt or "full" in qt or "100" in qt):
        _score(candidates, "usage_question", 19.0, ["gate:evidence-explain", "entity:filesystem-usage"])
    if explain_intent and ("container" in qt or "containers" in qt or "exited" in qt):
        _score(candidates, "exited_question", 19.0, ["gate:evidence-explain", "entity:container-state"])

    # Gate 3: practical disk check questions.
    if not command_intent and ("check" in qt or "show" in qt or "list" in qt) and (has_disk or "disk" in ql or "disks" in ql or "drive" in ql):
        _score(candidates, "disk_command_question", 18.0, ["gate:practical-check", "entity:disk"])

    # Gate 4: official manual document match.
    # Strong document matches win unless the wording clearly says there is a fault.
    if manual_match.get("score", 0) >= 45 and not diagnostic_intent:
        _score(candidates, "manual_knowledge_question", 17.5, [
            "gate:manual-index",
            "source:zimaos-docs",
            "match:" + manual_match.get("title", ""),
        ])
    elif manual_match.get("score", 0) >= 28 and not diagnostic_intent and {"build", "create", "setup", "set", "establish", "install", "enable", "migrate", "migration"} & qt:
        _score(candidates, "manual_knowledge_question", 16.5, [
            "gate:manual-action",
            "source:zimaos-docs",
            "match:" + manual_match.get("title", ""),
        ])


    # Explicit high-risk forum intake first.
    storage_provisioning = bool(
        (has_raid or has_disk or "storage" in qt)
        and {"add", "new", "cannot", "cant", "can't", "how", "create", "expand", "extend"} & qt
        and {"drive", "drives", "disk", "disks", "storage", "pool", "raid"} & qt
    )

    if storage_provisioning:
        _score(candidates, "raid_add_drive_question", 9.7, ["intent:diagnose", "entity:add-drive-raid"])
    elif has_raid and ("add" in qt or "newb" in qt or "cannot" in qt or "how" in qt):
        _score(candidates, "raid_add_drive_question", 9.7, ["intent:diagnose", "entity:add-drive-raid"])
    docker_daemon_problem = bool(
        has_docker and (
            {"daemon", "restart", "restarting", "service", "failed", "failure"} & qt
        )
    )

    if docker_daemon_problem:
        _score(candidates, "docker_daemon_question", 9.7, ["intent:diagnose", "entity:docker-daemon"])
    if _contains_phrase(qn, ["read only", "read-only", "readonly"]):
        _score(candidates, "read_only_storage_question", 9.7, ["intent:diagnose", "entity:read-only-storage"])
    if _contains_phrase(qn, ["macbook", "no devices found"]) or ("install" in qt and ("boot" in qt or "efi" in qt)):
        _score(candidates, "install_boot_question", 9.7, ["intent:diagnose", "entity:install-boot"])

    # App path / media-library questions must use path evidence before generic runtime diagnostics.
    # Example: Immich/Jellyfin/Nextcloud cannot see photos/media after a ZimaOS path change.
    try:
        from brain.layers.media_app_verified_guides import detect_app
        path_app_detected = detect_app(question)
    except Exception:
        path_app_detected = ""

    app_path_words = [
        "path", "paths", "photo", "photos", "upload", "uploads",
        "library", "media", "folder", "folders", "mount", "mounted",
        "bind", "bind mount", "external library", "cannot see", "can't see",
        "cant see", "not detecting", "not detected", "after zimaos",
        "/media", "/data", "/usr/src/app/upload"
    ]

    app_path_profiles = {
        "immich", "jellyfin", "nextcloud", "plex", "emby",
        "qbittorrent", "radarr", "sonarr", "sabnzbd"
    }

    if path_app_detected in app_path_profiles and any(w in ql for w in app_path_words):
        _score(candidates, "app_storage_path_question", 130.0, ["gate:app-path-hard-route", "entity:app-storage-path", f"profile:{path_app_detected}"])
        _score(candidates, "docker_bind_mount_question", 125.0, ["gate:app-path-bind-mount-route", "entity:docker-bind", f"profile:{path_app_detected}"])






    # Generic app install guard.
    # "how to install MariaDB/Pi-hole/Nextcloud/etc" must not route to OS install/boot diagnostics.
    app_install_words = ["how to install", "install", "setup", "set up", "configure"]
    os_install_words = [
        "zimaos installer", "install zimaos", "reinstall zimaos", "bootable usb",
        "usb installer", "efi", "boot picker", "boot menu", "macbook", "recovery",
        "no devices found", "install device", "boot from usb"
    ]

    if any(w in ql for w in app_install_words) and not any(w in ql for w in os_install_words):
        try:
            from brain.layers.media_app_verified_guides import detect_app
            generic_app_detected = detect_app(question)
        except Exception:
            generic_app_detected = ""

        if generic_app_detected:
            _score(candidates, "media_app_verified_guides_question", 120.0, ["gate:app-identity-hard-route", "entity:app", f"profile:{generic_app_detected}"])
        elif "zimaos" not in ql and "boot" not in ql and "installer" not in ql:
            _score(candidates, "media_app_verified_guides_question", 40.0, ["gate:generic-app-install-not-os-install", "entity:generic-app"])

    # Hard gate for supported app install/setup questions.
    # These should use the verified install guide, not the older generic app setup layer.
    try:
        from brain.layers.media_app_verified_guides import detect_app
        hard_app_guide_detected = detect_app(question)
    except Exception:
        hard_app_guide_detected = ""

    hard_app_guide_words = [
        "install", "setup", "set up", "configure", "how to",
        "external library", "library scan", "cannot see", "can't see", "cant see",
        "api key", "connect", "connection", "download path", "media folder",
        "transcoding", "hardware transcoding", "vaapi", "nvidia"
    ]

    hard_app_store_words = [
        "app store", "third party", "third-party", "which store",
        "risk", "risks", "docker socket", "host network", "privileged"
    ]

    if hard_app_guide_detected and any(w in ql for w in hard_app_guide_words) and not any(w in ql for w in hard_app_store_words):
        _score(candidates, "media_app_verified_guides_question", 80.0, ["gate:app-verified-guide-hard-install", "entity:app"])

    # Hard priority: explicit official manual/docs questions must use the Manual Knowledge Engine.
    # This prevents app-store/app-install routing from stealing official ZimaOS/CasaOS documentation questions.
    if (
        ("zimaos" in qt or "casaos" in qt)
        and ("official" in qt or "manual" in qt or "docs" in qt or "documentation" in qt)
    ):
        _score(candidates, "manual_knowledge_question", 170.0, ["gate:official-manual-hard-route", "source:zimaos-docs"])


    # Third-party app-store index questions.
    # This should catch app-store/risk/source questions and "can I install X" before generic setup guidance.
    app_store_words = [
        "app store", "third party", "third-party", "store", "source",
        "risk", "risks", "docker socket", "host network", "privileged",
        "which store", "can i install", "is it in"
    ]

    try:
        from brain.layers.third_party_app_store_index import search_apps
        app_store_matches = search_apps(question, limit=3)
    except Exception:
        app_store_matches = []

    if app_store_matches:
        app_store_intent = any(w in ql for w in app_store_words)

        os_platform_question = (
            ("zimaos" in qt and {"install", "installation", "installer", "upgrade", "update", "troubleshooting", "guide", "safely"} & qt)
            or ("casaos" in qt and ("proxmox" in qt or "ubuntu" in qt or "docker ce" in ql or "installer" in qt))
            or (("move" in qt or "migrate" in qt or "migration" in qt) and "casaos" in qt and "zimaos" in qt)
        )

        install_setup_intent = (
            any(w in ql for w in app_install_words)
            and not any(w in ql for w in os_install_words)
            and not os_platform_question
        )

        try:
            from brain.layers.media_app_verified_guides import detect_app
            dedicated_verified_app = detect_app(question)
        except Exception:
            dedicated_verified_app = ""

        # Dedicated verified install guides win for known core apps.
        # Third-party app-store index wins for app-store/source/risk questions,
        # or for install/setup questions where no dedicated profile exists.
        if dedicated_verified_app and install_setup_intent and not app_store_intent:
            _score(candidates, "media_app_verified_guides_question", 120.0, ["gate:verified-app-beats-third-party-index", "entity:app", f"profile:{dedicated_verified_app}"])
        elif app_store_intent:
            _score(candidates, "third_party_app_store_question", 90.0, ["gate:third-party-app-store-index", "source:app-store-index", "intent:app-store-source-risk"])
        elif install_setup_intent and not dedicated_verified_app:
            _score(candidates, "third_party_app_store_question", 90.0, ["gate:third-party-app-store-index", "source:app-store-index", "priority:app-store-match-before-generic-install"])


    # Generic unknown/unverified app questions.
    # Do not create one-off profiles for every odd app.
    # Route to generic app guidance so the answer can say not verified / not confirmed in app store.
    unknown_app_help = (
        ("trying to get" in ql and "work" in ql)
        or ("does" in qt and "work" in qt and ("app" in qt or "zimaos" in qt))
        or ("repo" in qt and ("find" in qt or "has" in qt or "app" in qt))
        or ("not in app store" in ql)
        or ("is it in the app store" in ql)
        or ("can i install" in ql and not ("zimaos" in qt and ("install" in qt or "upgrade" in qt)))
    )
    if unknown_app_help:
        _score(candidates, "media_app_verified_guides_question", 82.0, ["gate:generic-unverified-app", "entity:unknown-app"])


    # Media app verified install/integration guides.
    # This layer handles Immich, Jellyfin, Jellyseerr/Seerr, and JellyBridge in the correct order:
    # storage -> container -> bind mounts -> permissions -> network -> logs -> integration.
    # Hard priority: Docker bind-mount questions must beat general host storage mount answers.
    if (
        ({"docker", "container", "containers"} & qt)
        and ({"bind", "mount", "mounts", "mounted"} & qt)
        and ("/media" in ql or "media" in qt or "path" in qt or "paths" in qt)
    ):
        _score(candidates, "docker_bind_mount_question", 145.0, ["gate:docker-bind-hard-route", "entity:docker-bind"])

    # Hard priority: permission denied on AppData/Docker paths must not route to weak manual knowledge.
    if (
        {"permission", "permissions", "denied", "ownership", "owner", "chown", "chmod", "uid", "gid"} & qt
        and ("appdata" in qt or "/data/appdata" in ql or "docker" in qt or has_app)
    ):
        _score(candidates, "permissions_ownership_question", 145.0, ["gate:permission-hard-route", "entity:permissions"])

    # Hard priority: ZimaBrain self-audit / own privilege questions are network/security risk questions.
    if (
        ("zimabrain" in ql or "zima brain" in ql or "itself" in qt or "own" in qt or "self" in qt)
        and ({"privileged", "privilege", "privileges", "elevated", "root", "risk", "security", "docker.sock", "dockersock"} & qt or "docker socket" in ql)
    ):
        _score(candidates, "network_exposure_question", 190.0, ["gate:self-audit-hard-route", "entity:self-security"])

    # Hard priority: firewall / ZFW / LAN exposure questions are network/security risk questions.
    if (
        {"zfw", "firewall", "iptables", "docker-user", "blocked", "blocking", "protecting", "protect", "enforcing", "enforce", "reachable", "lan"} & qt
        or "docker-user" in ql
        or "docker user" in ql
        or "lan access" in ql
        or "safe-apply" in ql
    ):
        _score(candidates, "network_exposure_question", 180.0, ["gate:zfw-firewall-hard-route", "entity:network-exposure"])

    # Hard priority: public exposure questions are network/security risk questions.
    if (
        {"expose", "exposed", "public", "publicly", "internet", "wan"} & qt
        and ("portainer" in qt or "agent" in qt or "docker" in qt or "docker.sock" in ql or "dashboard" in qt)
    ):
        _score(candidates, "network_exposure_question", 145.0, ["gate:public-exposure-hard-route", "entity:network-exposure"])

    # Hard priority: command requests mentioning Docker containers/mounts/ports should prefer container verification commands.
    if (
        {"command", "commands", "cmd", "terminal", "cli"} & qt
        and ({"docker", "container", "containers"} & qt)
        and ({"mount", "mounts", "ports", "port", "bind"} & qt)
    ):
        _score(candidates, "container_command_question", 145.0, ["gate:docker-command-hard-route", "entity:container-commands"])

    try:
        from brain.layers.media_app_verified_guides import detect_app
        media_app_detected = detect_app(question)
    except Exception:
        media_app_detected = ""

    media_app_words = [
        "install", "setup", "set up", "configure", "external library",
        "library scan", "cannot see", "can't see", "cant see",
        "api key", "connect", "connection", "jellybridge", "jellyseerr", "seerr",
        "media folder", "transcoding", "hardware transcoding", "vaapi", "nvidia"
    ]

    media_app_store_words = [
        "app store", "third party", "third-party", "which store",
        "risk", "risks", "docker socket", "host network", "privileged"
    ]

    if media_app_detected and any(w in ql for w in media_app_words) and not any(w in ql for w in media_app_store_words):
        _score(candidates, "media_app_verified_guides_question", 35.0, ["gate:media-app-verified-guide", "entity:media-app"])

    # Known Zima app setup/install questions must beat OS install/boot routing.
    q = (question or "").lower()
    known_app_terms = [
        "wazuh", "netdata", "netdata cloud", "portainer",
        "home assistant", "home-assistant", "homeassistant",
        "borg web ui", "borg-web-ui", "borg ui",
        "tailscale", "cloudflare", "cloudflared", "cloudflare tunnel", "clouflare", "cloudfare", "cloudflair", "clodflare",
        "immich", "jellyfin", "qbittorrent", "nextcloud",
        "radarr", "sonarr", "sabnzbd", "ollama", "open webui", "open-webui"
    ]
    app_setup_words = ["install", "setup", "set up", "configure", "add app", "how do i"]
    if any(t in q for t in known_app_terms) and any(w in q for w in app_setup_words):
        _score(candidates, "app_setup_playbook_question", 34.0, ["gate:known-zima-app-setup", "entity:app"])

    # Multiple-interface and routing-conflict diagnostics.
    if (
        {"interface", "interfaces", "nic", "nics"} & qt
        and {"route", "routes", "routing", "gateway"} & qt
        and {"conflict", "conflicts", "multiple", "several"} & qt
    ):
        _score(
            candidates,
            "network_connectivity_question",
            31.0,
            ["gate:multi-interface-routing", "entity:network-routing"],
        )

    # Additional diagnostic layers.
    # Real forum hard routes from search/referral data.
    # These are common user phrases that must not fall through to weak fallback or app-store index.
    if ("casaos.local" in q or "local" in qt and "ip" in qt and ("works" in qt or "address" in qt)):
        _score(candidates, "network_connectivity_question", 145.0, ["gate:forum-casaos-local-dns", "entity:network-dns-local"])

    if ("failed to load apps" in q or ("load" in qt and "apps" in qt and ("failed" in qt or "refresh" in qt))):
        _score(candidates, "app_runtime_diag_question", 145.0, ["gate:forum-failed-load-apps", "entity:zimaos-app-runtime"])

    if (("move" in qt or "migrate" in qt or "migration" in qt) and "casaos" in qt and "zimaos" in qt):
        _score(candidates, "manual_knowledge_question", 145.0, ["gate:forum-casaos-to-zimaos", "source:zimaos-docs"])

    if ("docker ce" in q and "not found" in q and "ubuntu" in qt and "casaos" in qt):
        _score(candidates, "install_boot_question", 145.0, ["gate:forum-casaos-installer-docker-ce", "entity:installer-dependency"])

    if (("qbittorrent" in qt or "qbit" in qt) and ("radarr" in qt or "sonarr" in qt) and ("download" in qt or "downloads" in qt or "showing" in qt or "not" in qt)):
        _score(candidates, "app_storage_path_question", 146.0, ["gate:forum-download-stack-paths", "entity:download-stack"])

    if {"macbook", "efi", "installer", "install", "boot", "recovery"} & qt and not ("version" in qt):
        _score(candidates, "install_boot_question", 9.2, ["intent:diagnose", "entity:install-boot"])

    if {"share", "shares", "smb", "samba", "windows"} & qt:
        _score(candidates, "smb_shares_question", 9.3, ["intent:diagnose", "entity:smb-shares"])

    if {"permission", "permissions", "denied", "ownership", "owner", "chown", "chmod", "uid", "gid"} & qt:
        _score(candidates, "permissions_ownership_question", 9.3, ["intent:diagnose", "entity:permissions"])

    if {"internet", "connection", "connectivity", "ping", "dns", "gateway", "offline"} & qt:
        _score(candidates, "network_connectivity_question", 9.2, ["intent:diagnose", "entity:network-connectivity"])

    if has_zima and {"update", "upgrade", "rollback", "reinstall", "safe", "safety"} & qt:
        _score(candidates, "zimaos_update_safety_question", 9.3, ["intent:safety", "entity:zimaos-update"])

    if {"log", "logs", "journal", "journalctl", "error", "traceback", "attached", "output"} & qt:
        _score(candidates, "log_intake_question", 8.8, ["intent:intake", "entity:logs"])

    if {"repair", "fix", "plan", "next"} & qt and {"what", "should", "do", "now", "next"} & qt:
        _score(candidates, "repair_planner_question", 7.5, ["intent:plan", "entity:repair"])

    # ZimaOS version/regression.
    if "zimaos" in qt and ("version" in qt or "kernel" in qt):
        _score(candidates, "zimaos_regression_question", 9.5, ["intent:version", "entity:zimaos"])
    elif has_zima and {"update", "upgrade", "rollback", "regression", "rauc", "kernel"} & qt:
        _score(candidates, "zimaos_regression_question", 8.5, ["intent:verify", "entity:zimaos-update"])

    # Disk inventory vs mount vs health.
    if has_disk and (has_list or has_size):
        _score(candidates, "disk_inventory_question", 9.0, ["intent:list", "entity:disk"])
    if has_disk and has_health:
        _score(candidates, "disk_health_question", 8.5, ["intent:diagnose", "entity:disk-health"])
    if has_mount or ("where" in qt and has_disk):
        _score(candidates, "storage_mount_question", 8.0, ["intent:locate", "entity:mount/storage"])

    # Storage capacity without explicit disk.
    if "storage" in qt and (has_list or has_size):
        _score(candidates, "disk_inventory_question", 8.0, ["intent:list", "entity:storage"])

    # Apps.
    app_media_problem = bool(has_app and (
        {"path", "paths", "storage", "library", "download", "downloads", "media", "movies", "photos", "files"} & qt
        or {"missing", "showing", "visible", "found", "import", "importing", "scan", "scanning", "downloading", "stalled"} & qt
        or ({"no", "not"} & qt and {"movies", "photos", "files", "library", "download", "downloads", "downloading"} & qt)
    ))

    if has_app and has_setup:
        _score(candidates, "app_setup_playbook_question", 9.0, ["intent:setup/version", "entity:app"])
    elif app_media_problem:
        _score(candidates, "app_runtime_diag_question", 9.1, ["intent:diagnose", "entity:app-runtime"])


    # Official ZimaOS manual scoring is handled by Router v2 hard gates above.

    # Docker/container.
    if has_docker and has_command:
        _score(candidates, "container_command_question", 7.5, ["intent:command", "entity:docker"])
    elif has_docker and ({"ps", "status", "running", "containers", "container"} & qt):
        _score(candidates, "container_question", 7.5, ["intent:list/status", "entity:container"])
    elif has_docker and ({"bind", "volume", "volumes", "mapping", "mount"} & qt):
        _score(candidates, "docker_bind_mount_question", 8.0, ["intent:verify", "entity:docker-bind"])

    container_state_terms = {
        "stopped", "unhealthy", "restarting"
    } & qt

    if (
        {"container", "containers"} & qt
        and len(container_state_terms) >= 2
    ):
        _score(
            candidates,
            "container_question",
            30.0,
            ["gate:combined-container-state", "entity:container-state"],
        )

    if {"exited", "stopped", "dead"} & qt:
        _score(candidates, "exited_question", 8.5, ["intent:diagnose", "entity:container-state"])

    # Network.
    if has_network and has_command:
        _score(candidates, "network_command_question", 7.5, ["intent:command", "entity:network"])
    elif has_network:
        _score(candidates, "network_exposure_question", 8.0, ["intent:verify", "entity:network-exposure"])

    # Other diagnostic domains.
    if has_backup:
        _score(candidates, "backup_borg_question", 8.0, ["intent:verify", "entity:backup"])
    if has_gpu:
        _score(candidates, "gpu_ai_runtime_question", 8.0, ["intent:verify", "entity:gpu-ai"])
    if has_compare:
        _score(candidates, "report_comparison_question", 8.0, ["intent:compare", "entity:report"])
    if has_raid and not candidates:
        _score(candidates, "snapraid_question", 7.5, ["intent:verify", "entity:raid/pool"])

    # Comprehensive whole-system health assessment.
    comprehensive_health_intent = (
        _contains_phrase(question, (
            "complete system-health assessment",
            "complete system health assessment",
            "complete health assessment",
            "system health assessment",
            "summarize the health",
            "summarise the health",
            "is my system healthy",
            "overall system health",
            "overall health",
            "health summary",
            "system summary",
            "full diagnosis",
            "full report",
        ))
        or (
            ("summarize" in qt or "summarise" in qt)
            and "health" in qt
            and ("system" in qt or "cube" in qt)
        )
    )
    if comprehensive_health_intent:
        _score(
            candidates,
            "comprehensive_health_question",
            30.0,
            ["gate:comprehensive-health", "entity:whole-system"],
        )

    # Generic dashboard health.
    if {"alert", "alerts", "wrong", "problem", "problems", "health", "status"} & qt and not candidates:
        _score(candidates, "dashboard_alert_question", 6.5, ["intent:overview", "entity:dashboard"])

    # Commands.
    if has_command and has_disk:
        _score(candidates, "disk_command_question", 6.5, ["intent:command", "entity:disk"])
    if has_command and "system" in qt:
        _score(candidates, "system_command_question", 6.5, ["intent:command", "entity:system"])

    candidates.sort(key=lambda x: x["score"], reverse=True)

    result = {flag: False for flag in ALL_FLAGS}

    best = candidates[0] if candidates else None
    second = candidates[1] if len(candidates) > 1 else None

    if best:
        result[best["flag"]] = True
        gap = best["score"] - (second["score"] if second else 0)
        confidence = min(0.99, max(0.35, (best["score"] / 10.0) + (gap / 12.0)))
    else:
        confidence = 0.0

    label_map = {
        "comprehensive_health_question": "comprehensive_health",
        "host_hardware_question": "host_hardware_metrics",
        "trend_history_question": "trend_history",
        "smart_health_question": "smart_health",
        "hardware_compatibility_question": "hardware_compatibility",
        "dashboard_alert_question": "dashboard_alerts",
        "failed_unit_question": "failed_units",
        "crc_question": "crc_errors",
        "usage_question": "filesystem_usage",
        "exited_question": "exited_containers",
        "container_question": "containers",
        "docker_daemon_question": "docker_daemon_diag",
        "disk_health_question": "disk_health",
        "storage_mount_question": "storage_mounts",
        "docker_bind_mount_question": "docker_bind_mounts",
        "container_bind_mount_permission_question": "container_bind_mount_permissions",
        "app_storage_path_question": "app_storage_paths",
        "app_runtime_diag_question": "app_runtime_diag",
        "app_setup_playbook_question": "app_setup_playbook",
        "third_party_app_store_question": "third_party_app_store_index",
        "media_app_verified_guides_question": "media_app_verified_guides",
        "manual_knowledge_question": "manual_knowledge",
        "backup_borg_question": "backup_borg",
        "smart_trend_question": "smart_trend",
        "network_exposure_question": "network_exposure",
        "zimaos_regression_question": "zimaos_regression",
        "gpu_ai_runtime_question": "gpu_ai_runtime",
        "report_comparison_question": "report_comparison",
        "disk_inventory_question": "disk_inventory",
        "forum_issue_intake_question": "forum_issue_intake",
        "read_only_storage_question": "read_only_storage_diag",
        "install_boot_question": "install_boot_diag",
        "raid_add_drive_question": "raid_add_drive_diag",
        "network_connectivity_question": "network_connectivity_diag",
        "smb_shares_question": "smb_shares_diag",
        "permissions_ownership_question": "permissions_ownership_diag",
        "zimaos_update_safety_question": "zimaos_update_safety",
        "log_intake_question": "log_intake_diag",
        "repair_planner_question": "repair_planner",
        "snapraid_question": "snapraid_mergerfs",
        "disk_command_question": "disk_commands",
        "container_command_question": "container_commands",
        "system_command_question": "system_commands",
        "network_command_question": "network_commands",
    }

    result["_intent"] = label_map.get(best["flag"], "unknown") if best else "unknown"
    result["_intent_flag"] = best["flag"] if best else None
    result["_confidence"] = round(confidence, 2)
    result["_matched_terms"] = best["matched"] if best else []
    result["_candidates"] = [
        {
            "flag": c["flag"],
            "intent": label_map.get(c["flag"], c["flag"]),
            "score": round(c["score"], 3),
            "matched": c["matched"],
        }
        for c in candidates[:3]
    ]
    result["_needs_clarification"] = (not best) or confidence < 0.45

    return result
