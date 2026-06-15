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


def _is_storage_path(path):
    return (
        path.startswith("/DATA")
        or path.startswith("/media")
        or "/.media/" in path
        or path.startswith("/var/lib/casaos_data/.media")
    )


def answer(bundle):
    lines = []
    rows = _parse_docker_access(bundle)

    lines.append("- This is a Docker bind-mount verification question.")
    lines.append("- The answer comes from the Docker Bind-Mount Verifier using Docker inspect evidence.")
    lines.append("")

    if not rows:
        lines.append("No Docker bind-mount evidence was parsed from the current report.")
        return {
            "lines": lines,
            "next_step": "Run read-only Docker inspect commands to collect container bind-mount evidence before changing app paths.",
            "forum_summary": "No Docker bind-mount evidence was available in the current report. Collect docker inspect mount data before changing any app paths.",
        }

    full_data_rw = []
    media_paths = []
    old_or_risky_paths = []
    no_storage_binds = []

    for row in rows:
        name = row["name"]
        mounts = row["mounts"]

        storage_mounts = [m for m in mounts if _is_storage_path(m["source"]) or _is_storage_path(m["dest"])]

        if not storage_mounts:
            no_storage_binds.append(name)
            continue

        for m in storage_mounts:
            src = m["source"]
            dst = m["dest"]
            rw = "rw" if m["rw"] else "ro"

            if src == "/DATA" and m["rw"]:
                full_data_rw.append(f"{name}: {src} -> {dst} {rw}")

            if src.startswith("/media") or dst.startswith("/media"):
                media_paths.append(f"{name}: {src} -> {dst} {rw}")

            if "/dev/" in src or "-/dev/" in src or "/DATA/.media" in src or "/var/lib/casaos_data/.media" in src:
                old_or_risky_paths.append(f"{name}: {src} -> {dst} {rw}")

    lines.append("### Bind-mount findings")

    if full_data_rw:
        lines.append("- Containers with full read-write `/DATA` access:")
        for item in full_data_rw[:20]:
            lines.append(f"  - {item}")
    else:
        lines.append("- No container with full read-write `/DATA` access was detected in parsed bind mounts.")

    if media_paths:
        lines.append("")
        lines.append("- Containers using `/media` paths:")
        for item in media_paths[:30]:
            lines.append(f"  - {item}")
    else:
        lines.append("")
        lines.append("- No `/media` bind paths were detected in parsed bind mounts.")

    if old_or_risky_paths:
        lines.append("")
        lines.append("- Paths needing extra verification:")
        for item in old_or_risky_paths[:30]:
            lines.append(f"  - {item}")
    else:
        lines.append("")
        lines.append("- No obvious old `/dev`-style or CasaOS `.media` bind paths were detected.")

    lines.append("")
    lines.append("### How to interpret this")
    lines.append("- A Docker bind source path must exist and match the active storage mount.")
    lines.append("- A visible folder is not enough. Confirm with `findmnt` before changing app paths.")
    lines.append("- Full `/DATA` read-write access is powerful and should only be used when intentional.")
    lines.append("- Do not recreate apps until the exact source path and app data path are verified.")

    return {
        "lines": lines,
        "next_step": "Compare these Docker bind paths against active findmnt mounts before changing, recreating, or deleting any app path.",
        "forum_summary": "Docker bind mounts should be verified against active findmnt output. Do not rely on visible folders alone, and do not recreate apps until the exact source path, destination path, and active storage mount are confirmed.",
    }
