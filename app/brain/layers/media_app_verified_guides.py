import re
from brain.layers.app_identity_guard import resolve_app_identity

APP_ALIASES = {
    "immich": ["immich"],
    "jellyfin": ["jellyfin"],
    "jellyseerr": ["jellyseerr", "seerr", "jellyseer", "jelly seerr"],
    "jellybridge": ["jellybridge", "jelly bridge"],
}

GUIDES = {
    "immich": {
        "title": "Immich verified install guide",
        "manual": "Official ZimaOS Immich guide available in the local ZimaOS manual index.",
        "order": [
            "Verify the ZimaOS app/config path first. Prefer a stable AppData path such as /DATA/AppData/immich or the actual ZimaOS-created Immich AppData folder.",
            "Verify upload/originals storage before importing photos. Do not move the upload folder until the active mount path is confirmed.",
            "Verify external library bind mounts. The host photo folder must be visible inside the Immich container at the configured container path.",
            "Verify the full Immich stack is running: server, postgres, redis, and machine-learning.",
            "Verify database location. The Postgres data path should live under the Immich AppData/project folder, for example /DATA/AppData/big-bear-immich/pgdata or the actual configured equivalent.",
            "Verify permissions on upload and external library folders before blaming Immich scanning.",
            "Verify GPU/machine-learning/transcoding only after the base stack and storage are healthy.",
            "Before upgrade, back up AppData, database data, and upload/originals paths. Do not upgrade blindly if the database path is unknown.",
            "Collect logs before asking for help: immich-server, immich-postgres, immich-redis, immich-machine-learning, plus bind mount evidence.",
        ],
        "common_issues": [
            "Photos do not appear because the external library path is mounted on the host but not inside the container.",
            "Upload fails because the upload/originals folder is on the wrong disk or has wrong permissions.",
            "Database problems occur when pgdata is moved, deleted, or not backed up.",
            "Machine-learning issues are separate from storage/import issues and should be checked after the main containers are healthy.",
        ],
    },
    "jellyfin": {
        "title": "Jellyfin verified install guide",
        "manual": "Official ZimaOS Jellyfin/media server guide available in the local ZimaOS manual index.",
        "order": [
            "Verify the ZimaOS app/config path first. Prefer a stable AppData path such as /DATA/AppData/jellyfin or the actual ZimaOS-created Jellyfin AppData folder.",
            "Verify the media folder host path before adding the library. For external HDD/RAID, confirm the active /media path or RAID mount path first.",
            "Verify Jellyfin bind mounts. The host Movies/TV/Music folder must be visible inside the Jellyfin container.",
            "Verify permissions. Jellyfin must be able to read the media folders and traverse parent folders.",
            "Verify the container is running and the web UI port is reachable before rescanning libraries.",
            "Verify library scan logs before reinstalling. Reinstalling will not fix a wrong bind mount or permission issue.",
            "For hardware transcoding, verify Intel VAAPI, NVIDIA, or other GPU device visibility before enabling transcoding in Jellyfin.",
            "For NVIDIA, confirm nvidia-smi/driver visibility and container GPU access. For Intel, confirm VAAPI/render device visibility.",
            "Back up Jellyfin config metadata under AppData before major changes or reinstall.",
            "Collect logs before asking for help: Jellyfin container logs, bind mount list, media path ls output, permissions, and GPU check output if transcoding is involved.",
        ],
        "common_issues": [
            "Library scan finds nothing because the media path selected in Jellyfin is not the path mounted inside the container.",
            "External disk appears in Files but not inside Jellyfin because the container bind mount is wrong.",
            "Permission issues look like empty libraries or failed scans.",
            "Hardware transcoding problems should not be mixed with basic library path problems.",
        ],
    },
    "jellyseerr": {
        "title": "Jellyseerr / Seerr verified install guide",
        "manual": "This is integration guidance. Jellyseerr/Seerr is not treated as a default Jellyfin App Store install unless confirmed by the app index or local evidence.",
        "order": [
            "Verify Jellyfin works first. Do not configure Jellyseerr before Jellyfin is reachable and libraries work.",
            "Verify whether Jellyseerr/Seerr is installed from an app store or manually through Docker/Compose.",
            "Verify the Jellyseerr container is running before opening configuration.",
            "Use the correct Jellyfin URL from inside Docker. If containers are on different networks, use the host IP or correct Docker network name.",
            "Create and verify the Jellyfin API key.",
            "Only add Radarr/Sonarr if the user wants full request automation. Jellyseerr can connect to Jellyfin first without full automation.",
            "Verify network access from Jellyseerr to Jellyfin before changing API settings.",
            "Collect logs before asking for help: Jellyseerr logs, Jellyfin URL used, API key status, Docker network, and container status.",
        ],
        "common_issues": [
            "Jellyseerr cannot connect because it uses localhost inside the container instead of the Jellyfin host/container address.",
            "Missing or wrong Jellyfin API key.",
            "Radarr/Sonarr are configured before Jellyfin connection is proven.",
            "Container is installed but not running before configuration starts.",
        ],
    },
    "jellybridge": {
        "title": "JellyBridge verified install guide",
        "manual": "This is dependency/order guidance. JellyBridge must be treated as an integration layer, not the first app to configure.",
        "order": [
            "Explain what JellyBridge is before installing: it bridges/integrates services around Jellyfin/Jellyseerr rather than replacing them.",
            "Verify Jellyfin is working first: container running, libraries visible, web UI reachable.",
            "Verify Jellyseerr/Seerr is working second: container running, Jellyfin API key accepted, network path correct.",
            "Only then configure JellyBridge.",
            "Verify whether JellyBridge is a plugin, companion container, or manual Compose service in the user’s chosen setup.",
            "Verify URLs used between containers. Docker localhost usually means the same container, not the other app.",
            "Verify logs/checks when it fails: JellyBridge logs, Jellyfin logs, Jellyseerr logs, API key status, and network reachability.",
        ],
        "common_issues": [
            "User installs JellyBridge before Jellyfin and Jellyseerr are working.",
            "Dependency app is missing or not reachable.",
            "Wrong internal URL or Docker network mismatch.",
            "No logs are provided, so failure point cannot be verified.",
        ],
    },
}


def _norm(text):
    text = (text or "").lower()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def detect_app(question):
    q = _norm(question)

    guarded_app = resolve_app_identity(question)
    if guarded_app:
        return guarded_app

    # Integration apps must be checked before Jellyfin because questions often contain both,
    # for example: "setup Jellyseerr with Jellyfin".
    priority = ["jellybridge", "jellyseerr", "immich", "jellyfin"]

    for app in priority:
        for alias in APP_ALIASES.get(app, []):
            if _norm(alias) in q:
                return app

    # Then check every other supported app profile.
    for app, aliases in APP_ALIASES.items():
        if app in priority:
            continue
        for alias in aliases:
            if _norm(alias) in q:
                return app

    return ""


def _local_evidence(bundle, app):
    evidence = bundle.get("same_report_evidence", {}) if isinstance(bundle, dict) else {}
    docker_ps = evidence.get("docker_ps", "") or ""
    docker_access = evidence.get("docker_access", "") or ""

    aliases = [_norm(x) for x in APP_ALIASES.get(app, [app])]
    found = []

    for src in [docker_ps, docker_access]:
        for raw in src.splitlines():
            clean = raw.strip()
            if not clean:
                continue

            name = clean.split("|", 1)[0].strip().lstrip("/")
            n = _norm(name)

            if any(a and (a == n or a in n or n in a) for a in aliases):
                if clean not in found:
                    found.append(clean)

    return found[:10]



def _install_steps(app):
    app_label = {
        "homeassistant": "Home Assistant",
        "qbittorrent": "qBittorrent",
        "sabnzbd": "SABnzbd",
        "cloudflared": "Cloudflared",
        "nextcloud": "Nextcloud",
        "pihole": "Pi-hole",
        "mariadb": "MariaDB",
    }.get(app, app)

    appdata_name = {
        "homeassistant": "home-assistant",
        "qbittorrent": "qbittorrent",
        "sabnzbd": "sabnzbd",
        "cloudflared": "cloudflared",
        "pihole": "pihole",
    }.get(app, app)

    if app == "mariadb":
        return [
            "Step 1 — Confirm MariaDB is actually required. Many apps already include their own database container, so do not install another MariaDB unless the app specifically needs an external database.",
            "Step 2 — Check if a MariaDB/MySQL container already exists. If one is already running, confirm whether you can use it or whether the new app needs a separate database.",
            "Step 3 — Choose the database storage path before installing. Use a stable path such as /DATA/AppData/mariadb or the actual ZimaOS-created MariaDB folder.",
            "Step 4 — Do not place database data on a temporary, duplicate, or ghost /media path. Database storage must be stable before first start.",
            "Step 5 — Check the port plan. MariaDB normally uses container port 3306. If another database already uses host port 3306, choose a different host port.",
            "Step 6 — Install MariaDB from the ZimaOS App Store if available. If not available, use a trusted Docker/Compose source.",
            "Step 7 — Record the database name, username, password, and root password. Do not continue until these are known.",
            "Step 8 — Connect the dependent app using the correct Docker network name, container name, or host IP. Do not use localhost unless both services are inside the same container.",
            "Step 9 — Test the dependent app connection before importing real data.",
            "Step 10 — Back up the database volume before upgrades, reinstalls, migration, or repair.",
            "Step 11 — If it fails, collect MariaDB logs, dependent app logs, bind mounts, port mapping, credentials used, and disk free space before asking for help.",
        ]

    if app == "nextcloud":
        return [
            "Step 1 — Open ZimaOS App Store and search for Nextcloud. If it is available, install it from the App Store first.",
            "Step 2 — Before clicking install, decide where the Nextcloud user data will live. Do not leave this unclear.",
            "Step 3 — Confirm the config/AppData path, normally /DATA/AppData/nextcloud or the actual ZimaOS-created Nextcloud AppData folder.",
            "Step 4 — Choose the data path. For large file storage, use a stable mounted disk path, not a temporary or duplicate /media ghost path.",
            "Step 5 — Check the Installed Apps / Port Map panel and confirm the Nextcloud web port is not conflicting with another app.",
            "Step 6 — Install and start Nextcloud.",
            "Step 7 — Create the admin account only after the data path and database path are confirmed.",
            "Step 8 — If using external storage, confirm the host folder is bind-mounted into the container before adding it inside Nextcloud.",
            "Step 9 — Check permissions on the data/external storage folders before uploading files.",
            "Step 10 — Back up AppData, database data, and the Nextcloud data folder before upgrades, reinstalls, or path changes.",
            "Step 11 — If it fails, collect Nextcloud container logs, database logs, bind mounts, ports, disk free space, and the exact data path before asking for help.",
        ]

    if app == "pihole":
        return [
            "Step 1 — Open ZimaOS App Store and search for Pi-hole. If available, install it from the App Store first.",
            "Step 2 — Decide whether Pi-hole will be DNS only or DNS plus DHCP. Do not enable DHCP until the router/LAN plan is confirmed.",
            "Step 3 — Confirm the config/AppData path, normally /DATA/AppData/pihole or the actual ZimaOS-created Pi-hole folder.",
            "Step 4 — Check the port plan before install. Pi-hole commonly needs DNS port 53, a web UI port, and optional DHCP ports if DHCP is enabled.",
            "Step 5 — Check the Installed Apps / Port Map panel for conflicts, especially port 53.",
            "Step 6 — Install and start Pi-hole.",
            "Step 7 — Verify the container is running and the web UI opens.",
            "Step 8 — Point only one test client to Pi-hole first. Do not change whole-network DNS until the test works.",
            "Step 9 — Only change router DNS after Pi-hole is confirmed healthy.",
            "Step 10 — Back up Pi-hole config before upgrades or reinstall.",
            "Step 11 — If it fails, collect Pi-hole container logs, port map, DNS settings, router DNS/DHCP settings, and container bind mounts before asking for help.",
        ]

    if app == "qbittorrent":
        return [
            "Step 1 — Install qBittorrent from ZimaOS App Store if available. If not available, use a trusted Docker/Compose source.",
            "Step 2 — Before install, choose incomplete and completed download folders.",
            "Step 3 — Use a stable download path on /DATA or an active /media mounted disk.",
            "Step 4 — Bind the host download folder into the container.",
            "Step 5 — Use the container-mounted path inside qBittorrent settings, not the host-only path.",
            "Step 6 — Confirm the Web UI port is free in the Port Map panel.",
            "Step 7 — Start qBittorrent and verify the Web UI opens.",
            "Step 8 — Test one small download before connecting Radarr/Sonarr.",
            "Step 9 — If downloads stall, collect qBittorrent logs, bind mounts, download path, permissions, and disk free space.",
        ]

    if app in {"portainer", "netdata", "wazuh"}:
        return [
            f"Step 1 — Check first whether {app_label} is already installed. Do not install a duplicate management/security dashboard.",
            f"Step 2 — Install {app_label} from ZimaOS App Store if available, otherwise use a trusted Docker/Compose source.",
            f"Step 3 — Use a stable config/AppData path under /DATA/AppData/{appdata_name} or the actual ZimaOS-created folder.",
            "Step 4 — Check the Port Map panel before choosing web/admin ports.",
            "Step 5 — If Docker socket is required, treat it as high risk and keep the dashboard private.",
            "Step 6 — Do not expose the dashboard publicly unless access control is confirmed.",
            "Step 7 — Start the container and verify container state, ports, bind mounts, and logs.",
            "Step 8 — Back up AppData before upgrade or reinstall.",
        ]

    if app in {"jellyseerr", "jellybridge"}:
        return [
            "Step 1 — Do not install/configure this integration first.",
            "Step 2 — Confirm Jellyfin is already working: web UI reachable, libraries visible, and media paths correct.",
            "Step 3 — Confirm the dependency container is running before configuration.",
            "Step 4 — Confirm the correct internal URL. Inside Docker, localhost usually means the same container, not the other app.",
            "Step 5 — Confirm API key or token requirements before saving configuration.",
            "Step 6 — Only after the dependency works, install/configure the integration using the chosen Docker/Compose or app-store method.",
            "Step 7 — Collect logs from both the integration and the dependency app before asking for help.",
        ]

    if app in {"immich", "jellyfin", "plex", "emby"}:
        return [
            f"Step 1 — Open ZimaOS App Store and search for {app_label}. If it is available, install it from the App Store first.",
            "Step 2 — Before installing, confirm where the app config and metadata will live.",
            f"Step 3 — Confirm the AppData path, normally under /DATA/AppData/{appdata_name} or the actual ZimaOS-created folder.",
            "Step 4 — Choose the media/upload/library path before install, especially if using external HDD, RAID, or /media paths.",
            "Step 5 — Verify the host folder will be bind-mounted into the container.",
            "Step 6 — Install and start the app.",
            "Step 7 — Verify the container is running and the web UI opens.",
            "Step 8 — Add libraries/uploads only after the mounted container path is confirmed.",
            "Step 9 — Check permissions before scanning, importing, or uploading.",
            "Step 10 — Configure GPU/transcoding only after the basic app and storage paths work.",
            "Step 11 — Back up AppData and database/config folders before upgrade or reinstall.",
            "Step 12 — If it fails, collect container logs, bind mounts, media path listing, permissions, and GPU checks if transcoding is involved.",
        ]

    return [
        f"Step 1 — Open ZimaOS App Store and search for {app_label}. If it is available, install it from the App Store first.",
        f"Step 2 — If {app_label} is not in the App Store, check the third-party app-store index or use a trusted Docker/Compose source.",
        f"Step 3 — Before installing, choose the config/AppData path, normally under /DATA/AppData/{appdata_name} or the actual ZimaOS-created folder.",
        "Step 4 — Choose any data/media/download/database path before install, especially if using external HDD, RAID, or /media paths.",
        "Step 5 — Check the Installed Apps / Port Map panel before choosing ports.",
        "Step 6 — Review risk flags before install: docker.sock, host networking, privileged mode, latest tag, exposed admin UI.",
        "Step 7 — Install the app only after paths and ports are clear.",
        "Step 8 — After install, verify container state, bind mounts, ports, permissions, and logs.",
        "Step 9 — Do not expose admin dashboards publicly unless access control is confirmed.",
        "Step 10 — If it fails, collect container logs, compose/app config, bind mounts, ports, storage path, permissions, and disk free space before asking for help.",
    ]



def _extract_generic_app_name(question):
    q = (question or "").strip()
    low = _norm(q)

    remove_phrases = [
        "how to install", "how do i install", "can i install",
        "how to setup", "how do i setup", "setup", "set up",
        "install", "configure", "on zimaos", "on zima", "zimaos", "zima",
    ]

    cleaned = low
    for phrase in remove_phrases:
        cleaned = cleaned.replace(_norm(phrase), " ")

    cleaned = " ".join(cleaned.split())

    if not cleaned:
        return ""

    bad = {"app", "container", "docker", "service", "server"}
    words = [w for w in cleaned.split() if w not in bad]

    if not words:
        return ""

    return " ".join(words[:3])



def _invalid_generic_app_name(app_name):
    name = _norm(app_name or "")

    blocked = {
        "bullshit", "shit", "fuck", "fake", "fake app", "fakeapp",
        "test", "test app", "testapp", "random", "random app",
        "asdf", "qwerty", "blah", "blahblah", "nothing",
    }

    if not name:
        return True

    if name in blocked:
        return True

    # Avoid creating fake /DATA/AppData paths for obvious nonsense.
    if len(name) < 2:
        return True

    return False

def _generic_install_steps(app_name):
    label = app_name or "this app"
    safe_name = _norm(label).replace(" ", "-") or "app"

    return [
        f"Step 1 — Confirm what {label} is needed for before installing it.",
        "Step 2 — Check whether the app already exists in the ZimaOS App Store.",
        "Step 3 — If it is not in the App Store, check the third-party app-store index or use a trusted Docker/Compose source.",
        f"Step 4 — Choose the config/AppData path before install, normally under /DATA/AppData/{safe_name} or the actual ZimaOS-created folder.",
        "Step 5 — Choose any data/media/download/database path before install, especially if using external HDD, RAID, or /media paths.",
        "Step 6 — Check the Installed Apps / Port Map panel before choosing ports.",
        "Step 7 — Review risk flags before install: docker.sock, host networking, privileged mode, latest tag, exposed admin UI.",
        "Step 8 — Install only after paths and ports are clear.",
        "Step 9 — After install, verify container state, bind mounts, ports, permissions, and logs.",
        "Step 10 — Do not expose admin dashboards publicly unless access control is confirmed.",
        "Step 11 — If it fails, collect container logs, compose/app config, bind mounts, ports, storage path, permissions, and disk free space before asking for help.",
    ]


def _generic_common_issues(app_name):
    label = app_name or "the app"

    return [
        f"{label} is installed but the data path is not mounted inside the container.",
        "The app is using the wrong host path or a stale /media ghost path.",
        "The selected port is already used by another app.",
        "The app cannot write because of folder permissions.",
        "The user exposes an admin UI before access control is confirmed.",
        "No logs, ports, mounts, or path evidence are provided, so the failure point cannot be verified.",
    ]

def _pihole_post_install_steps():
    return [
        "Step 1 — Confirm the Pi-hole container is healthy.",
        "Step 2 — Confirm the web UI opens on the mapped web port.",
        "Step 3 — Confirm DNS port 53 TCP and UDP are mapped and not conflicting.",
        "Step 4 — Confirm the config bind mount is stable, normally /DATA/AppData/pihole/etc/pihole.",
        "Step 5 — Do not enable Pi-hole DHCP unless router DHCP has been disabled or the LAN DHCP plan is confirmed.",
        "Step 6 — Test one client first by manually setting that client DNS to the ZimaOS/Pi-hole IP.",
        "Step 7 — Confirm the test client can resolve websites and that queries appear in Pi-hole.",
        "Step 8 — Only after the one-client test works, change router DNS for the wider network.",
        "Step 9 — Keep a rollback plan: know how to change router DNS back to automatic/ISP DNS.",
        "Step 10 — If DNS fails, collect Pi-hole logs, port map, router DNS/DHCP settings, and client DNS settings.",
    ]

def answer(bundle, question=""):
    app = detect_app(question)
    lines = []

    if not app:
        lines.append("- This is an unverified/custom app request.")
        lines.append("- ZimaBrain must confirm app-store/manual/local evidence before giving install steps.")
        lines.append("- This is not a verified ZimaOS App Store or official manual install guide.")
        lines.append("")

        generic_app = _extract_generic_app_name(question)

        lines.append("### Requested app name")
        if generic_app:
            lines.append(f"- {generic_app}")
        else:
            lines.append("- Unknown app")

        if _invalid_generic_app_name(generic_app):
            lines.append("")
            lines.append("### Guide type")
            lines.append("- No install guide generated.")
            lines.append("- The requested app name could not be verified as a real install target.")
            lines.append("- ZimaBrain will not invent AppData paths, ports, or Docker guidance for an obvious fake or unconfirmed app name.")
            lines.append("")
            lines.append("### Next check")
            lines.append("- Confirm the real app name.")
            lines.append("- Confirm whether it exists in the ZimaOS App Store, third-party app-store index, or a trusted Docker/Compose source.")
            lines.append("- Then ask again using the confirmed app name.")

            return {
                "lines": lines,
                "next_step": "Confirm the real app name or trusted source before generating install guidance.",
                "forum_summary": "No install guide generated because the app name was not verified as a real install target.",
                "trust_state": "NOT VERIFIED",
                "trust_title": "❌ NOT VERIFIED",
                "trust_detail": "The requested app name was not verified as a real install target, so no install guide was generated.",
            }

        lines.append("")
        lines.append("### GENERIC INSTALL CHECKLIST")
        lines.append(
            f"- Requested app `{generic_app}` has not been verified against "
            "a dedicated ZimaBrain profile."
        )
        lines.append(
            "- The following is a cautious generic workflow, not a claim that "
            "the app exists in the ZimaOS App Store."
        )
        lines.append(
            "- Confirm the official project and trusted container/Compose "
            "source before using any image, port, or volume."
        )
        lines.append("")

        lines.append("### Generic installation steps")
        for item in _generic_install_steps(generic_app):
            lines.append(f"- {item}")

        lines.append("")
        lines.append("### Generic failure patterns")
        for item in _generic_common_issues(generic_app):
            lines.append(f"- {item}")

        return {
            "lines": lines,
            "next_step": (
                f"Confirm the official project and trusted Docker/Compose "
                f"source for {generic_app} before installing it."
            ),
            "forum_summary": (
                f"Generic install checklist for {generic_app}. The app has "
                "not been verified against a dedicated ZimaBrain profile; "
                "confirm its trusted source, ports, volumes, and risk flags."
            ),
            "trust_state": "PARTIALLY VERIFIED",
            "trust_title": "⚠️ GENERIC INSTALL CHECKLIST",
            "trust_detail": (
                "The workflow is a verified generic safety checklist, but the "
                "requested app itself has not been verified against a dedicated "
                "profile or confirmed app-store entry."
            ),
        }

    guide = GUIDES[app]
    local = _local_evidence(bundle, app)

    lines.append("### Verified app/profile detected")
    lines.append(f"- {app}")
    lines.append("")
    lines.append("### Guide type")
    lines.append(f"- {guide['title']}")
    lines.append(f"- {guide['manual']}")
    lines.append("")

    post_install_mode = (
        app == "pihole"
        and local
        and any(w in _norm(question) for w in [
            "installed",
            "already installed",
            "changing router dns",
            "before changing router dns",
            "router dns",
            "change dns",
            "dns check",
        ])
    )

    if post_install_mode:
        lines.append("### Mode")
        lines.append("- Post-install router DNS safety check.")
        lines.append("- Pi-hole is already installed, so install steps are skipped in this answer.")
    else:
        lines.append("### Actual install guide / setup steps")
        for item in _install_steps(app):
            lines.append(f"- {item}")

    lines.append("")
    lines.append("### Local evidence")
    if local:
        for item in local:
            lines.append(f"- {item}")
    else:
        lines.append("- No local container evidence was found in the current report for this app.")
        lines.append("- This answer is install/integration guidance only until local evidence is provided.")

    lines.append("")

    if app == "pihole" and local:
        lines.append("### Post-install status")
        lines.append("- Pi-hole local container evidence was found in this report.")
        lines.append("- Treat this as a post-install verification question before changing router DNS.")
        lines.append("")
        lines.append("### Before changing router DNS")
        for item in _pihole_post_install_steps():
            lines.append(f"- {item}")
        lines.append("")

    lines.append("### Verification checklist")
    for item in guide["order"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("### Common failure patterns")
    for item in guide["common_issues"]:
        lines.append(f"- {item}")

    if app == "pihole" and local:
        next_step = "Pi-hole is installed. Test one client first before changing router DNS for the whole network."
        forum_summary = "Pi-hole is installed and local evidence is present. Verify container health, port 53, web UI, AppData bind mount, and one-client DNS test before changing router DNS."
    else:
        next_step = "Verify storage path, container state, bind mounts, permissions, network access, and logs before changing the app configuration."
        forum_summary = f"{guide['title']}: verify storage, container state, bind mounts, permissions, network access, and logs before reinstalling or changing configuration."

    return {
        "lines": lines,
        "next_step": next_step,
        "forum_summary": forum_summary,
        "trust_state": "VERIFIED INSTALL GUIDE",
        "trust_title": "🧭 VERIFIED INSTALL GUIDE",
        "trust_detail": "This answer uses a verified install and troubleshooting order for a dedicated app profile.",
    }


# --- APP VERIFIED GUIDE EXTENSIONS START ---

# Broader verified install guide profiles.
# These extend the same pattern:
# storage -> container -> bind mounts -> permissions -> network -> logs -> configuration.

APP_ALIASES.update({
    "nextcloud": ["nextcloud", "next cloud"],
    "qbittorrent": ["qbittorrent", "qbit", "q bit", "torrent"],
    "plex": ["plex"],
    "emby": ["emby"],
    "tailscale": ["tailscale", "tailscaled"],
    "cloudflared": ["cloudflare", "cloudflared", "cloudflare tunnel", "clouflare", "cloudfare", "cloudflair", "clodflare"],
    "netdata": ["netdata", "netdata cloud"],
    "portainer": ["portainer"],
    "homeassistant": ["home assistant", "home-assistant", "homeassistant"],
    "wazuh": ["wazuh"],
    "paperless": ["paperless", "paperless ngx", "paperless-ngx"],
    "radarr": ["radarr"],
    "sonarr": ["sonarr"],
    "sabnzbd": ["sabnzbd", "sab", "sabnzb"],
})

GUIDES.update({
    "nextcloud": {
        "title": "Nextcloud verified install guide",
        "manual": "No confirmed official ZimaOS manual install guide for this app in the current guide profile. Use the app-store index/local Docker evidence where available, then verify AppData, data path, database, and external storage evidence.",
        "order": [
            "Verify the AppData/config path first. Prefer a stable path under /DATA/AppData or the actual ZimaOS-created Nextcloud folder.",
            "Verify the Nextcloud data folder before uploading files. Do not move the data folder until the active mount path is confirmed.",
            "Verify database location and backup path before upgrade or reinstall.",
            "Verify external storage bind mounts if using external HDD, RAID, SMB, or mounted folders.",
            "Verify permissions on the data folder and any external storage path.",
            "Verify the container is running and the web UI is reachable before changing trusted domains or storage settings.",
            "Check logs before asking for help: Nextcloud app logs, database logs, container status, bind mounts, and disk free space.",
        ],
        "common_issues": [
            "User points Nextcloud to a path that exists on the host but is not mounted inside the container.",
            "External storage appears in ZimaOS Files but not inside Nextcloud.",
            "Database or data folder is moved without backup.",
            "Upgrade breaks because AppData/database location was not confirmed first.",
        ],
    },
    "qbittorrent": {
        "title": "qBittorrent verified install guide",
        "manual": "This guide verifies download paths, bind mounts, permissions, and network before changing qBittorrent settings.",
        "order": [
            "Verify the AppData/config path first.",
            "Verify the download path on the host before starting downloads.",
            "Verify the host download folder is mounted inside the qBittorrent container.",
            "Verify permissions on incomplete and completed download folders.",
            "Verify the Web UI port and container status.",
            "Verify VPN/network mode only after storage paths are confirmed.",
            "Check logs before asking for help: container logs, bind mounts, download path, permissions, and free space.",
        ],
        "common_issues": [
            "Downloads are stuck because the download folder is not mounted inside the container.",
            "The app can write to incomplete but not completed folder.",
            "Wrong path is selected inside qBittorrent settings.",
            "Network/VPN issues are mixed up with storage permission issues.",
        ],
    },
    "plex": {
        "title": "Plex verified install guide",
        "manual": "This guide verifies media paths, permissions, claim/server access, and transcoding before changing Plex settings.",
        "order": [
            "Verify AppData/config path first.",
            "Verify media folder host path on /DATA, /media, external HDD, or RAID.",
            "Verify media bind mounts inside the Plex container.",
            "Verify permissions so Plex can read all media folders.",
            "Verify the Web UI and server claim/access before library scanning.",
            "Verify hardware transcoding only after media paths and permissions are correct.",
            "Check logs before asking for help: Plex logs, container status, bind mounts, media path listing, and GPU checks if transcoding is involved.",
        ],
        "common_issues": [
            "Library is empty because the selected path is not the container-mounted path.",
            "External disk path changed after reboot or update.",
            "Permissions block Plex from reading media.",
            "Transcoding is blamed before basic library path is verified.",
        ],
    },
    "emby": {
        "title": "Emby verified install guide",
        "manual": "This guide follows the same media-server verification order as Jellyfin and Plex.",
        "order": [
            "Verify AppData/config path first.",
            "Verify media folder host path before adding libraries.",
            "Verify media bind mounts inside the Emby container.",
            "Verify permissions on media folders and parent folders.",
            "Verify container status and Web UI port.",
            "Verify Intel VAAPI/NVIDIA/GPU access only after basic library scanning works.",
            "Check logs before asking for help: Emby logs, bind mounts, media path listing, permissions, and GPU checks if transcoding is involved.",
        ],
        "common_issues": [
            "Media folder exists on host but is not visible inside container.",
            "Library scan fails due to wrong path or permissions.",
            "GPU/transcoding is configured before media path is proven.",
        ],
    },
    "tailscale": {
        "title": "Tailscale verified install guide",
        "manual": "This guide verifies container/network mode, authentication, and subnet/exit-node intent before changing routes.",
        "order": [
            "Verify whether Tailscale is installed as a ZimaOS app, Docker container, or host service.",
            "Verify container is running and authenticated.",
            "Verify network mode. Tailscale often requires host networking or extra network permissions depending on setup.",
            "Verify whether the user needs device access only, subnet routing, exit node, or remote app access.",
            "Do not change subnet routes until LAN interface and routing intent are confirmed.",
            "Check logs before asking for help: container logs, auth state, network mode, advertised routes, and access result.",
        ],
        "common_issues": [
            "User installs Tailscale but does not authenticate the node.",
            "Subnet route is enabled without understanding LAN routing.",
            "Container network mode prevents expected access.",
            "Remote access issue is confused with app port/firewall issue.",
        ],
    },
    "cloudflared": {
        "title": "Cloudflared verified install guide",
        "manual": "This guide verifies tunnel token, target service, internal URL, and access control before exposing anything.",
        "order": [
            "Verify the app/service you want to expose works locally first.",
            "Verify Cloudflare tunnel/token is created before starting the container.",
            "Verify the cloudflared container is running.",
            "Verify the target internal URL. Do not use localhost unless the target service is inside the same container.",
            "Verify access control before exposing admin dashboards.",
            "Verify DNS/tunnel route after the local service and container are confirmed.",
            "Check logs before asking for help: cloudflared logs, tunnel name/token status, target URL, and target app container status.",
        ],
        "common_issues": [
            "Tunnel points to localhost instead of the correct host/container address.",
            "Admin dashboard is exposed before access control is confirmed.",
            "Target app is not running locally, so tunnel cannot reach it.",
            "Token/tunnel mismatch.",
        ],
    },
    "netdata": {
        "title": "Netdata verified install guide",
        "manual": "This guide verifies monitoring scope, ports, Docker socket risk, and Netdata Cloud connection before exposing dashboards.",
        "order": [
            "Verify whether the user wants local Netdata only or Netdata Cloud.",
            "Verify container is running and Web UI port is reachable.",
            "Verify Docker socket mount if container monitoring is required.",
            "Treat Docker socket as sensitive because it can expose Docker control surface.",
            "Verify Netdata Cloud claim only after local Netdata is healthy.",
            "Do not expose Netdata publicly unless access control is confirmed.",
            "Check logs before asking for help: Netdata container logs, port mapping, Docker socket mount, claim status, and network access.",
        ],
        "common_issues": [
            "Netdata Cloud claim attempted before local Netdata is healthy.",
            "Docker containers do not appear because Docker socket is not mounted.",
            "Dashboard exposed publicly without access control.",
        ],
    },
    "portainer": {
        "title": "Portainer verified install guide",
        "manual": "This guide verifies Docker socket access, admin UI exposure, AppData path, and existing container state before install/reinstall.",
        "order": [
            "Verify whether Portainer is already installed before installing another copy.",
            "Verify AppData path, usually under /DATA/AppData/portainer or actual configured path.",
            "Verify Docker socket mount only if Portainer must manage Docker.",
            "Treat Docker socket as high risk and keep Portainer private.",
            "Verify ports 9000/9443 or configured mapped ports before accessing the UI.",
            "Back up Portainer data before reinstall or upgrade.",
            "Check logs before asking for help: Portainer logs, docker socket mount, ports, and AppData path.",
        ],
        "common_issues": [
            "User installs a second Portainer instead of fixing access to the first one.",
            "Docker socket is missing, so Portainer cannot manage containers.",
            "Admin UI is exposed to LAN/public without access control.",
        ],
    },
    "homeassistant": {
        "title": "Home Assistant verified install guide",
        "manual": "This guide verifies storage, network mode, device passthrough, and integrations before changing Home Assistant config.",
        "order": [
            "Verify AppData/config path first.",
            "Verify container is running and Web UI is reachable.",
            "Verify network mode, especially if discovery, mDNS, or local device integrations are needed.",
            "Verify USB/Zigbee/Z-Wave/Bluetooth device passthrough before configuring integrations.",
            "Back up Home Assistant config before changing add-ons or integrations.",
            "Check logs before asking for help: Home Assistant logs, config path, network mode, device passthrough, and integration error.",
        ],
        "common_issues": [
            "Local discovery does not work because container network mode is wrong.",
            "USB coordinator is not passed into the container.",
            "Config folder moved or not backed up before changes.",
        ],
    },
    "wazuh": {
        "title": "Wazuh verified install guide",
        "manual": "This guide treats Wazuh as a heavier security stack. Verify storage, ports, resources, and exposure before install.",
        "order": [
            "Verify whether the user wants Wazuh manager, dashboard, indexer, agent, or full stack.",
            "Verify stable AppData/storage path first because Wazuh can be storage heavy.",
            "Verify memory/CPU capacity before deploying the stack.",
            "Verify ports and dashboard exposure before starting.",
            "Do not expose Wazuh dashboard publicly without strong access control.",
            "Check logs before asking for help: manager, indexer, dashboard, agent logs, port mapping, and storage usage.",
        ],
        "common_issues": [
            "User installs only one part of the Wazuh stack and expects the full dashboard to work.",
            "Storage or memory pressure causes indexer/dashboard issues.",
            "Dashboard exposed before access control is confirmed.",
        ],
    },
    "paperless": {
        "title": "Paperless-ngx verified install guide",
        "manual": "This guide verifies consume/media/export paths, database/redis, permissions, and scanner/import workflow.",
        "order": [
            "Verify AppData/config path first.",
            "Verify consume, media, data, and export/archive paths before importing documents.",
            "Verify database and Redis containers if using a stack install.",
            "Verify permissions on consume and media folders.",
            "Verify OCR/language/container logs only after storage paths are confirmed.",
            "Back up database and media before upgrade.",
            "Check logs before asking for help: webserver, worker, broker/redis, database, consume path, media path, and permissions.",
        ],
        "common_issues": [
            "Documents do not import because consume folder is not mounted inside the container.",
            "OCR errors are blamed before folder permissions are checked.",
            "Database/media are not backed up before upgrade.",
        ],
    },
    "radarr": {
        "title": "Radarr verified install guide",
        "manual": "This guide verifies movies path, download client paths, permissions, and indexer/download client integration.",
        "order": [
            "Verify AppData/config path first.",
            "Verify Movies library path on the host and inside the container.",
            "Verify download client path mapping matches qBittorrent/SABnzbd paths.",
            "Verify permissions on movie and download folders.",
            "Verify Radarr can reach download client and indexers.",
            "Do not configure automation until library and download paths are confirmed.",
            "Check logs before asking for help: Radarr logs, path mappings, download client settings, permissions, and completed download path.",
        ],
        "common_issues": [
            "Completed downloads cannot import because Radarr and downloader use different container paths.",
            "Movies folder is not mounted or not writable.",
            "Downloader works but Radarr cannot see completed files.",
        ],
    },
    "sonarr": {
        "title": "Sonarr verified install guide",
        "manual": "This guide verifies TV path, download client paths, permissions, and season/episode import logic.",
        "order": [
            "Verify AppData/config path first.",
            "Verify TV library path on the host and inside the container.",
            "Verify download client path mapping matches qBittorrent/SABnzbd paths.",
            "Verify permissions on TV and download folders.",
            "Verify Sonarr can reach download client and indexers.",
            "Do not configure automation until library and download paths are confirmed.",
            "Check logs before asking for help: Sonarr logs, path mappings, download client settings, permissions, and completed download path.",
        ],
        "common_issues": [
            "Completed downloads cannot import because Sonarr and downloader use different container paths.",
            "TV folder is not mounted or not writable.",
            "Downloader works but Sonarr cannot see completed files.",
        ],
    },
    "sabnzbd": {
        "title": "SABnzbd verified install guide",
        "manual": "This guide verifies download paths, categories, permissions, and integration with Radarr/Sonarr.",
        "order": [
            "Verify AppData/config path first.",
            "Verify incomplete and completed download paths on the host.",
            "Verify paths are mounted inside the SABnzbd container.",
            "Verify permissions on incomplete and completed folders.",
            "Verify categories match Radarr/Sonarr expectations.",
            "Verify Radarr/Sonarr path mappings only after SABnzbd can download and complete files.",
            "Check logs before asking for help: SABnzbd logs, path settings, categories, permissions, and downloader/container status.",
        ],
        "common_issues": [
            "Downloads complete but Radarr/Sonarr cannot import due to path mismatch.",
            "Incomplete/completed folders are not mounted or not writable.",
            "Categories are missing or wrong.",
        ],
    },
})

# --- APP VERIFIED GUIDE EXTENSIONS END ---



# --- PIHOLE VERIFIED GUIDE EXTENSION START ---

APP_ALIASES.update({
    "pihole": ["pi-hole", "pihole", "pi hole"],
})

GUIDES.update({
    "pihole": {
        "title": "Pi-hole verified install guide",
        "manual": "No confirmed official ZimaOS manual install guide for this app in the current guide profile. Use app-store/local Docker evidence where available, then verify DNS ports, AppData, network settings, and router/client DNS changes.",
        "order": [
            "Verify whether Pi-hole will be DNS only or DNS plus DHCP.",
            "Verify AppData/config path first.",
            "Verify port availability, especially DNS port 53 and the web UI port.",
            "Verify container state before changing router DNS.",
            "Verify LAN/router DNS settings only after Pi-hole is reachable.",
            "Do not enable DHCP unless the router DHCP plan is confirmed.",
            "Check logs before asking for help: Pi-hole logs, container status, port map, DNS settings, and router/client DNS configuration.",
        ],
        "common_issues": [
            "Port 53 is already used by another DNS service.",
            "User changes router DNS before Pi-hole is confirmed healthy.",
            "DHCP is enabled in two places and causes network issues.",
            "Pi-hole works locally but clients are still using router or ISP DNS.",
        ],
    },
})

# --- PIHOLE VERIFIED GUIDE EXTENSION END ---


# --- DATABASE APP VERIFIED GUIDE EXTENSION START ---

APP_ALIASES.update({
    "mariadb": ["mariadb", "maria db", "mysql", "mysql database"],
})

GUIDES.update({
    "mariadb": {
        "title": "MariaDB / MySQL verified install guide",
        "manual": "No confirmed official ZimaOS manual install guide for this app in the current guide profile. Use app-store/local Docker evidence where available, then verify database storage, ports, credentials, backups, and dependent apps.",
        "order": [
            "Verify why MariaDB is needed first. Many apps already include their own database container.",
            "Verify the AppData/database path first, normally under /DATA/AppData/mariadb or the actual ZimaOS-created folder.",
            "Never store database data on an unstable or duplicate /media ghost path.",
            "Verify the database port, usually 3306, is not conflicting with another database container.",
            "Verify credentials, database name, user name, and password before connecting another app.",
            "Verify dependent apps can reach MariaDB by the correct Docker network name or host IP.",
            "Back up the database volume before upgrade, reinstall, migration, or repair.",
            "Check logs before asking for help: MariaDB logs, container status, bind mounts, port mapping, free disk space, and the dependent app connection error.",
        ],
        "common_issues": [
            "User installs a second database even though the app already has one.",
            "Database data path is wrong, moved, or not backed up.",
            "Dependent app uses localhost inside Docker and cannot reach the database.",
            "Port 3306 conflicts with another MySQL/MariaDB container.",
            "Wrong database credentials are entered into the dependent app.",
        ],
    },
})

# --- DATABASE APP VERIFIED GUIDE EXTENSION END ---


# --- APP IDENTITY GUARD EXTENSION START ---

APP_ALIASES.update({
    "portainer-agent": ["portainer agent", "portainer-agent"],
    "agent-dvr": ["agent dvr", "ispy agent dvr", "ispyagentdvr", "ispy agent"],
})

GUIDES.update({
    "portainer-agent": {
        "title": "Portainer Agent verified install guide",
        "manual": "Portainer Agent is not the same as Portainer CE. Use it only when this ZimaOS host needs to be managed as a remote Docker environment by another Portainer server.",
        "order": [
            "Confirm whether the user wants Portainer CE dashboard or Portainer Agent remote endpoint.",
            "If Portainer CE is already running locally with Docker socket access, do not install Portainer Agent on the same host unless remote management is required.",
            "Before installing, verify existing Portainer containers, Docker socket access, exposed ports, and AppData path.",
            "If installing Portainer Agent, keep the agent private and only expose it to the trusted Portainer server or private network.",
            "Verify container state, port mapping, Docker socket mount, and logs after install.",
        ],
        "common_issues": [
            "User installs Portainer Agent when they only needed Portainer CE.",
            "User installs a duplicate Portainer CE dashboard instead of an agent.",
            "Agent port is exposed publicly.",
            "Docker socket mount is missing, so the agent cannot manage Docker.",
        ],
    },
    "agent-dvr": {
        "title": "Agent DVR / iSpy verified identity guide",
        "manual": "Agent DVR is iSpy Agent DVR. Do not confuse it with generic Docker images containing the word agent, such as Portainer Agent or LinuxServer build-agent.",
        "order": [
            "Confirm the requested app is Agent DVR / iSpy Agent DVR.",
            "Do not match linuxserver/build-agent or portainer-agent.",
            "Use a trusted Agent DVR / iSpy Docker source only after verifying image name, ports, storage paths, and access control.",
            "Map persistent data under /DATA/AppData/agent-dvr or the verified ZimaOS-created AppData folder.",
            "Verify container state, port mapping, bind mounts, and logs after install.",
        ],
        "common_issues": [
            "Generic app search matches portainer-agent.",
            "Generic app search matches linuxserver/build-agent.",
            "Camera app data is not mapped to persistent storage.",
        ],
    },
})

# --- APP IDENTITY GUARD EXTENSION END ---
