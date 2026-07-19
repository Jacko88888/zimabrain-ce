import re


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
