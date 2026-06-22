from pathlib import Path
import json
import re

INDEX_PATH = Path("docs/zimaos-official/manual-index.json")

GENERIC_WORDS = {
    "how", "what", "where", "when", "why", "can", "could", "would",
    "should", "the", "and", "for", "with", "from", "into", "onto",
    "zimaos", "zima", "official", "manual", "docs", "documentation",
    "say", "about", "create", "setup", "use", "using", "make",
    "find", "access", "device", "data", "drive", "files"
}

TOPIC_RULES = [
    {
        "name": "ssh",
        "q_any": ["ssh", "enable ssh", "open ssh"],
        "want": ["ssh", "enable ssh", "open ssh", "ssh setting"],
        "block": ["raid", "raid6", "zfs", "time machine", "backup", "network id"],
    },
    {
        "name": "network_id",
        "q_any": ["network id", "remote id"],
        "want": ["network id", "remote id", "get network id"],
        "block": ["raid", "raid6", "zfs", "ssh", "time machine", "backup"],
    },
    {
        "name": "install_usb",
        "q_any": ["bootable usb", "usb installer", "create usb", "flash usb", "install zimaos", "installing zimaos", "how to install", "installer", "installation"],
        "want": ["how to install zimaos", "install zimaos", "installing zimaos", "install"],
        "block": ["raid", "raid6", "zfs", "ssh", "network id", "time machine", "backup", "smb"],
    },
    {
        "name": "update_safety",
        "q_any": ["upgrade", "upgrading", "update", "updating", "safely"],
        "want": ["update offline", "offline install", "update", "upgrade"],
        "block": ["azuracast", "paperless", "syncthing", "zabbix", "immich", "jellyfin", "time machine"],
    },
    {
        "name": "backup_321",
        "q_any": ["3-2-1", "3 2 1", "backup"],
        "want": ["3 2 1", "3-2-1", "backup"],
        "block": ["raid6", "zfs", "ssh", "network id", "immich", "jellyfin"],
    },
    {
        "name": "migration",
        "q_any": ["migrate", "migrating", "migration", "move data", "transfer data", "another drive", "rsync", "casaos to zimaos", "from casaos to zimaos"],
        "want": ["migrate from casaos to zimaos", "casaos to zimaos", "migration", "migrate", "rsync", "backup", "3 2 1", "3-2-1"],
        "block": ["raid6", "zfs", "ssh", "network id", "immich", "jellyfin", "time machine"],
    },
    {
        "name": "remote_access",
        "q_any": ["remote access", "access remotely", "remotely", "zimaclient", "zima client"],
        "want": ["remote access", "zimaclient", "zima client", "remote id", "network id"],
        "block": ["raid", "raid6", "zfs", "ssh", "backup"],
    },
    {
        "name": "smb",
        "q_any": ["smb", "samba", "share", "shares", "synology"],
        "want": ["smb", "samba", "share", "shares", "synology"],
        "block": ["raid6", "zfs", "ssh", "network id", "immich"],
    },
    {
        "name": "transfer_speed",
        "q_any": ["slow transfer", "transfer speed", "fastest transfer", "network speed", "speed"],
        "want": ["transfer speed", "fastest transfer", "slow transfer", "nas transfer", "network"],
        "block": ["raid6", "zfs", "ssh", "backup"],
    },
    {
        "name": "raid_rebuild",
        "q_any": ["rebuild raid after reinstall", "raid after reinstall", "reinstall raid", "recover raid", "rebuild raid"],
        "want": ["rebuild raid", "raid after reinstall", "reinstall"],
        "block": ["ssh", "network id", "immich", "jellyfin", "time machine"],
    },
    {
        "name": "raid_general",
        "q_any": ["raid6", "raid 6", "zfs", "storage pool"],
        "want": ["raid6", "raid 6", "zfs", "storage pool"],
        "block": ["ssh", "network id", "immich", "jellyfin"],
    },
]

def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()

def _tokens(text):
    return [
        t for t in re.findall(r"[a-z0-9]+", str(text or "").lower())
        if len(t) >= 3 and t not in GENERIC_WORDS
    ]

def _load_index():
    if not INDEX_PATH.exists():
        return []
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return data.get("pages", [])
    except Exception:
        return []

def _page_blob(page):
    return _norm(f"{page.get('title') or ''} {page.get('url') or ''}")

def _matched_rules(question):
    q = _norm(question)
    rules = []
    for rule in TOPIC_RULES:
        if any(_norm(p) in q for p in rule["q_any"]):
            rules.append(rule)
    return rules

def _score_page(question, page):
    q = _norm(question)
    blob = _page_blob(page)
    q_tokens = _tokens(q)

    score = 0
    rules = _matched_rules(question)

    if rules:
        for rule in rules:
            for want in rule["want"]:
                want_n = _norm(want)
                if want_n and want_n in blob:
                    score += 80 + len(want_n.split()) * 4

            for bad in rule["block"]:
                bad_n = _norm(bad)
                if bad_n and bad_n in blob:
                    score -= 120

        for t in q_tokens:
            if t in blob:
                score += 8

    else:
        for t in q_tokens:
            if t in blob:
                score += 5

    # Strong boosts for explicit official manual page intents.
    if ("install" in q or "installing" in q or "installation" in q) and "zimaos" in q and "how to install zimaos" in blob:
        score += 260

    if ("upgrade" in q or "upgrading" in q or "update" in q or "updating" in q) and "zimaos" in q and ("update offline" in blob or "offline install" in blob):
        score += 220

    if ("casaos" in q and "zimaos" in q and ("migrate" in q or "migrating" in q or "migration" in q)) and ("casaos to zimaos" in blob or "migrate from casaos to zimaos" in blob):
        score += 300

    # Hard guards for known dangerous wrong matches.
    if ("bootable usb" in q or "usb installer" in q or ("usb" in q and "install" in q)) and ("raid" in blob or "raid6" in blob or "zfs" in blob):
        score -= 250

    if ("migrate" in q or "migration" in q or "another drive" in q) and ("time machine" in blob or "backup" in blob or "3 2 1" in blob or "3-2-1" in blob):
        score -= 300

    if ("3 2 1" in q or "3-2-1" in q) and "time machine" in blob:
        score -= 180

    if ("rebuild raid after reinstall" in q or "raid after reinstall" in q) and "raid6" in blob:
        score -= 180

    return score

def _read_page(path, max_chars=1300):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    noise = [
        "Zima-Docs", "ZimaOS", "ZimaCube", "ZimaBoard", "Forum",
        "English", "中文", "日本語", "Português", "Español", "Store",
        "Last updated:", "Prev Next", "Contents", "Back to Top",
        "What's Zima", "Overview", "Install Guide", "Explore"
    ]

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Source:"):
            continue
        if line.startswith("# "):
            continue
        if any(line == n or line.startswith(n) for n in noise):
            continue
        if len(line) < 3:
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    sidebar_stops = [
        "Get Started", "Features", "Remote Access", "Thunderbolt PC Direct",
        "Sync Photos with Immich", "Media Server Setup with Jellyfin",
        "Get Network ID", "Create Raid6", "Immich Tutorial"
    ]

    for stop in sidebar_stops:
        pos = cleaned.find("\n" + stop)
        if pos > 500:
            cleaned = cleaned[:pos].strip()
            break

    return cleaned[:max_chars].strip()

def answer(bundle, question):
    pages = _load_index()
    if not pages:
        return {
            "title": "ZimaOS Manual Knowledge Engine",
            "severity": "warning",
            "lines": [
                "Official ZimaOS manual index was not found.",
                "Run the manual fetcher and clean index builder first.",
            ],
        }

    ranked = sorted(
        [(_score_page(question, p), p) for p in pages],
        key=lambda x: x[0],
        reverse=True
    )

    matches = [(s, p) for s, p in ranked if s > 0][:5]

    if not matches or matches[0][0] < 35:
        return {
            "title": "ZimaOS Manual Knowledge Engine",
            "severity": "info",
            "lines": [
                "This is a ZimaOS manual / how-to question, but no strong official manual match was found.",
                "I should not force a weak manual page into the answer.",
                "Ask for a clearer topic, or add a stronger official/manual page for this subject.",
            ],
        }

    best_score, best = matches[0]
    second_score = matches[1][0] if len(matches) > 1 else 0
    excerpt = _read_page(best.get("markdown", ""))

    confidence = "high"
    if best_score < 80 or (second_score and best_score - second_score < 12):
        confidence = "medium"

    lines = [
        "This is a ZimaOS manual / how-to question.",
        "Answer source: official ZimaOS manual pages saved locally.",
        "This is guidance from documentation, not a same-report diagnosis.",
        f"Manual relevance confidence: {confidence}",
    ]

    qn = _norm(question)
    best_blob = _page_blob(best)

    if (
        ("upgrade" in qn or "upgrading" in qn or "update" in qn or "updating" in qn or "safely" in qn)
        and "zimaos" in qn
    ):
        lines += [
            "",
            "ZimaBrain safety note:",
            "The best official page found is the ZimaOS offline update page. Treat this as the manual reference, not a full update safety diagnosis.",
            "Before updating, verify current ZimaOS version, backup status, RAUC status, failed services, storage mounts, and enough free space.",
            "If the system already has storage or app path problems, fix those before updating.",
        ]

    lines += [
        "",
        "Best matching official page:",
        f"{best.get('title')}",
        f"Source: {best.get('url')}",
        "",
        "Relevant manual excerpt:",
        excerpt if excerpt else "No excerpt text could be loaded from the saved page.",
        "",
        "Other possible manual matches:",
    ]

    for score, p in matches[1:5]:
        lines.append(f"- {p.get('title')} | {p.get('url')}")

    lines += [
        "",
        "Next safest step:",
        "Follow the official manual page first. If the user has an error or failed step, collect evidence and route back to the diagnostic layers.",
    ]

    return {
        "title": "ZimaOS Manual Knowledge Engine",
        "severity": "info",
        "lines": lines,
    }
