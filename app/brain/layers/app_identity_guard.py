import re


def _norm(text):
    text = (text or "").lower()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


APP_IDENTITY_ALIASES = {
    "agent-dvr": [
        "agent dvr",
        "ispy agent dvr",
        "ispyagentdvr",
        "ispy agent",
    ],
    "portainer-agent": [
        "portainer agent",
        "portainer-agent",
    ],
    "portainer": [
        "portainer ce",
        "portainer server",
        "portainer dashboard",
    ],
}


def resolve_app_identity(question):
    q = _norm(question)
    matches = []

    for app, aliases in APP_IDENTITY_ALIASES.items():
        for alias in aliases:
            a = _norm(alias)
            if a and a in q:
                matches.append((len(a), app))

    if not matches:
        return ""

    matches.sort(reverse=True)
    return matches[0][1]
