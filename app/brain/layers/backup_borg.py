def _parse_docker_access(bundle):
    text = bundle.get("same_report_evidence", {}).get("docker_access", "")
    rows = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or "|" not in line:
            continue

        parts = line.split("|", 2)
        if len(parts) != 3:
            continue

        name = parts[0].lstrip("/")
        mounts = parts[1]
        ports = parts[2]

        mount_items = []
        for item in mounts.split(";"):
            item = item.strip()
            if not item or "->" not in item:
                continue

            try:
                source_dest, rw = item.rsplit(":", 1)
                source, dest = source_dest.split("->", 1)
            except ValueError:
                continue

            mount_items.append({
                "source": source.strip(),
                "dest": dest.strip(),
                "rw": rw.strip().lower() == "true",
            })

        rows.append({
            "name": name,
            "mounts": mount_items,
            "ports": ports,
        })

    return rows


def _looks_backup_related(text):
    low = text.lower()
    return any(x in low for x in [
        "borg",
        "borgmatic",
        "backup",
        "restore",
        "repo",
        "repos",
    ])


def answer(bundle):
    lines = []
    rows = _parse_docker_access(bundle)

    lines.append("- This is a backup / Borg verification question.")
    lines.append("- The answer comes from the Backup / Borg Layer using same-report Docker mount evidence.")
    lines.append("")

    if not rows:
        lines.append("No Docker mount evidence was parsed from the current report.")
        return {
            "lines": lines,
            "next_step": "Collect Docker inspect mount evidence before relying on backup or restore paths.",
            "forum_summary": "No backup mount evidence was available in the current report. Collect Docker inspect mount data before relying on backup paths.",
        }

    borg_containers = []
    repo_paths = []
    restore_paths = []
    source_paths = []
    risky_paths = []
    appdata_backup_access = []

    for row in rows:
        name = row["name"]
        container_is_borg = _looks_backup_related(name)

        for m in row["mounts"]:
            src = m["source"]
            dst = m["dest"]
            rw = "rw" if m["rw"] else "ro"
            combined = f"{name} {src} {dst}"

            if not container_is_borg and not _looks_backup_related(combined):
                continue

            item = f"{name}: {src} -> {dst} {rw}"
            borg_containers.append(name)

            low_item = item.lower()
            if "repo" in low_item or "repos" in low_item:
                repo_paths.append(item)
            elif "restore" in low_item:
                restore_paths.append(item)
            else:
                source_paths.append(item)

            if "/DATA/AppData" in src or "/DATA/AppData" in dst:
                appdata_backup_access.append(item)

            if "/DATA/.media" in src or "/var/lib/casaos_data/.media" in src or "-/dev/" in src:
                risky_paths.append(item)

    unique_containers = sorted(set(borg_containers))

    lines.append("### Backup containers detected")
    if unique_containers:
        for name in unique_containers:
            lines.append(f"- {name}")
    else:
        lines.append("- No Borg/Borgmatic/backup-related containers were detected from parsed Docker evidence.")

    lines.append("")
    lines.append("### Repository paths")
    if repo_paths:
        for item in repo_paths[:20]:
            lines.append(f"- {item}")
    else:
        lines.append("- No Borg repository path was detected from parsed Docker evidence.")

    lines.append("")
    lines.append("### Restore paths")
    if restore_paths:
        for item in restore_paths[:20]:
            lines.append(f"- {item}")
    else:
        lines.append("- No restore path was detected from parsed Docker evidence.")

    lines.append("")
    lines.append("### Backup source / config paths")
    if source_paths:
        for item in source_paths[:25]:
            lines.append(f"- {item}")
    else:
        lines.append("- No extra backup source/config paths were detected.")

    lines.append("")
    lines.append("### AppData backup visibility")
    if appdata_backup_access:
        for item in appdata_backup_access[:20]:
            lines.append(f"- {item}")
    else:
        lines.append("- No `/DATA/AppData` backup visibility was detected in parsed backup mounts.")

    lines.append("")
    lines.append("### Paths needing extra verification")
    if risky_paths:
        for item in risky_paths[:20]:
            lines.append(f"- {item}")
    else:
        lines.append("- No obvious `/DATA/.media`, CasaOS `.media`, or old `/dev`-style backup paths were detected.")

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- A backup UI showing a repo path does not prove the repo is healthy.")
    lines.append("- The repo path must match an active mounted disk, not just a visible folder.")
    lines.append("- Restore paths should be checked before depending on them.")
    lines.append("- This layer verifies backup path exposure only. It does not yet prove last backup success, repo integrity, or key safety.")

    return {
        "lines": lines,
        "next_step": "Verify the repository path with active findmnt output, then confirm the Borg repo/key/last backup status before relying on the backup.",
        "forum_summary": "Backup paths should be verified against active mounts before relying on them. A visible Borg repo folder is not enough. Confirm the repo path, restore path, key safety, and last successful backup before treating backups as protected.",
    }
