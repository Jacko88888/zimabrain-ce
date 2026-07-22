import re

try:
    from brain.app_aliases import APP_ALIASES
except Exception:
    from app.brain.app_aliases import APP_ALIASES


APP_TOKENS = set(APP_ALIASES)
for _aliases in APP_ALIASES.values():
    APP_TOKENS.update(
        alias for alias in _aliases
        if re.fullmatch(r"[a-z0-9]+", alias)
    )


def _tokens(question):
    return set(re.findall(r"[a-z0-9]+", str(question or "").lower()))


def _result(domain="unknown", task="unknown", entity="unknown",
            handler="", route_flag="", route_intent="unknown"):
    return {
        "domain": domain,
        "task": task,
        "entity": entity,
        "handler": handler,
        "route_flag": route_flag,
        "route_intent": route_intent,
        "memory_key": f"{domain}:{task}:{entity}",
    }


def classify(question):
    q = str(question or "").lower()
    tokens = _tokens(question)

    if {"fictional", "imaginary", "nonexistent", "madeup"} & tokens:
        return _result()

    rauc_action_question = bool(
        tokens & {"safe", "safety", "rollback", "reinstall", "mark", "switch", "change"}
    )
    rauc_slot_question = bool(
        "rauc" in tokens
        or (
            tokens & {"slot", "slots"}
            and (
                tokens & {"update", "boot", "booted", "activated", "rootfs", "kernel"}
                or (
                    tokens & {
                        "active", "inactive", "good", "bad", "missing",
                        "present", "health", "healthy", "status",
                    }
                    and tokens & {"zimaos", "os"}
                )
            )
        )
    )
    if rauc_slot_question and rauc_action_question:
        return _result(
            "system", "safety", "rauc",
            "zimaos_update_safety",
            "zimaos_update_safety_question",
            "zimaos_update_safety",
        )
    if rauc_slot_question:
        return _result(
            "system", "status", "rauc",
            "zimaos_regression",
            "zimaos_regression_question",
            "zimaos_regression",
        )

    system_subjects = {
        "system", "machine", "host", "zimacube", "cube", "server"
    }
    overview_terms = {
        "overall", "whole", "entire", "complete", "full", "condition",
        "health", "healthy", "assessment", "attention"
    }
    security_terms = {
        "secure", "security", "adequately", "firewall", "audit", "exposure"
    }

    if (
        tokens & system_subjects
        and tokens & overview_terms
        and not tokens & security_terms
        and not tokens & {"update", "updated", "upgrade", "upgraded"}
    ):
        return _result(
            "system", "status", "overall",
            "comprehensive_health",
            "comprehensive_health_question",
            "comprehensive_health",
        )

    if tokens & {"memory", "ram", "swap"}:
        return _result(
            "performance", "status", "memory",
            "host_hardware",
            "host_hardware_question",
            "host_hardware_metrics",
        )

    disk_terms = {
        "disk", "disks", "drive", "drives", "smart", "nvme", "crc",
        "media", "shutdown", "shutdowns", "counter", "counters"
    }
    comparison_terms = {
        "increase", "increased", "rise", "rose", "rising", "worse",
        "worsening", "changed", "change", "trend", "compare", "since"
    }

    if tokens & disk_terms and tokens & comparison_terms:
        return _result(
            "storage", "compare", "smart-nvme",
            "trend_history",
            "trend_history_question",
            "trend_history",
        )

    update_terms = {"update", "updated", "upgrade", "upgraded", "zimaos", "os"}
    update_compare_terms = {
        "after", "changed", "change", "compare", "baseline", "since",
        "regression", "problems", "health"
    }
    safety_terms = {"safe", "safety", "rollback", "reinstall", "install"}

    if (
        tokens & update_terms
        and tokens & update_compare_terms
        and not tokens & safety_terms
        and not tokens & {"slow", "sluggish", "lag", "laggy"}
    ):
        return _result(
            "system", "compare", "update",
            "trend_history",
            "trend_history_question",
            "trend_history",
        )

    if "tailscale" in tokens and tokens & {
        "working", "functioning", "correctly", "status", "up",
        "connected", "connectivity", "tunnel"
    }:
        return _result(
            "network", "status", "tailscale",
            "network_connectivity",
            "network_connectivity_question",
            "network_connectivity_diag",
        )

    listener_subjects = {
        "service", "services", "process", "processes",
        "application", "applications", "app", "apps"
    }
    listener_terms = {
        "listen", "listening", "listener", "listeners",
        "port", "ports", "socket", "sockets"
    }

    if tokens & listener_subjects and tokens & listener_terms:
        return _result(
            "network", "status", "listeners",
            "network_connectivity",
            "network_connectivity_question",
            "network_connectivity_diag",
        )

    network_terms = {
        "dns", "resolver", "resolve", "gateway", "route", "routes",
        "routing", "interface", "interfaces"
    }
    network_change_terms = {
        "install", "installed", "configure", "configuration",
        "change", "changing", "before", "setup"
    }
    network_diagnostic_terms = {
        "working", "problem", "problems", "issue", "issues",
        "failed", "failing", "resolve", "reach", "active",
        "current", "conflict"
    }

    if (
        tokens & network_terms
        and (
            not tokens & network_change_terms
            or tokens & network_diagnostic_terms
        )
    ):
        return _result(
            "network", "status", "dns-routing",
            "network_connectivity",
            "network_connectivity_question",
            "network_connectivity_diag",
        )

    named_container = bool(tokens & {"container", "containers"})
    container_configuration_terms = {
        "misconfigured", "misconfiguration", "configuration",
        "configured", "privileged", "privilege", "security",
        "socket", "capability", "capabilities", "dangerous", "risky"
    }

    if (
        named_container
        and tokens & container_configuration_terms
        and not tokens & {
            "firewall", "audit", "exposure", "posture", "protected"
        }
    ):
        return _result(
            "containers", "assess", "configuration",
            "containers",
            "container_question",
            "containers",
        )

    container_states = {
        "running", "exited", "stopped", "restarting", "unhealthy",
        "healthy", "dead", "paused"
    }
    matched_container_states = tokens & container_states

    if named_container and len(matched_container_states) >= 2:
        return _result(
            "containers", "status", "all",
            "containers",
            "container_question",
            "containers",
        )

    if (
        named_container
        and matched_container_states & {"exited", "stopped", "dead"}
    ):
        return _result(
            "containers", "status", "inactive",
            "containers",
            "exited_question",
            "exited_containers",
        )

    if named_container and matched_container_states:
        return _result(
            "containers", "status", "all",
            "containers",
            "container_question",
            "containers",
        )

    container_permission_scope = bool(
        tokens & {"docker", "container", "containers", "volume", "volumes", "bind"}
        or tokens & {"app", "application"}
        or tokens & APP_TOKENS
    )
    storage_permission_scope = bool(
        tokens & {
            "storage", "filesystem", "drive", "disk", "usb", "media", "folder",
            "folders", "file", "files", "mount", "mounted", "volume", "volumes",
        }
    )
    write_permission_symptom = bool(
        tokens & {
            "permission", "permissions", "denied", "writable", "write", "writing",
            "create", "creating", "rename", "renaming", "delete", "deleting",
            "remove", "removing", "readonly", "ownership", "owner", "uid", "gid",
        }
        or "read-only" in q
        or "read only" in q
    )
    read_write_contrast = bool(
        "read" in tokens
        and tokens & {"write", "create", "rename", "delete", "remove", "move"}
    )
    explicit_storage_path = bool(
        re.search(r"/(?:data|media|mnt|srv)(?:/|\b)", q)
    )
    named_writer_match = re.search(
        r"\b([a-z0-9][a-z0-9_.-]{2,})\s+"
        r"(?:write|create|rename|delete|remove|move)\b",
        q,
    )
    named_writer = (
        named_writer_match.group(1) if named_writer_match else ""
    )
    explicit_named_storage_writer = bool(
        explicit_storage_path
        and named_writer
        and named_writer not in {
            "app", "application", "container", "docker", "host", "root",
            "system", "user", "users", "this", "that",
        }
    )
    if (
        (container_permission_scope or explicit_named_storage_writer)
        and storage_permission_scope
        and (write_permission_symptom or read_write_contrast)
    ):
        return _result(
            "containers", "diagnose", "bind-permissions",
            "container_bind_mount_permissions",
            "container_bind_mount_permission_question",
            "container_bind_mount_permissions",
        )

    read_only = (
        "readonly" in tokens
        or ("read" in tokens and "only" in tokens)
        or "read-only" in q
    )
    storage_scope = {
        "storage", "filesystem", "filesystems", "mount", "mounts",
        "data", "media", "disk", "drive"
    }
    if read_only and tokens & storage_scope:
        return _result(
            "storage", "status", "read-only",
            "read_only_storage",
            "read_only_storage_question",
            "read_only_storage_diag",
        )

    service_terms = {"service", "services", "unit", "units", "systemd"}
    failed_terms = {"failed", "failing", "degraded", "broken"}
    helper_terms = {
        "helper", "helpers", "watchdog", "watchdogs", "monitor", "monitors"
    }
    executable_terms = {
        "executable", "executables", "script", "scripts", "execstart", "exec"
    }
    execution_failure_terms = {
        "missing", "absent", "broken", "failed", "failing", "invalid",
        "permission", "permissions", "203"
    }
    primary_state_terms = {
        "primary", "related", "degraded", "outage", "active", "inactive",
        "running", "recovered", "historical"
    }

    if (
        (tokens & helper_terms and tokens & (failed_terms | primary_state_terms))
        or (tokens & executable_terms and tokens & execution_failure_terms)
        or (
            tokens & executable_terms
            and any(phrase in q for phrase in (
                "not found", "cannot be found", "can't be found",
                "cannot locate", "can't locate",
            ))
        )
        or ("203" in tokens and ("exec" in tokens or tokens & service_terms))
        or (
            tokens & helper_terms
            and tokens & {"file", "files", "executable", "executables"}
            and tokens & {"missing", "absent", "broken"}
        )
    ):
        execution_focus = bool(
            tokens & executable_terms
            or tokens & {"file", "files", "missing", "absent", "203"}
        )
        entity = "execution" if execution_focus else "helper-primary"
        return _result(
            "services", "diagnose", entity,
            "failed_units",
            "failed_unit_question",
            "failed_units",
        )

    if tokens & service_terms and tokens & failed_terms:
        return _result(
            "services", "status", "failed",
            "failed_units",
            "failed_unit_question",
            "failed_units",
        )

    snapraid_terms = {"snapraid", "mergerfs", "parity"}
    if tokens & snapraid_terms and tokens & {
        "protect", "protecting", "protected", "protection",
        "healthy", "health", "safe", "status"
    }:
        return _result(
            "storage", "status", "snapraid",
            "snapraid",
            "snapraid_question",
            "snapraid_mergerfs",
        )

    if tokens & security_terms:
        return _result(
            "security", "status", "posture",
            "network_exposure",
            "network_exposure_question",
            "network_exposure",
        )

    gpu_terms = {"gpu", "nvidia", "cuda", "transcoding", "acceleration"}
    if tokens & gpu_terms:
        return _result(
            "gpu", "status", "runtime",
            "gpu_runtime",
            "gpu_ai_runtime_question",
            "gpu_ai_runtime",
        )

    compatibility_terms = {
        "compatible", "compatibility", "supported", "support", "adapter",
        "card", "fit", "bifurcation", "passthrough"
    }
    hardware_terms = {
        "pcie", "nvme", "sata", "nic", "gpu", "hba", "usb",
        "raid", "zfs", "disk", "drive"
    }
    if tokens & compatibility_terms and tokens & hardware_terms:
        return _result(
            "hardware", "compatibility", "device",
            "hardware_compatibility",
            "hardware_compatibility_question",
            "hardware_compatibility",
        )

    if tokens & {"smart", "nvme"} and (
        tokens & {"health", "healthy", "failing", "failure", "warning"}
    ):
        return _result(
            "storage", "status", "smart-nvme",
            "smart_health",
            "smart_health_question",
            "smart_health",
        )

    return _result()
