KNOWN_APPS = {
    "immich": ["immich"],
    "jellyfin": ["jellyfin"],
    "nextcloud": ["nextcloud"],
    "qbittorrent": ["qbittorrent", "qbitt"],
    "radarr": ["radarr"],
    "sonarr": ["sonarr"],
    "sabnzbd": ["sabnzbd", "sab"],
    "ollama": ["ollama"],
    "open-webui": ["open-webui", "open_webui", "open webui"],
    "borg": ["borg", "borgmatic"],
    "mailcow": ["mailcow"],
    "casadrop": ["casadrop"],
}

DOWNLOAD_STACK = {"qbittorrent", "radarr", "sonarr", "sabnzbd"}


def _detect_requested_apps(question):
    q = (question or "").lower()
    hits = []

    for app, needles in KNOWN_APPS.items():
        if any(n in q for n in needles):
            hits.append(app)

    if "download" in q or "downloading" in q or "torrent" in q:
        if "qbittorrent" not in hits:
            hits.append("qbittorrent")

    if any(app in hits for app in DOWNLOAD_STACK):
        for app in ["qbittorrent", "radarr", "sonarr", "sabnzbd"]:
            if app not in hits:
                hits.append(app)

    return hits


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


def _match_app(container_name):
    low = container_name.lower()
    for app, needles in KNOWN_APPS.items():
        if any(n in low for n in needles):
            return app
    return None


def _is_user_storage_path(path):
    return (
        path.startswith("/media")
        or path.startswith("/DATA/.media")
        or path.startswith("/var/lib/casaos_data/.media")
        or path.startswith("/DATA")
    )


def _is_docker_volume_path(path):
    return "/docker/volumes/" in path


def _collect_paths(rows, requested_apps=None):
    requested_apps = set(requested_apps or [])
    focused = bool(requested_apps)

    app_hits = {}
    risky_paths = []
    normal_volume_paths = []
    unknown_storage_paths = []

    for row in rows:
        name = row["name"]
        app = _match_app(name)

        if focused and app not in requested_apps:
            continue

        for m in row["mounts"]:
            src = m["source"]
            dst = m["dest"]
            rw = "rw" if m["rw"] else "ro"

            if not _is_user_storage_path(src) and not _is_user_storage_path(dst):
                continue

            item = f"{name}: {src} -> {dst} {rw}"

            if app:
                app_hits.setdefault(app, []).append(item)
            else:
                unknown_storage_paths.append(item)

            if src.startswith("/DATA/.media") or src.startswith("/var/lib/casaos_data/.media") or "-/dev/" in src:
                risky_paths.append(item)

            if _is_docker_volume_path(src):
                normal_volume_paths.append(item)

    return app_hits, risky_paths, normal_volume_paths, unknown_storage_paths


def answer(bundle, question=""):
    lines = []
    rows = _parse_docker_access(bundle)
    requested_apps = _detect_requested_apps(question)
    focused = bool(requested_apps)

    lines.append("- This is an app storage-path verification question.")
    lines.append("- The answer comes from the App Storage-Path Verifier using Docker inspect mount evidence.")
    lines.append("")

    if focused:
        lines.append("### Focused app check")
        lines.append(f"- Requested app/stack: {', '.join(requested_apps)}")
        lines.append("- This answer is limited to the requested app or download stack.")
        lines.append("")

    if not rows:
        lines.append("No Docker mount evidence was parsed from the current report.")
        return {
            "lines": lines,
            "next_step": "Collect Docker inspect mount evidence before changing any app storage paths.",
            "forum_summary": "No app storage-path evidence was available. Collect Docker inspect mount data before changing app paths.",
        }

    app_hits, risky_paths, normal_volume_paths, unknown_storage_paths = _collect_paths(rows, requested_apps)

    lines.append("### App storage paths")

    if app_hits:
        for app in sorted(app_hits):
            lines.append(f"- {app}:")
            for item in app_hits[app][:16]:
                lines.append(f"  - {item}")
    else:
        if focused:
            lines.append("- No matching Docker mount evidence was found for the requested app/stack in the current report.")
            lines.append("- This may mean the app is not installed, not running, named differently, or not captured in the current evidence.")
        else:
            lines.append("- No known app storage paths were matched from parsed Docker evidence.")

    lines.append("")
    lines.append("### Paths needing extra verification")

    if risky_paths:
        for item in risky_paths[:16]:
            lines.append(f"- {item}")
    else:
        lines.append("- No obvious CasaOS `.media`, `/DATA/.media`, or old `/dev`-style paths were detected for this scope.")

    if not focused:
        lines.append("")
        lines.append("### Normal Docker volume-style paths")

        if normal_volume_paths:
            lines.append("- Docker volume paths can be normal, but still need the source disk verified if they live under `/media`.")
            for item in normal_volume_paths[:18]:
                lines.append(f"- {item}")
        else:
            lines.append("- No Docker volume-style storage paths were detected in known app mounts.")

    lines.append("")
    lines.append("### How to interpret this")

    if focused and "jellyfin" in requested_apps:
        lines.append("- For Jellyfin, the library path inside Jellyfin must match the container destination path, not the host path.")
        lines.append("- If movies are missing, verify the Docker bind mount and then rescan the Jellyfin library.")
    elif focused and any(app in requested_apps for app in DOWNLOAD_STACK):
        lines.append("- For qBittorrent/Radarr/Sonarr/SABnzbd, all containers must agree on the same container-side download path.")
        lines.append("- A common problem is SAB/qBittorrent downloading to one container path while Radarr/Sonarr look at another.")
    elif focused and "immich" in requested_apps:
        lines.append("- For Immich, verify upload path, external library path, database path, and the active mounted storage path.")
    else:
        lines.append("- App storage paths should match active storage mounts, not just visible folders.")
        lines.append("- Immich, Jellyfin, Nextcloud, and qBittorrent paths should be checked carefully before reinstalling or changing apps.")

    lines.append("- Do not recreate an app until the exact source path and container destination path are confirmed.")

    if focused:
        next_step = "Verify the focused app's source path against active findmnt output, then confirm the app uses the matching container path."
        forum_summary = f"ZimaBrain checked the requested app/stack only: {', '.join(requested_apps)}. Verify the source path against active mount evidence and confirm the container destination path before changing app settings."
    else:
        next_step = "Verify the listed app source paths against active findmnt output before changing app settings, reinstalling apps, or moving data."
        forum_summary = "Known app storage paths should be verified against active mount evidence before changing apps. Pay special attention to Immich, Jellyfin, Nextcloud, qBittorrent, and any paths under /DATA/.media or /var/lib/casaos_data/.media."

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
    }
