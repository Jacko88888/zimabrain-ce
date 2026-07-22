import shlex

from brain import bind_mount_permissions


def _evidence(bundle):
    return (bundle.get("same_report_evidence", {}) or {}).get(
        "bind_mount_permissions", {}
    ) or {}


def _identity(record):
    uid = record.get("effective_uid")
    gid = record.get("effective_gid")
    if uid is None or gid is None:
        return "not verified"
    return f"{uid}:{gid} ({record.get('identity_source') or 'source unavailable'})"


def _mount_options(record):
    mount = record.get("mount", {}) or {}
    return mount.get("options") or "not verified"


def _containers_using_mount(records, target):
    return sorted({
        item.get("container", "") for item in records
        if item.get("mount", {}).get("target", "") == target
        and item.get("container")
    })


def _compact_names(names, limit=8):
    values = list(names or [])
    if len(values) <= limit:
        return ", ".join(values)
    return ", ".join(values[:limit]) + f" (+{len(values) - limit} more)"


def answer(bundle, question):
    assessment = bind_mount_permissions.assess_evidence(_evidence(bundle))
    all_records = assessment.get("records", []) or []
    selection = bind_mount_permissions.question_selection(assessment, question)
    records = selection["records"]
    focused_selection = selection["focused"]
    candidate_count = selection["candidate_count"]
    lines = [
        "- This is a container bind-mount permission diagnostic question.",
        "- Host `rw`, Docker bind access, filesystem semantics, numeric ownership and container identity are assessed separately.",
        "",
        "### Correlated bind-mount evidence",
    ]

    if not assessment.get("collected"):
        lines.append("- Container bind-mount permission evidence was not collected.")
        return {
            "lines": lines,
            "next_step": (
                "Collect read-only Docker bind, findmnt, numeric stat and container-identity "
                "evidence before changing permissions or container IDs."
            ),
            "forum_summary": (
                "Container storage permission diagnosis is not verified because correlated "
                "bind-mount evidence was unavailable."
            ),
            "trust_state": "NOT VERIFIED",
            "trust_title": "❌ NOT VERIFIED FROM CURRENT REPORT",
            "trust_detail": "No correlated container bind-mount permission evidence was available.",
        }

    if not records:
        lines.append("- No actionable storage bind was matched to an exact requested container/path.")
        lines.append(
            f"- Current evidence contained {len(all_records)} correlated storage/configuration "
            "bind record(s), but none verifies the cause of this unspecific symptom."
        )
        lines.append("- An empty bounded configuration search is not treated as a collection error.")
        return {
            "lines": lines,
            "next_step": (
                "Confirm the exact container name and its host-source/container-destination "
                "mapping before any write test or permission change."
            ),
            "forum_summary": "No specific failing container storage bind was verified from the current report.",
            "trust_state": "NOT VERIFIED",
            "trust_title": "❌ NOT VERIFIED FROM CURRENT REPORT",
            "trust_detail": "The requested container/path was not matched to current Docker bind evidence.",
        }

    states = []
    if not focused_selection:
        lines.extend([
            "- The question did not identify an exact container or bind path.",
            (
                f"- Showing {len(records)} actionable candidate(s) from {candidate_count}; "
                "these are leads, not a verified match to the reported symptom."
            ),
        ])

    exact_selection = focused_selection and len(records) == 1
    for record in records[:30]:
        states.append(record.get("verification", "PARTIALLY VERIFIED"))
        mount = record.get("mount", {}) or {}
        stat = record.get("stat", {}) or {}
        acl = record.get("acl", {}) or {}
        persistence = record.get("persistence", {}) or {}
        active_users = record.get("active_users", {}) or {}
        target = mount.get("target", "")

        lines.extend([
            "",
            (
                f"#### {'Container' if focused_selection else 'Candidate container'}: "
                f"{record.get('container') or 'not verified'}"
            ),
            f"- Bind mapping: {record.get('source') or 'not verified'} -> {record.get('destination') or 'not verified'}",
            f"- Docker bind access: {'read/write' if record.get('bind_rw') else 'read-only'}",
            f"- Host mount target: {target or 'not verified'}",
            f"- Filesystem: {mount.get('fstype') or 'not verified'}",
            f"- Host mount options: {_mount_options(record)}",
            (
                "- Host path numeric ownership/mode: "
                f"{stat.get('uid', 'unknown')}:{stat.get('gid', 'unknown')} mode={stat.get('mode') or 'unknown'}"
            ),
            f"- Container write identity: {_identity(record)}",
            f"- Classification: {record.get('classification', 'evidence_incomplete')}",
            f"- Severity: {record.get('severity', 'INCOMPLETE')}",
            f"- Diagnosis: {record.get('explanation')}",
        ])

        if record.get("filesystem_uses_mount_permissions"):
            lines.append(
                f"- Filesystem handling: {mount.get('fstype')} normally synthesizes Linux "
                "ownership and modes from mount options in this configuration; recursive "
                "chmod/chown is not an appropriate correction."
            )
        else:
            lines.append(
                "- Filesystem handling: normal Linux mode/ownership checks apply; named ACLs "
                "must also be considered when present."
            )

        if record.get("filesystem_uses_mount_permissions"):
            lines.append(
                "- ACL evidence: normal per-file POSIX ACL ownership is not the primary "
                "permission model for this mounted filesystem."
            )
        elif acl.get("available"):
            lines.append(
                "- ACL evidence: named ACL entries present."
                if acl.get("named_entries")
                else "- ACL evidence: captured; no named ACL entry was detected."
            )
        else:
            lines.append("- ACL evidence: unavailable; ACL restriction is not excluded.")

        write_test = record.get("write_test", {}) or {}
        lines.append(
            f"- Harmless write/remove probe: {write_test.get('result') or 'not tested'}"
        )
        live_remount = record.get("live_remount", {}) or {}
        if live_remount.get("attempted"):
            lines.append(
                "- Live remount support/result: "
                f"{live_remount.get('result') or 'failed/unsupported'}; no remount success is assumed."
            )
        else:
            lines.append("- Live remount support/result: not verified; no remount success is assumed.")

        same_mount_containers = _containers_using_mount(all_records, target)
        if same_mount_containers:
            lines.append(
                "- Containers using this active mount: " + _compact_names(same_mount_containers)
            )

        if active_users.get("collected"):
            lines.append("- Active-user check: `fuser -vm` evidence was collected for this mount.")
            for raw in str(active_users.get("text", "")).splitlines()[:12]:
                lines.append(f"  - {raw}")
        elif target:
            lines.append(
                "- Active-user check before any unmount: "
                f"`fuser -vm {shlex.quote(target)}`"
            )

        if persistence.get("source_verified"):
            paths = sorted({item.get("path", "") for item in persistence.get("matches", [])})
            lines.append(
                "- Persistent mount-management evidence matched: " + ", ".join(paths)
            )
        else:
            searched = persistence.get("searched", []) or []
            lines.append(
                "- Persistent ZimaOS mount-management source: not verified"
                + (f" after bounded checks of {', '.join(searched)}." if searched else ".")
            )
            lines.append(
                "- No persistent correction is claimed. An empty bounded configuration search "
                "is valid negative evidence, not a command failure."
            )

    config_records = [
        item for item in all_records
        if item.get("role") == "configuration"
        and item.get("container") in {record.get("container") for record in records}
    ]
    lines.extend([
        "",
        "### Safety boundaries",
        "- Do not change PUID/PGID until the same container's configuration-directory ownership is verified.",
        "- Do not recursively chmod or chown exFAT, NTFS or other mount-option-permission filesystems.",
        "- Do not force-unmount an active drive. Verify host processes and every bound container first.",
        "- Separate a temporary live test, a clean unmount/remount and a persistent ZimaOS-compatible change.",
    ])
    if focused_selection and config_records:
        lines.append("- Configuration-directory bind evidence was captured for the selected container.")
        for item in config_records[:10]:
            stat = item.get("stat", {}) or {}
            lines.append(
                f"  - {item.get('container')}: {item.get('source')} -> {item.get('destination')} "
                f"owner={stat.get('uid', 'unknown')}:{stat.get('gid', 'unknown')} "
                f"mode={stat.get('mode') or 'unknown'}"
            )
    else:
        lines.append("- Configuration-directory ownership was not verified; changing PUID/PGID is not recommended.")

    probes = [
        bind_mount_permissions.safe_probe_command(record)
        for record in records if not (record.get("write_test", {}) or {}).get("attempted")
    ]
    probes = [item for item in probes if item]
    if exact_selection and probes:
        lines.extend([
            "",
            "### Optional temporary verification",
            "- This is a probe, not a repair. It is limited to the confirmed container media directory and removes its test file immediately:",
            "```bash",
            probes[0],
            "```",
        ])

    if not focused_selection:
        trust_state = "PARTIALLY VERIFIED"
        trust_title = "⚠️ PARTIALLY VERIFIED"
        trust_detail = (
            "Actionable permission candidates were found, but the question did not identify "
            "which container and bind path actually failed."
        )
    elif "VERIFIED" in states:
        trust_state = "VERIFIED"
        trust_title = "✅ VERIFIED FROM CORRELATED CONTAINER/MOUNT EVIDENCE"
        trust_detail = (
            "Docker bind state, host mount state, numeric ownership and container identity "
            "were correlated for at least one requested binding."
        )
    else:
        trust_state = "PARTIALLY VERIFIED"
        trust_title = "⚠️ PARTIALLY VERIFIED"
        trust_detail = (
            "A matching container storage bind was found, but the actual write result or one "
            "of the permission gates remains incomplete."
        )

    issue_records = [item for item in records if item.get("issue")]
    if issue_records and not focused_selection:
        next_step = (
            "Confirm the exact failing container name and host-source/container-destination bind. "
            "ZimaBrain can then offer one self-cleaning probe for that confirmed media directory."
        )
        forum_summary = (
            f"ZimaBrain found {candidate_count} permission candidate(s), but no exact failing "
            "container bind was identified by the question."
        )
    elif issue_records:
        next_step = (
            "Run only the offered self-cleaning write probe for one exact media bind. If a clean "
            "unmount is later required, review `fuser -vm` and stop only the identified containers "
            "before changing any mount configuration."
        )
        forum_summary = (
            f"ZimaBrain correlated {len(records)} container storage bind(s); "
            f"{len(issue_records)} currently need permission or evidence follow-up."
        )
    else:
        next_step = (
            "No mount or basic mode denial was verified. If the application still cannot delete, "
            "run the offered direct identity probe before changing application settings."
        )
        forum_summary = (
            "Container bind, mount and numeric mode evidence do not currently verify a storage-level denial."
        )

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
        "trust_state": trust_state,
        "trust_title": trust_title,
        "trust_detail": trust_detail,
    }
