import os
import re

from brain import health_memory
from brain import service_diagnostics


TREND_DB_PATH = "/data/zimabrain_trends.sqlite"


def _failed_lines(text):
    result = []
    for raw in str(text or "").splitlines():
        line = " ".join(raw.split())
        low = line.lower()
        if not line or line.startswith("ERROR:"):
            continue
        if "0 loaded units listed" in low or "no units listed" in low:
            continue
        result.append(line)
    return result


def _history(bundle):
    db_path = str(bundle.get("health_memory_db_path", TREND_DB_PATH) or TREND_DB_PATH)
    if not os.path.exists(db_path):
        return []
    try:
        return health_memory.helper_service_correlations(db_path, limit=20)
    except Exception:
        return []


def _path_line(item):
    state = "missing" if not item.get("exists") else "exists"
    if item.get("exists") and item.get("requires_executable"):
        state += ", executable" if item.get("executable") else ", not executable"
    return (
        f"{item.get('path', 'unknown')} ({item.get('source', 'unknown')}: {state})"
    )


def _append_missing_analysis(lines, assessment):
    if assessment["missing_fragments"]:
        for item in assessment["missing_fragments"]:
            lines.append(f"- Unit FragmentPath does not exist: {_path_line(item)}")
        lines.append(
            "- Classification: stale, removed or inconsistent unit definition. "
            "A missing FragmentPath alone does not confirm a packaging regression."
        )

    if assessment["missing_system"]:
        for item in assessment["missing_system"]:
            lines.append(f"- Missing ZimaOS-managed helper/executable: {_path_line(item)}")
        if assessment["possible_packaging_regression"]:
            lines.append(
                "- Classification: possible ZimaOS packaging regression. "
                "The OS-managed unit, missing system path and execution-failure evidence agree, "
                "but this is not confirmed without comparison to the expected files for this ZimaOS build."
            )
        else:
            lines.append(
                "- Classification: missing system helper verified, but a ZimaOS packaging regression "
                "is not confirmed. A stale or locally overridden service configuration remains possible."
            )

    if assessment["missing_data"]:
        for item in assessment["missing_data"]:
            lines.append(f"- Missing user/local script or required file under /DATA: {_path_line(item)}")
        lines.append(
            "- Classification: broken or stale local service configuration, unless the /DATA path "
            "was temporarily unavailable when the evidence was collected."
        )

    if assessment["missing_other"]:
        for item in assessment["missing_other"]:
            lines.append(f"- Missing referenced executable/file: {_path_line(item)}")
        lines.append(
            "- Classification: broken or stale service configuration; ownership by ZimaOS or a local "
            "installation must be confirmed from FragmentPath and package provenance."
        )

    if assessment["non_executable"]:
        for item in assessment["non_executable"]:
            lines.append(f"- Required executable exists without executable permission: {_path_line(item)}")

    if assessment["status_203"]:
        lines.append("- systemd execution evidence: status=203/EXEC was verified.")
    if assessment["journal_missing_path"]:
        lines.append(
            '- Journal evidence: a recent file-not-found/"No such file or directory" execution message was captured.'
        )
    if assessment["status_missing_path"]:
        lines.append(
            '- systemctl status evidence: a file-not-found/"No such file or directory" execution message was captured.'
        )
    if assessment["fragment_path"]:
        lines.append(f"- Unit FragmentPath: {assessment['fragment_path']}")


def answer(bundle, critical_badge, question=""):
    question_text = str(question or "").lower()
    question_tokens = set(re.findall(r"[a-z0-9]+", question_text))
    missing_focus = bool(
        question_tokens & {
            "missing", "absent", "executable", "executables",
            "execstart", "exec", "203",
        }
        or "not found" in question_text
        or "cannot locate" in question_text
        or "can't locate" in question_text
    )
    helper_focus = bool(
        question_tokens & {
            "helper", "helpers", "watchdog", "watchdogs", "primary",
        }
    ) and not missing_focus
    evidence = bundle.get("same_report_evidence", {}) or {}
    raw = str(evidence.get("failed_units", "") or "")
    failed_lines = _failed_lines(raw)
    details = evidence.get("failed_unit_details", []) or []
    details_collected = bool(evidence.get("failed_unit_details_collected", False))
    if not isinstance(details, list):
        details = []

    assessments = service_diagnostics.assess_details(details)
    detail_evidence_complete = bool(
        details_collected
        and len(details) >= len(failed_lines)
        and all(item["verification"] == "VERIFIED" for item in assessments)
    ) if failed_lines else details_collected
    history = _history(bundle)
    missing_found = any(
        item["missing"] or item["non_executable"] or item["status_203"]
        or item["journal_missing_path"] or item["status_missing_path"]
        for item in assessments
    )

    lines = ["Failed service / systemd unit check", "", "Confirmed:"]
    trust_state = "VERIFIED"
    trust_title = "✅ VERIFIED FROM SAME-REPORT EVIDENCE"
    trust_detail = (
        "Failed-unit, unit-property, executable-path and related-service evidence were checked."
    )
    if failed_lines and not detail_evidence_complete:
        trust_state = "PARTIALLY VERIFIED"
        trust_title = "⚠️ PARTIALLY VERIFIED"
        trust_detail = (
            "The failed-unit list is available, but one or more unit-property or path checks are incomplete."
        )

    if failed_lines:
        lines.append(
            f"- Failed-unit assessment: {len(failed_lines)} failed unit(s) were captured by systemctl."
        )
    else:
        lines.append(
            "- Failed-unit assessment: no failed host unit was captured by the current systemctl evidence."
        )

    for detail, assessment in zip(details, assessments):
        unit = assessment["unit"]
        props = detail.get("properties", {}) or {}
        state = (
            f"{props.get('ActiveState', 'unknown')}/"
            f"{props.get('SubState', 'unknown')}"
        )
        lines.extend([
            "",
            f"- Failed unit: {unit}",
            f"  Current unit state: {state}",
            f"  Severity: {assessment['severity']}",
        ])

        if assessment["is_helper"]:
            lines.append(f"  Failed helper/watchdog unit: {unit}")
            lines.append(
                f"  Related primary service: {assessment['primary_unit'] or 'not identified'}"
            )
            if assessment["primary_available"]:
                lines.append(
                    "  Current primary-service state: "
                    f"{assessment['primary_state']}/{assessment['primary_substate']}"
                )
            else:
                lines.append("  Current primary-service state: evidence unavailable")
            lines.append(
                f"  Current outage indicated: {assessment['current_outage']}"
            )
            if assessment["current_outage"] == "no":
                lines.append(
                    "  Conclusion: the helper is failed, but the related primary service is active. "
                    "No current primary-service outage was verified, so severity is reduced."
                )
            elif assessment["current_outage"] == "yes":
                lines.append(
                    "  Conclusion: both the helper and related primary service are failed. "
                    "A current outage is indicated and severity remains high."
                )
            else:
                lines.append(
                    "  Evidence incomplete: the primary-service state could not be verified. "
                    "Confirmation is still required."
                )
                trust_state = "PARTIALLY VERIFIED"
                trust_title = "⚠️ PARTIALLY VERIFIED"
                trust_detail = (
                    "The helper failure is verified, but current primary-service evidence is unavailable."
                )

        _append_missing_analysis(lines, assessment)

    if failed_lines and not details and not details_collected:
        lines.append(
            "- Detailed unit-property, journal and executable-path evidence was not captured for "
            "the failed units in this report."
        )
        trust_state = "PARTIALLY VERIFIED"
        trust_title = "⚠️ PARTIALLY VERIFIED"
        trust_detail = (
            "The failed-unit list is verified, but detailed executable and related-service evidence is unavailable."
        )

    if missing_focus and not missing_found and detail_evidence_complete:
        lines.append(
            "- No missing required helper files were verified from the current failed-unit evidence."
        )
    elif missing_focus and not detail_evidence_complete:
        lines.append(
            "- Missing-helper and executable-path verification evidence is unavailable."
        )
        if not failed_lines:
            trust_state = "NOT VERIFIED"
            trust_title = "❌ NOT VERIFIED"
            trust_detail = (
                "Failed-unit evidence could not be collected, so missing required helpers cannot be assessed."
            )

    helper_assessments = [item for item in assessments if item["is_helper"]]
    if helper_focus and not helper_assessments:
        lines.append(
            "- No failed helper/watchdog relationship with a related primary service "
            "was verified from the current failed-unit evidence."
        )

    current_units = {item["unit"] for item in assessments}
    for item in history:
        if item.get("helper") in current_units or item.get("classification") == "recovered_helper":
            lines.append(f"- Timeline: {item.get('message', '')}")

    if not failed_lines and not details:
        recovered = [
            item for item in history
            if item.get("classification") == "recovered_helper"
        ]
        if recovered:
            lines.append(
                "- Recovered condition: the earlier helper failure is historical; it is not present "
                "in the current failed-unit evidence."
            )

    if failed_lines:
        helper_outage = any(
            item["current_outage"] == "yes" for item in helper_assessments
        )
        helper_active = any(
            item["current_outage"] == "no" for item in helper_assessments
        )

        if trust_state != "VERIFIED":
            next_step = (
                "Confirm the incomplete primary-service, unit-property or executable-path "
                "evidence explicitly identified above before changing, restarting or repairing a service."
            )
        elif missing_focus and not missing_found:
            next_step = (
                "No missing-helper repair is indicated by the current evidence. Review the separately "
                "listed failed unit only if its service function is required or a current symptom exists."
            )
        elif helper_focus and not helper_assessments:
            next_step = (
                "No helper-to-primary outage repair is indicated by the current evidence. Review the "
                "separately listed failed unit only if its service function is required or a current symptom exists."
            )
        elif missing_found:
            next_step = (
                "Verify the referenced path, FragmentPath and file ownership or package provenance shown "
                "above before replacing a file, changing permissions or editing the unit."
            )
        elif helper_outage:
            next_step = (
                "Inspect the related primary service and its recent journal evidence before attempting a "
                "restart or repair, because the current evidence indicates an outage."
            )
        elif helper_active:
            next_step = (
                "No current primary-service outage repair is indicated. Compare the helper failure with "
                "the health timeline and investigate it during a maintenance window if it persists."
            )
        else:
            next_step = (
                "Review the failed unit's current role and recent journal evidence before deciding whether "
                "action is needed; do not restart it solely because a failed state was recorded."
            )

        if missing_focus:
            if missing_found:
                forum_summary = (
                    f"Current systemctl evidence contains {len(failed_lines)} failed unit(s) and verified "
                    "a referenced executable or file condition. Classification remains scoped to the evidence shown."
                )
            else:
                forum_summary = (
                    f"Current systemctl evidence contains {len(failed_lines)} failed unit(s), but no missing "
                    "required helper file was verified from the executable-path checks."
                )
        elif helper_focus:
            if helper_assessments:
                forum_summary = (
                    f"Current systemctl evidence contains {len(failed_lines)} failed unit(s). ZimaBrain "
                    "correlated the helper relationship and checked the related primary-service state."
                )
            else:
                forum_summary = (
                    f"Current systemctl evidence contains {len(failed_lines)} failed unit(s), but no failed "
                    "helper/watchdog relationship with a related primary service was verified."
                )
        else:
            forum_summary = (
                f"Current systemctl evidence contains {len(failed_lines)} failed unit(s). "
                "ZimaBrain checked unit properties, related services and referenced executable paths."
            )
    else:
        if trust_state != "VERIFIED":
            next_step = (
                "Current failed-unit evidence is incomplete or unavailable. Collect a fresh systemctl "
                "failed-unit snapshot and unit-property evidence before drawing a conclusion or changing a service."
            )
            forum_summary = (
                "Failed-unit evidence was unavailable, so no current service or executable-path conclusion "
                "could be verified."
            )
        else:
            next_step = (
                "No failed-unit repair is indicated by this snapshot. Recheck only if a service symptom is active."
            )
            forum_summary = "Current systemctl evidence did not contain a failed host unit."

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
        "trust_state": trust_state,
        "trust_title": trust_title,
        "trust_detail": trust_detail,
    }
