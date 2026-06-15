ISSUE_TYPES = {
    "docker_daemon": {
        "label": "Docker daemon / Docker service issue",
        "need": [
            "Docker service status",
            "Recent Docker journal logs",
            "Filesystem free space",
            "Whether /var/lib/docker or app storage is read-only",
        ],
        "safe": [
            "Do not run docker system prune.",
            "Do not delete /var/lib/docker.",
            "Do not reinstall ZimaOS until storage and Docker evidence are checked.",
        ],
        "next": "Collect Docker service status, Docker journal logs, and filesystem/mount evidence before attempting repair.",
    },
    "installer_boot": {
        "label": "Install / boot / hardware compatibility issue",
        "need": [
            "Device model and year",
            "Installer version",
            "Boot mode shown in BIOS/EFI",
            "Screenshot of the boot or installer error",
            "Output from a live Linux USB if ZimaOS will not boot",
        ],
        "safe": [
            "Do not wipe the internal disk until boot mode and target disk are confirmed.",
            "Disconnect data drives before reinstalling if there is data to protect.",
            "Confirm whether the machine can boot another Linux installer.",
        ],
        "next": "Confirm boot mode, target disk visibility, and whether a Linux live USB can see the internal drive.",
    },
    "readonly_storage": {
        "label": "Storage became read-only",
        "need": [
            "Active mount output",
            "Filesystem errors from journal",
            "Disk health / SMART evidence",
            "Which path became read-only",
            "Whether apps are writing to /DATA, /media, or .media paths",
        ],
        "safe": [
            "Do not force remount read-write until disk and filesystem errors are checked.",
            "Do not run repair commands without confirming the affected device and filesystem.",
            "Back up important data before any filesystem repair.",
        ],
        "next": "Collect mount, df, lsblk, and recent filesystem error evidence before changing the mount state.",
    },
    "add_drives_storage": {
        "label": "Add drives / storage pool / RAID question",
        "need": [
            "Current disk list",
            "Existing pool or RAID layout",
            "Which drives are new",
            "Whether the user wants redundancy or capacity",
            "Whether the data needs to be preserved",
        ],
        "safe": [
            "Do not create or format a pool until the target drives are confirmed.",
            "Do not assume RAID can be expanded safely without checking the current layout.",
            "Separate OS disk, app data disk, and storage disks before advising.",
        ],
        "next": "Collect disk inventory and current storage/RAID layout before advising add-drive or RAID changes.",
    },
    "general": {
        "label": "General forum issue intake",
        "need": [
            "Exact ZimaOS version",
            "Device model",
            "What changed before the issue started",
            "Screenshots or logs",
            "Current storage and container evidence if relevant",
        ],
        "safe": [
            "Do not run destructive commands.",
            "Do not reinstall before confirming whether data drives are separate from the OS disk.",
            "Ask for evidence before giving repair steps.",
        ],
        "next": "Collect the missing evidence first, then route the issue into the correct diagnostic layer.",
    },
}


def _detect_issue(question):
    q = (question or "").lower()

    if "docker" in q and ("daemon" in q or "not working" in q or "restart" in q or "restarting" in q):
        return "docker_daemon"

    if any(x in q for x in ["macbook", "install", "installer", "efi", "boot", "no devices found"]):
        return "installer_boot"

    if any(x in q for x in ["read-only", "readonly", "read only", "set my storage to read"]):
        return "readonly_storage"

    if any(x in q for x in ["add drives", "add drive", "raid", "storage pool", "cannot add drives", "newb"]):
        return "add_drives_storage"

    return "general"


def answer(bundle, question=""):
    issue_key = _detect_issue(question)
    issue = ISSUE_TYPES.get(issue_key, ISSUE_TYPES["general"])

    lines = []
    lines.append("- This is a forum-style issue intake question.")
    lines.append("- No matching same-report evidence was found to verify the root cause.")
    lines.append("- This answer is intake guidance only, not a verified diagnosis.")
    lines.append("")

    lines.append("### Intake category")
    lines.append(f"- {issue['label']}")

    lines.append("")
    lines.append("### Evidence needed before diagnosis")
    for item in issue["need"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("### What not to do yet")
    for item in issue["safe"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("### How ZimaBrain should handle this")
    lines.append("- Mark this as NOT VERIFIED until the required evidence is present.")
    lines.append("- Once evidence is provided, route the issue to the correct diagnostic layer.")
    lines.append("- Give safe commands only after the affected device, service, or path is confirmed.")

    return {
        "lines": lines,
        "next_step": issue["next"],
        "forum_summary": f"This is a {issue['label']} intake case. It is not verified yet. Collect the required evidence before giving repair steps.",
    }
