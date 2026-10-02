import os
import re

from brain import health_memory


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


def is_host_restart_question(question):
    q = str(question or "").lower()
    tokens = set(re.findall(r"[a-z0-9]+", q))
    component_scope = bool(tokens & {
        "container", "containers", "docker", "compose", "service", "services",
        "application", "applications", "app", "apps", "process", "processes",
    })
    if component_scope:
        return False
    host_subject = any(
        word in q for word in (
            "nas", "host", "system", "server", "machine", "zimacube",
            "zima cube", "zimaboard", "zima board", "zimaos",
        )
    )
    reboot_focus = any(word in q for word in ("reboot", "rebooted", "boot again"))
    restart_focus = any(word in q for word in ("restart", "restarted"))
    incident_history = (
        "before the reboot" in q
        or "before reboot" in q
        or (host_subject and "became unresponsive" in q)
        or (host_subject and "become unresponsive" in q)
        or (
            ("cpu" in q or "processor" in q)
            and ("ram" in q or "memory" in q)
            and ("100" in q or "max" in q or "full" in q)
        )
    )
    return reboot_focus or (restart_focus and host_subject) or incident_history


def _short_boot(value):
    value = str(value or "")
    return value[:12] if value else "unknown"


def _rate(value):
    if value is None:
        return "not captured"
    value = float(value)
    units = ("B/s", "KiB/s", "MiB/s", "GiB/s")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GiB/s"


def _peak_line(label, sample, metric, suffix="%"):
    if not sample or sample.get(metric) is None:
        return f"- {label}: not captured before this reboot."
    return (
        f"- {label}: {float(sample[metric]):.1f}{suffix} at "
        f"`{sample.get('created_at', 'unknown')}`."
    )


def _top_processes(sample, field):
    if not sample:
        return []
    items = sample.get(field, []) or []
    result = []
    for item in items[:5]:
        command = str(item.get("command", "unknown") or "unknown")[:140]
        if field == "top_cpu":
            value = item.get("host_percent")
            label = f"{float(value):.1f}% of total host CPU" if value is not None else "CPU not measured"
        else:
            value = item.get("rss_mb")
            label = f"{float(value):.1f} MiB RSS" if value is not None else "memory not measured"
        result.append(f"- PID {item.get('pid', 'unknown')}: `{command}` — {label}.")
    return result


def answer(question, bundle):
    bundle = bundle if isinstance(bundle, dict) else {}
    evidence = bundle.get("same_report_evidence", {}) if isinstance(bundle, dict) else {}
    current_boot_id = str(evidence.get("boot_id", "") or "").strip()
    db_path = str(bundle.get("health_memory_db_path", TREND_DB_PATH) or TREND_DB_PATH)
    try:
        context = (
            health_memory.monitor_restart_context(db_path, current_boot_id)
            if os.path.exists(db_path)
            else {}
        )
    except Exception as error:
        context = {"read_error": str(error)[:300]}
    boot = context.get("boot_evidence", {}) or {}
    previous = context.get("previous", {}) or {}
    previous_boot_id = context.get("previous_boot_id", "") or ""
    reboot_verified = bool(
        current_boot_id and previous_boot_id and current_boot_id != previous_boot_id
    )
    journal_available = bool(boot.get("journal_available"))

    if reboot_verified:
        verification = "@@VERIFY:VERIFIED@@ ✅ VERIFIED FROM HOST BOOT AND LOCAL INCIDENT HISTORY"
        verification_detail = (
            f"- A host boot transition was recorded: `{_short_boot(previous_boot_id)}` "
            f"→ `{_short_boot(current_boot_id)}`."
        )
    elif boot or context.get("current_sample"):
        verification = "@@VERIFY:PARTIALLY VERIFIED@@ ⚠️ PARTIALLY VERIFIED"
        verification_detail = (
            "- Current host-boot evidence exists, but ZimaBrain does not have a "
            "comparable prior boot ID proving the reported reboot."
        )
    else:
        verification = "@@VERIFY:NOT VERIFIED@@ ❌ NOT VERIFIED FROM AVAILABLE HISTORY"
        verification_detail = "- No background host-boot record is available yet."

    if boot.get("kernel_panic"):
        cause = "Kernel-panic evidence was captured in the previous boot journal."
    elif boot.get("update_reboot"):
        cause = "The previous journal contains an explicit update-related reboot marker."
    elif boot.get("manual_reboot"):
        cause = "The previous journal contains an explicit manual reboot request marker."
    elif boot.get("clean_shutdown"):
        cause = (
            "An orderly shutdown/reboot sequence was captured, but the available "
            "evidence does not identify who or what initiated it."
        )
    elif boot.get("oom_before_reboot"):
        cause = (
            "An OOM event was captured before the reboot. The timing is relevant, "
            "but it does not by itself prove that OOM caused the reboot."
        )
    elif reboot_verified:
        cause = (
            "The NAS reboot was verified, but the available evidence cannot determine "
            "the exact cause."
        )
    else:
        cause = "The reported reboot and its cause cannot be verified from the available history."

    out = [
        "### ZimaBrain Answer",
        "",
        "## ❓ Question asked",
        f"### {str(question or '').strip()}",
        "",
        "#### Verification status",
        verification,
        verification_detail,
        "- Active layer: Host Restart and Incident History Layer",
        "- Layer files: `app/brain/layers/host_restart.py`, `app/brain/background_monitor.py`",
        "",
        "#### Direct answer / severity",
        f"- {cause}",
        "",
        "#### Reboot-cause evidence",
    ]

    if not journal_available:
        out.append(
            "- Previous-boot journal evidence was not available. ZimaBrain cannot "
            "retroactively distinguish power loss, a hard reset, a manual reboot, "
            "an update reboot, or a kernel failure without that evidence."
        )
        if context.get("read_error"):
            out.append(
                "- Local incident history could not be read: "
                f"`{context['read_error']}`"
            )
    else:
        out.extend([
            f"- Kernel panic marker: {'found' if boot.get('kernel_panic') else 'not found'}.",
            f"- Explicit update-triggered reboot marker: {'found' if boot.get('update_reboot') else 'not found'}.",
            f"- Explicit manual reboot marker: {'found' if boot.get('manual_reboot') else 'not found'}.",
            f"- Orderly shutdown/reboot sequence: {'found' if boot.get('clean_shutdown') else 'not found'}.",
            f"- OOM event before reboot: {'found' if boot.get('oom_before_reboot') else 'not found'}.",
        ])
        if boot.get("update_activity") and not boot.get("update_reboot"):
            out.append(
                "- Update activity was present in the previous journal, but no explicit "
                "evidence says that it triggered the reboot."
            )
        if boot.get("abrupt_shutdown_possible"):
            out.append(
                "- No orderly shutdown marker was captured. Abrupt power loss or a hard "
                "reset remains possible, but is not verified from absence alone."
            )

    details = boot.get("details", {}) or {}
    exact_lines = []
    for key in ("panic", "update_reboot", "manual_reboot", "clean_shutdown", "oom"):
        exact_lines.extend(details.get(key, []) or [])
    if exact_lines:
        out.extend(["", "#### Exact previous-boot markers"])
        for line in exact_lines[-8:]:
            safe_line = str(line).replace("`", "'")[:500]
            out.append(f"- `{safe_line}`")

    out.extend(["", "#### Pre-reboot performance window"])
    if not previous:
        out.append(
            "- No rolling samples exist for the previous boot. The new monitor cannot "
            "recover CPU, memory, process, disk-I/O, or container state that was never recorded."
        )
    else:
        out.append(
            f"- Analysed the latest {previous.get('sample_count', 0)} pre-reboot "
            "sample(s), from "
            f"`{previous.get('first_sample_at', 'unknown')}` to "
            f"`{previous.get('last_sample_at', 'unknown')}`."
        )
        out.append(_peak_line("Peak host CPU", previous.get("peak_cpu"), "cpu_percent"))
        out.append(_peak_line("Peak memory use", previous.get("peak_memory"), "memory_percent"))
        read_peak = previous.get("peak_disk_read") or {}
        write_peak = previous.get("peak_disk_write") or {}
        out.append(
            f"- Peak disk read rate: {_rate(read_peak.get('disk_read_bps'))}"
            f" at `{read_peak.get('created_at', 'unknown')}`."
        )
        out.append(
            f"- Peak disk write rate: {_rate(write_peak.get('disk_write_bps'))}"
            f" at `{write_peak.get('created_at', 'unknown')}`."
        )

        cpu_processes = _top_processes(previous.get("peak_cpu"), "top_cpu")
        memory_processes = _top_processes(previous.get("peak_memory"), "top_memory")
        out.extend(["", "#### Processes captured near the recorded peaks"])
        if cpu_processes:
            out.append("- Top CPU processes:")
            out.extend(f"  {line}" for line in cpu_processes)
        else:
            out.append("- No per-process CPU ranking was captured near the CPU peak.")
        if memory_processes:
            out.append("- Top memory processes:")
            out.extend(f"  {line}" for line in memory_processes)
        else:
            out.append("- No per-process memory ranking was captured near the memory peak.")

        last_sample = previous.get("last_sample", {}) or {}
        containers = last_sample.get("containers", []) or []
        non_running = [
            item for item in containers if item.get("state") != "running"
        ]
        out.extend(["", "#### Last container and filesystem state before reboot"])
        out.append(
            f"- Containers: {last_sample.get('running_containers', 0)} running of "
            f"{last_sample.get('total_containers', 0)} recorded."
        )
        if non_running:
            out.append(
                "- Non-running containers: "
                + ", ".join(
                    f"{item.get('name', 'unknown')} ({item.get('state', 'unknown')})"
                    for item in non_running[:20]
                )
                + "."
            )
        read_only = [
            item.get("target", "unknown")
            for item in last_sample.get("mounts", []) or []
            if item.get("read_only")
        ]
        out.append(
            "- Read-only tracked mounts: "
            + (", ".join(read_only) if read_only else "none captured")
            + "."
        )

    events = context.get("previous_events", []) or []
    out.extend(["", "#### Important events before reboot"])
    if events:
        for event in events[:20]:
            out.append(
                f"- `{event.get('created_at', 'unknown')}` "
                f"{event.get('kind', 'event')}: {event.get('message', '')}"
            )
    else:
        out.append("- No OOM, kernel-panic, filesystem, mount, or recorded threshold event was retained.")

    out.extend([
        "",
        "#### Next safest step",
        "- Keep the background monitor enabled. If the NAS becomes unresponsive again, "
        "ask this question after reboot before changing services or containers.",
        "",
        "#### Forum-ready summary",
        (
            f"ZimaBrain verified a host boot transition, but the exact cause is "
            f"{'supported by captured markers' if (boot.get('kernel_panic') or boot.get('update_reboot') or boot.get('manual_reboot')) else 'not proven by the available evidence'}."
            if reboot_verified
            else "ZimaBrain does not yet have enough retained host history to verify this reboot or its cause."
        ),
    ])
    return "\n".join(out)
