from brain import answer_modes
from brain import router
from brain.layers import storage_mounts
from brain.layers import disk_health
from brain.layers import failed_units
from brain.layers import snapraid_mergerfs
from brain.layers import dashboard_alerts
from brain.layers import disk_crc
from brain.layers import filesystem_usage
from brain.layers import disk_commands
from brain.layers import container_commands
from brain.layers import containers
from brain.layers import system_commands
from brain.layers import network_commands
from brain.layers import docker_bind_mounts
from brain.layers import docker_daemon_diag
from brain.layers import app_storage_paths
from brain.layers import app_runtime_diag
from brain.layers import app_setup_playbooks
from brain.layers import backup_borg
from brain.layers import smart_trend
from brain.layers import network_exposure
from brain.layers import zimaos_regression
from brain.layers import gpu_ai_runtime
from brain.layers import report_comparison
from brain.layers import disk_inventory
from brain.layers import forum_issue_intake
from brain.layers import read_only_storage_diag
from brain.layers import repair_planner
from brain.layers import log_intake_diag
from brain.layers import zimaos_update_safety
from brain.layers import permissions_ownership_diag
from brain.layers import smb_shares_diag
from brain.layers import network_connectivity_diag
from brain.layers import raid_add_drive_diag
from brain.layers import install_boot_diag
from brain.layers import manual_knowledge
from brain.layers import third_party_app_store_index
from brain.layers import media_app_verified_guides
from brain.layers.hardware_compatibility_layer import answer_hardware_compatibility
from brain.layers.smart_health_layer import answer_smart_health


def _verification_status(active_layer, layer_lines, report_text):
    text = "\n".join(str(x) for x in (layer_lines or [])).lower()
    layer = (active_layer or "").lower()

    if not str(report_text or "").strip():
        return {
            "state": "NOT VERIFIED",
            "title": "❌ NOT VERIFIED",
            "detail": "Dashboard evidence could not be loaded, so this answer is not verified.",
        }

    not_verified_markers = [
        "no matching local container/app evidence",
        "no matching docker mount evidence",
        "no docker mount evidence",
        "no docker evidence",
        "no matching evidence",
        "no matching same-report evidence",
        "intake guidance only",
        "not a verified diagnosis",
        "not verified yet",
        "no evidence was parsed",
        "could not be loaded",
        "not found in the current report",
        "not captured in this report",
        "not installed, not running",
        "fallback guidance route",
    ]

    partial_markers = [
        "this is a zimaos manual / how-to question",
        "answer source: official zimaos manual pages saved locally",
        "guidance from documentation",
        "official zimaos manual guidance",
        "cannot confirm the latest upstream release",
        "may mean",
        "could mean",
        "needs extra verification",
        "should be verified",
        "missing",
        "not captured",
        "not enough",
        "general playbook",
        "playbook guidance",
        "not fully verified from same-report evidence",
    ]

    if "zimaos manual knowledge engine" in layer:
        return {
            "state": "OFFICIAL MANUAL REFERENCE",
            "title": "📘 OFFICIAL MANUAL REFERENCE",
            "detail": "This answer is backed by official ZimaOS documentation, but it is not a same-report diagnosis of this machine.",
        }

    if "third-party app store index layer" in layer:
        return {
            "state": "THIRD-PARTY APP STORE INDEX",
            "title": "📦 THIRD-PARTY APP STORE INDEX",
            "detail": "This answer is based on the local third-party app-store index. It is not official ZimaOS manual evidence or full same-report verification.",
        }

    if "media app verified install guides layer" in layer or "app verified install guides layer" in layer:
        return {
            "state": "VERIFIED INSTALL GUIDE",
            "title": "🧭 VERIFIED INSTALL GUIDE",
            "detail": "This answer uses a verified install and troubleshooting order. It checks storage, containers, bind mounts, permissions, network access, and logs before configuration steps.",
        }

    if "fallback" in layer:
        return {
            "state": "NOT VERIFIED",
            "title": "❌ NOT VERIFIED",
            "detail": "The question did not match a verified diagnostic layer. This answer is guidance only.",
        }

    if "forum issue intake" in layer:
        return {
            "state": "NOT VERIFIED",
            "title": "❌ NOT VERIFIED",
            "detail": "This is intake guidance only. The root cause is not verified until the required evidence is provided.",
        }

    if any(marker in text for marker in not_verified_markers):
        return {
            "state": "NOT VERIFIED",
            "title": "❌ NOT VERIFIED",
            "detail": "The current report does not contain matching evidence to verify this answer.",
        }

    if any(marker in text for marker in partial_markers):
        return {
            "state": "PARTIALLY VERIFIED",
            "title": "⚠️ PARTIALLY VERIFIED",
            "detail": "Some local evidence was found, but one or more key facts still need confirmation.",
        }

    return {
        "state": "VERIFIED",
        "title": "✅ VERIFIED FROM SAME-REPORT EVIDENCE",
        "detail": "This answer is based on evidence found in the current report.",
    }


def _verification_block(status, active_layer, active_layer_file):
    return [
        "#### Verification status",
        f"@@VERIFY:{status['state']}@@ {status['title']}",
        f"- {status['detail']}",
        f"- Active layer: {active_layer}",
        f"- Layer file: `{active_layer_file}`",
        "",
    ]


def answer_question(question, bundle, build_verifier_summary, critical_badge, severity_dot):
    q = (question or "").strip().lower()
    smart_result = answer_smart_health(question, bundle)
    if smart_result.matched:
        return smart_result.answer

    hardware_result = answer_hardware_compatibility(question)
    if hardware_result.matched:
        return hardware_result.answer

    route = router.classify(question)
    n = bundle["normalized"]

    out = []
    focused_answer = not answer_modes.is_global_question(question)

    out.append("### ZimaBrain Answer")
    out.append("")
    out.append("## ❓ Question asked")
    out.append(f"### {question.strip()}")
    out.append("")
    out.append("@@VERIFICATION_BLOCK@@")
    out.append("")

    if not focused_answer:
        out.extend(build_verifier_summary(bundle))
        out.append("")

        critical = bundle.get("critical_findings", [])
        if critical:
            out.append("#### Critical Same-Report Verifier")
            for finding in critical:
                out.append(f"- {critical_badge(finding['level'])}: {finding['title']}")
                out.append(f"  Evidence: {finding['detail']}")
                out.append(f"  Why it matters: {finding['why']}")
                out.append(f"  Next safest step: {finding['next']}")
            out.append("")

    out.append("#### Direct answer / severity")
    if not bundle["report"].strip():
        out.append("- Dashboard evidence could not be loaded.")
        out.append("")
        out.append("#### Next safest step")
        out.append("- Check that the dashboard source on port 8514 is running before analysing dashboard evidence.")
        status = _verification_status("No Evidence", out, bundle.get("report", ""))
        block = _verification_block(status, "No Evidence", "app/brain/answer_builder.py")
        final = []
        for line in out:
            if line == "@@VERIFICATION_BLOCK@@":
                final.extend(block)
            else:
                final.append(line)
        return "\n".join(final)

    dashboard_alert_question = route.get("dashboard_alert_question", False)
    failed_unit_question = route.get("failed_unit_question", False)
    crc_question = route.get("crc_question", False)
    usage_question = route.get("usage_question", False)
    exited_question = route.get("exited_question", False)
    container_question = route.get("container_question", False)
    disk_health_question = route.get("disk_health_question", False)
    mount_question = route.get("storage_mount_question", False)
    snapraid_question = route.get("snapraid_question", False)
    disk_command_question = route.get("disk_command_question", False)
    container_command_question = route.get("container_command_question", False)
    system_command_question = route.get("system_command_question", False)
    network_command_question = route.get("network_command_question", False)
    docker_bind_mount_question = route.get("docker_bind_mount_question", False)
    docker_daemon_question = route.get("docker_daemon_question", False)
    app_storage_path_question = route.get("app_storage_path_question", False)
    app_runtime_diag_question = route.get("app_runtime_diag_question", False)
    app_setup_playbook_question = route.get("app_setup_playbook_question", False)
    third_party_app_store_question = route.get("third_party_app_store_question", False)
    media_app_verified_guides_question = route.get("media_app_verified_guides_question", False)
    trust_state_override = None
    trust_title_override = None
    trust_detail_override = None
    manual_knowledge_question = route.get("manual_knowledge_question", False)
    backup_borg_question = route.get("backup_borg_question", False)
    smart_trend_question = route.get("smart_trend_question", False)
    network_exposure_question = route.get("network_exposure_question", False)
    zimaos_regression_question = route.get("zimaos_regression_question", False)
    gpu_ai_runtime_question = route.get("gpu_ai_runtime_question", False)
    report_comparison_question = route.get("report_comparison_question", False)
    disk_inventory_question = route.get("disk_inventory_question", False)
    forum_issue_intake_question = route.get("forum_issue_intake_question", False)
    read_only_storage_question = route.get("read_only_storage_question", False)
    install_boot_question = route.get("install_boot_question", False)
    raid_add_drive_question = route.get("raid_add_drive_question", False)
    network_connectivity_question = route.get("network_connectivity_question", False)
    smb_shares_question = route.get("smb_shares_question", False)
    permissions_ownership_question = route.get("permissions_ownership_question", False)
    zimaos_update_safety_question = route.get("zimaos_update_safety_question", False)
    log_intake_question = route.get("log_intake_question", False)
    repair_planner_question = route.get("repair_planner_question", False)

    active_layer = "Verified Answer Builder"
    active_layer_file = "app/brain/answer_builder.py"
    layer_start_index = len(out)

    if failed_unit_question:
        layer = failed_units.answer(bundle, critical_badge)
        active_layer = "Failed Units Layer"
        active_layer_file = "app/brain/layers/failed_units.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif dashboard_alert_question:
        layer = dashboard_alerts.answer(bundle, severity_dot)
        active_layer = "Dashboard Alerts Layer"
        active_layer_file = "app/brain/layers/dashboard_alerts.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif crc_question:
        layer = disk_crc.answer(bundle)
        active_layer = "Disk CRC Layer"
        active_layer_file = "app/brain/layers/disk_crc.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif usage_question:
        layer = filesystem_usage.answer(bundle)
        active_layer = "Filesystem Usage Layer"
        active_layer_file = "app/brain/layers/filesystem_usage.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif exited_question or container_question:
        layer = containers.answer(bundle)
        active_layer = "Containers Layer"
        active_layer_file = "app/brain/layers/containers.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif smart_trend_question:
        layer = smart_trend.answer(bundle)
        active_layer = "SMART Trend Monitor"
        active_layer_file = "app/brain/layers/smart_trend.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif network_exposure_question:
        layer = network_exposure.answer(bundle)
        active_layer = "Network Exposure / Firewall Layer"
        active_layer_file = "app/brain/layers/network_exposure.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif zimaos_regression_question:
        layer = zimaos_regression.answer(bundle, question)
        active_layer = "ZimaOS Update / Regression Layer"
        active_layer_file = "app/brain/layers/zimaos_regression.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif gpu_ai_runtime_question:
        layer = gpu_ai_runtime.answer(bundle)
        active_layer = "GPU / AI Runtime Layer"
        active_layer_file = "app/brain/layers/gpu_ai_runtime.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif report_comparison_question:
        layer = report_comparison.answer(bundle)
        active_layer = "Report Comparison Layer"
        active_layer_file = "app/brain/layers/report_comparison.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif disk_inventory_question:
        layer = disk_inventory.answer(bundle)
        active_layer = "Disk Inventory / Drive Count Layer"
        active_layer_file = "app/brain/layers/disk_inventory.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif docker_daemon_question:
        layer = docker_daemon_diag.answer(bundle, question)
        active_layer = "Docker Daemon Diagnostics Layer"
        active_layer_file = "app/brain/layers/docker_daemon_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif read_only_storage_question:
        layer = read_only_storage_diag.answer(bundle, question)
        active_layer = "Read-Only Storage Diagnostics Layer"
        active_layer_file = "app/brain/layers/read_only_storage_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif install_boot_question:
        layer = install_boot_diag.answer(bundle, question)
        active_layer = "Install / Boot Diagnostics Layer"
        active_layer_file = "app/brain/layers/install_boot_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif raid_add_drive_question:
        layer = raid_add_drive_diag.answer(bundle, question)
        active_layer = "RAID / Add Drive Planning Layer"
        active_layer_file = "app/brain/layers/raid_add_drive_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif network_connectivity_question:
        layer = network_connectivity_diag.answer(bundle, question)
        active_layer = "Network Connectivity Diagnostics Layer"
        active_layer_file = "app/brain/layers/network_connectivity_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif smb_shares_question:
        layer = smb_shares_diag.answer(bundle, question)
        active_layer = "SMB / Shares Diagnostics Layer"
        active_layer_file = "app/brain/layers/smb_shares_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif permissions_ownership_question:
        layer = permissions_ownership_diag.answer(bundle, question)
        active_layer = "Permissions / Ownership Diagnostics Layer"
        active_layer_file = "app/brain/layers/permissions_ownership_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif zimaos_update_safety_question:
        layer = zimaos_update_safety.answer(bundle, question)
        active_layer = "ZimaOS Update / Rollback Safety Layer"
        active_layer_file = "app/brain/layers/zimaos_update_safety.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif log_intake_question:
        layer = log_intake_diag.answer(bundle, question)
        active_layer = "Log Intake / Uploaded Evidence Layer"
        active_layer_file = "app/brain/layers/log_intake_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif repair_planner_question:
        layer = repair_planner.answer(bundle, question)
        active_layer = "Final Recommendation / Repair Planner Layer"
        active_layer_file = "app/brain/layers/repair_planner.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif forum_issue_intake_question:
        layer = forum_issue_intake.answer(bundle, question)
        active_layer = "Forum Issue Intake Layer"
        active_layer_file = "app/brain/layers/forum_issue_intake.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif disk_health_question:
        layer = disk_health.answer(bundle, severity_dot)
        active_layer = "Disk Health Layer"
        active_layer_file = "app/brain/layers/disk_health.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif docker_bind_mount_question:
        layer = docker_bind_mounts.answer(bundle)
        active_layer = "Docker Bind-Mount Verifier"
        active_layer_file = "app/brain/layers/docker_bind_mounts.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif mount_question:
        layer = storage_mounts.answer(bundle)
        active_layer = "Storage Mount Layer"
        active_layer_file = "app/brain/layers/storage_mounts.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif snapraid_question:
        layer = snapraid_mergerfs.answer(bundle)
        active_layer = "SnapRAID / mergerfs Layer"
        active_layer_file = "app/brain/layers/snapraid_mergerfs.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif docker_bind_mount_question:
        layer = docker_bind_mounts.answer(bundle)
        active_layer = "Docker Bind-Mount Verifier"
        active_layer_file = "app/brain/layers/docker_bind_mounts.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif media_app_verified_guides_question:
        layer = media_app_verified_guides.answer(bundle, question)
        active_layer = "App Verified Install Guides Layer"
        active_layer_file = "app/brain/layers/media_app_verified_guides.py"
        out.extend(layer.get("lines", []))
        next_step = layer.get("next_step", "Verify storage path, container state, bind mounts, permissions, network access, and logs before changing configuration.")
        forum_summary = layer.get("forum_summary", "Media app verified install guidance. Verify storage, containers, bind mounts, permissions, network, and logs before reinstalling.")
        trust_state_override = layer.get("trust_state")
        trust_title_override = layer.get("trust_title")
        trust_detail_override = layer.get("trust_detail")

    elif third_party_app_store_question:
        layer = third_party_app_store_index.answer(bundle, question)
        active_layer = "Third-Party App Store Index Layer"
        active_layer_file = "app/brain/layers/third_party_app_store_index.py"
        out.extend(layer.get("lines", []))
        next_step = layer.get("next_step", "Verify the app source, ports, volumes, and permissions before installing.")
        forum_summary = layer.get("forum_summary", "Third-party app-store guidance only. Verify before installing.")

    elif app_setup_playbook_question:
        layer = app_setup_playbooks.answer(bundle, question)
        active_layer = "App Setup / Version Playbook Layer"
        active_layer_file = "app/brain/layers/app_setup_playbooks.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif manual_knowledge_question:
        layer = manual_knowledge.answer(bundle, question)
        active_layer = "ZimaOS Manual Knowledge Engine"
        active_layer_file = "app/brain/layers/manual_knowledge.py"
        out.extend(layer.get("lines", []))
        next_step = "Follow the official ZimaOS manual page first. If the user has an error, collect evidence and route back to diagnostics."
        forum_summary = "This is official ZimaOS manual guidance, not a same-report diagnosis."

    elif app_storage_path_question:
        layer = app_storage_paths.answer(bundle, question)
        active_layer = "App Storage-Path Verifier"
        active_layer_file = "app/brain/layers/app_storage_paths.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif app_runtime_diag_question:
        layer = app_runtime_diag.answer(bundle, question)
        active_layer = "App Runtime Diagnostics Layer"
        active_layer_file = "app/brain/layers/app_runtime_diag.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif app_storage_path_question:
        layer = app_storage_paths.answer(bundle, question)
        active_layer = "App Storage-Path Verifier"
        active_layer_file = "app/brain/layers/app_storage_paths.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif backup_borg_question:
        layer = backup_borg.answer(bundle)
        active_layer = "Backup / Borg Layer"
        active_layer_file = "app/brain/layers/backup_borg.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif container_command_question:
        layer = container_commands.answer(bundle)
        active_layer = "Container Commands Layer"
        active_layer_file = "app/brain/layers/container_commands.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif network_command_question:
        layer = network_commands.answer(bundle)
        active_layer = "Network Commands Layer"
        active_layer_file = "app/brain/layers/network_commands.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif system_command_question:
        layer = system_commands.answer(bundle)
        active_layer = "System Commands Layer"
        active_layer_file = "app/brain/layers/system_commands.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif container_command_question:
        layer = container_commands.answer(bundle)
        active_layer = "Container Commands Layer"
        active_layer_file = "app/brain/layers/container_commands.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    elif disk_command_question:
        layer = disk_commands.answer(bundle)
        active_layer = "Disk Commands Layer"
        active_layer_file = "app/brain/layers/disk_commands.py"
        out.extend(layer["lines"])
        next_step = layer["next_step"]
        forum_summary = layer["forum_summary"]

    else:
        active_layer = "Fallback Guidance Route"
        active_layer_file = "app/brain/answer_builder.py"
        out.append("- This Flask cockpit currently answers dashboard evidence questions reliably.")
        out.append("- Try: show me dashboard alerts, explain sda CRC errors, why is sdd filesystem usage 100%, which containers are exited, which disks are healthy, or is my system protected?")
        next_step = "Ask a dashboard-specific question, or extend the Flask verifier with additional ZimaOS layers."
        forum_summary = "Ask a dashboard-specific question so ZimaBrain can route the answer through the correct verifier layer."

    if not focused_answer:
        out.append("")
        out.append("#### What not to touch")
        out.append("- Do not run docker system prune.")
        out.append("- Do not remove containers in bulk.")
        out.append("- Do not delete /media folders until findmnt verifies whether they are active mounts.")
        out.append("- Do not change Docker bind mounts until the exact source path is verified.")
        out.append("- Do not repair SnapRAID/mergerfs until pool config, parity disk, and data disks are verified.")

    out.append("")
    out.append("#### Next safest step")
    out.append(f"- {next_step}")

    out.append("")
    out.append("#### Forum-ready summary")
    out.append(forum_summary)

    status = _verification_status(active_layer, out[layer_start_index:], bundle.get("report", ""))

    if trust_state_override:
        status = {
            "state": trust_state_override,
            "title": trust_title_override or trust_state_override,
            "detail": trust_detail_override or "Layer supplied a more specific trust state for this answer.",
        }

    block = _verification_block(status, active_layer, active_layer_file)

    final = []
    for line in out:
        if line == "@@VERIFICATION_BLOCK@@":
            final.extend(block)
        else:
            final.append(line)

    return "\n".join(final)
