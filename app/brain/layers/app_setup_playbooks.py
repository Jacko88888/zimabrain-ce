APP_ALIASES = {
    "immich": ["immich"],
    "jellyfin": ["jellyfin"],
    "qbittorrent": ["qbittorrent", "qbitt"],
    "nextcloud": ["nextcloud"],
    "tailscale": ["tailscale"],
    "adguard": ["adguard", "adguardhome", "adguard home"],
    "radarr": ["radarr"],
    "sonarr": ["sonarr"],
    "sabnzbd": ["sabnzbd", "sab"],
    "ollama": ["ollama"],
    "open-webui": ["open-webui", "open_webui", "open webui"],
    "cloudflared": ["cloudflare", "cloudflared", "cloudflare tunnel", "clouflare", "cloudfare", "cloudflair", "clodflare"],
    "wazuh": ["wazuh"],
    "netdata": ["netdata", "netdata cloud"],
    "portainer": ["portainer"],
    "home-assistant": ["home assistant", "home-assistant", "homeassistant"],
    "borg-web-ui": ["borg web ui", "borg-web-ui", "borg ui"],
}

SETUP_GUIDES = {
    "immich": [
        "Choose the storage location first, before installing or changing paths.",
        "Use a stable mounted path for uploads and external libraries.",
        "Verify the database, Redis, machine-learning, and server containers are created together.",
        "Do not move the upload folder until the active mount path is confirmed.",
    ],
    "jellyfin": [
        "Create or confirm the media folder on the host first.",
        "Map the host media folder into the Jellyfin container.",
        "Inside Jellyfin, add the library using the container path, not the host path.",
        "If movies do not show, verify the bind mount and rescan the library.",
    ],
    "qbittorrent": [
        "Choose completed and incomplete download folders first.",
        "Use the same container-side download path if Radarr/Sonarr/SABnzbd will use it.",
        "Verify permissions on the host download folder.",
        "Do not mix host paths and container paths inside app settings.",
    ],
    "nextcloud": [
        "Confirm where user data will live before installation.",
        "Avoid moving data folders until the active mount path and permissions are verified.",
        "Check database and app data paths separately.",
    ],
    "tailscale": [
        "Install and authenticate Tailscale first.",
        "Confirm the ZimaOS device appears in the tailnet.",
        "Use Tailscale for private access before exposing ports publicly.",
    ],
    "adguard": [
        "Confirm which device will provide DNS on the LAN.",
        "Check port conflicts before enabling DNS service.",
        "Only change router DNS after AdGuard is confirmed reachable.",
    ],
    "ollama": [
        "Confirm model storage location first.",
        "Check whether GPU runtime is required before installing large models.",
        "Verify Ollama port and model path after install.",
    ],
    "open-webui": [
        "Confirm Open WebUI data path first.",
        "Verify the Ollama URL/port it will connect to.",
        "Check authentication and exposed port before remote access.",
    ],
    "cloudflared": [
        "Create the tunnel and token from Cloudflare first.",
        "Map only the service you intend to expose.",
        "Avoid exposing admin dashboards unless access control is confirmed.",
    ],
    "wazuh": [
        "Confirm whether this is for monitoring only or active security alerting.",
        "Choose a stable AppData location before installing.",
        "Verify container health, ports, and storage use after install.",
        "Do not expose the dashboard publicly unless access control is confirmed.",
    ],
    "netdata": [
        "Confirm whether you want local Netdata only or Netdata Cloud connection.",
        "Verify the container is healthy before claiming the node in Netdata Cloud.",
        "Check exposed ports and avoid public access unless access control is confirmed.",
    ],
    "portainer": [
        "Confirm whether Portainer is needed before adding another Docker management UI.",
        "Verify Docker socket access and keep it private.",
        "Do not expose Portainer publicly unless strong access control is confirmed.",
    ],
    "home-assistant": [
        "Confirm storage location before installing.",
        "Check whether host networking, USB devices, or Zigbee/Z-Wave passthrough is required.",
        "Verify container state, ports, and mapped config path after install.",
    ],
    "borg-web-ui": [
        "Confirm the Borg repository path is on an active mounted disk.",
        "Confirm restore path and AppData visibility.",
        "Verify repo keys and last backup status before relying on the UI.",
    ],
}


def _detect_app(question):
    q = (question or "").lower()
    for app, aliases in APP_ALIASES.items():
        if any(alias in q for alias in aliases):
            return app
    return "app"


def _find_container_lines(bundle, app):
    evidence = bundle.get("same_report_evidence", {})
    docker_ps = evidence.get("docker_ps", "")
    docker_access = evidence.get("docker_access", "")
    lines = []

    aliases = APP_ALIASES.get(app, [app])

    for src in [docker_ps, docker_access]:
        for line in (src or "").splitlines():
            low = line.lower()
            if app != "app" and any(alias in low for alias in aliases):
                clean = line.strip()
                if clean and clean not in lines:
                    lines.append(clean)

    return lines[:12]


def _is_setup_question(q):
    return any(x in q for x in [
        "setup", "set up", "install", "how to", "configure", "configuration",
        "first time", "new install", "not installed", "add app"
    ])


def _is_version_question(q):
    return any(x in q for x in ["latest", "version", "update", "upgrade"])


def answer(bundle, question=""):
    app = _detect_app(question)
    q = (question or "").lower()

    setup_question = _is_setup_question(q)
    version_question = _is_version_question(q)

    lines = []
    lines.append("- This is an app setup / app version playbook question.")
    lines.append("- The answer uses local dashboard/Docker evidence first and does not pretend to know online release data.")
    lines.append("")

    lines.append("### App detected")
    lines.append(f"- {app}")

    evidence_lines = _find_container_lines(bundle, app)
    app_found = bool(evidence_lines)

    lines.append("")
    lines.append("### Local evidence found")
    if app_found:
        for line in evidence_lines:
            lines.append(f"- {line}")
    else:
        lines.append("- No matching local container/app evidence was found in the current report.")
        lines.append("- This may mean the app is not installed, not running, named differently, or not captured in this report.")

    lines.append("")
    lines.append("### Setup / version guidance")

    if version_question:
        lines.append("- I can verify the installed container/image/tag from local evidence if it appears in the report.")
        lines.append("- I cannot confirm the latest upstream release from local dashboard evidence alone.")
        lines.append("- To confirm latest version safely, compare the installed image/tag with the official app source or ZimaOS app store metadata.")
        if not app_found:
            lines.append("- Since no local app evidence was found, first confirm whether the app is installed before checking for updates.")

    if setup_question or not app_found:
        guide = SETUP_GUIDES.get(app)
        if guide:
            lines.append("")
            lines.append("### Safe setup checklist")
            lines.append("- This setup checklist is playbook guidance. It is not fully verified from same-report evidence.")
            for item in guide:
                lines.append(f"- {item}")
        else:
            lines.append("")
            lines.append("### Safe setup checklist")
            lines.append("- This setup checklist is playbook guidance. It is not fully verified from same-report evidence.")
            lines.append("- Confirm the app you want to install.")
            lines.append("- Choose the storage location before installing.")
            lines.append("- Verify the active mounted path before mapping volumes.")
            lines.append("- Check ports before exposing the app on the network.")
            lines.append("- Keep app data and media paths separate where possible.")

    if app_found and not version_question and not setup_question:
        if app == "immich":
            lines.append("- For Immich, verify upload path, external library path, database/Redis containers, and Docker bind mounts.")
        elif app == "jellyfin":
            lines.append("- For Jellyfin, verify media folder path, Docker bind mount, permissions, and container library path.")
        elif app == "qbittorrent":
            lines.append("- For qBittorrent, verify download path, incomplete path, permissions, and matching paths with Radarr/Sonarr/SABnzbd.")
        else:
            lines.append("- Verify the app container, mapped volumes, published ports, and active storage mount.")

    if app_found:
        next_step = f"Verify the installed {app} container, bind mounts, ports, and active storage path before changing settings."
        forum_summary = f"ZimaBrain found local evidence for {app}. Verify container state, bind mounts, ports, and active storage paths before changing settings."
    else:
        next_step = f"Confirm whether {app} is installed. If not installed, choose the storage path and port plan before installing."
        forum_summary = f"No local evidence for {app} was found in this report. Treat this as a setup question: choose storage paths, confirm ports, and install only after the active mount path is known."

    if version_question:
        next_step = f"Check the installed {app} image/tag first, then compare it against the official release/app-store source before updating."
        forum_summary = f"This looks like an {app} version/update question. ZimaBrain can verify local installed evidence, but should not claim the latest release unless official release/app-store evidence is available."

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
    }
