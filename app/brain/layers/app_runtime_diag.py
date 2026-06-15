APP_ALIASES = {
    "jellyfin": ["jellyfin"],
    "immich": ["immich"],
    "qbittorrent": ["qbittorrent", "qbit", "qbitt"],
    "radarr": ["radarr"],
    "sonarr": ["sonarr"],
    "sabnzbd": ["sabnzbd", "sab"],
    "nextcloud": ["nextcloud"],
}


def _norm(value):
    return (value or "").lower()


def _detect_app(question):
    q = _norm(question)
    for app, aliases in APP_ALIASES.items():
        if any(alias in q for alias in aliases):
            return app
    return None


def _detect_symptom(question):
    q = _norm(question)

    if any(x in q for x in ["not downloading", "no download", "download stuck", "downloads stuck", "stalled"]):
        return "download failure"

    if any(x in q for x in ["no movies", "movies missing", "library empty", "media missing", "not showing movies"]):
        return "media library not showing"

    if any(x in q for x in ["photos missing", "photos not showing", "no photos"]):
        return "photo library not showing"

    if any(x in q for x in ["cannot import", "not importing", "import failed"]):
        return "import failure"

    if any(x in q for x in ["path problem", "path issue", "wrong path", "mapping problem"]):
        return "path mapping issue"

    return "app runtime issue"


def _report_has_app(report, app):
    if not app:
        return False
    return app in _norm(report)


def answer(bundle, question):
    report = bundle.get("report", "") or ""
    app = _detect_app(question)
    symptom = _detect_symptom(question)

    lines = []
    lines.append("- This is an app runtime diagnostic question.")
    lines.append(f"- Detected symptom: {symptom}")

    if not app:
        lines.append("- No app name was detected from the question.")
        lines.append("- No matching local container/app evidence was found.")
        return {
            "lines": lines,
            "next_step": "Ask which app is affected, then check container status, logs, bind mounts, and the exact storage path.",
            "forum_summary": "The app runtime issue is not verified because the affected app was not identified.",
        }

    lines.append(f"- Detected app: {app}")

    if not _report_has_app(report, app):
        lines.append(f"- {app} was not found in the current report.")
        lines.append("- No matching local container/app evidence was found.")
        return {
            "lines": lines,
            "next_step": f"Collect container status and logs for {app} before giving repair steps.",
            "forum_summary": f"The {app} issue is not verified because the current report does not contain matching app evidence.",
        }

    lines.append(f"- Matching same-report app evidence was found for {app}.")
    lines.append("- Root cause is not fully verified from same-report evidence.")
    lines.append("")
    lines.append("### Runtime checks required")
    lines.append("- Container running state")
    lines.append("- Recent app/container logs")
    lines.append("- Docker bind mounts")
    lines.append("- Host storage path exists")
    lines.append("- App internal path matches the host bind path")

    if symptom == "download failure":
        lines.append("")
        lines.append("### Download failure focus")
        lines.append("- Check download client container state.")
        lines.append("- Check download path bind mount.")
        lines.append("- Check free space on the target storage path.")
        lines.append("- Check whether the target path is read-only.")

    elif symptom in ["media library not showing", "photo library not showing"]:
        lines.append("")
        lines.append("### Library visibility focus")
        lines.append("- Check library path configured inside the app.")
        lines.append("- Check Docker bind mount source path.")
        lines.append("- Check permissions on the media/photo folder.")
        lines.append("- Check whether the app can see the folder from inside the container.")

    elif symptom == "import failure":
        lines.append("")
        lines.append("### Import failure focus")
        lines.append("- Check download/import source path.")
        lines.append("- Check final library destination path.")
        lines.append("- Check path mapping between downloader and media manager.")

    elif symptom == "path mapping issue":
        lines.append("")
        lines.append("### Path mapping focus")
        lines.append("- Check the host path.")
        lines.append("- Check the container path.")
        lines.append("- Check whether related apps use the same internal path mapping.")

    return {
        "lines": lines,
        "next_step": f"Check {app} container status, logs, bind mounts, and exact storage paths before attempting repair.",
        "forum_summary": f"{app} is present in the current report, but the root cause of the {symptom} is only partially verified until logs and bind mounts are checked.",
    }
