def _text(bundle, key):
    return (bundle.get("same_report_evidence", {}) or {}).get(key, "") or ""


def _has_docker_ps(bundle):
    return bool(_text(bundle, "docker_ps").strip())


def _has_docker_access(bundle):
    return bool(_text(bundle, "docker_access").strip())


def _docker_mentions(report):
    r = (report or "").lower()
    return any(x in r for x in [
        "docker daemon",
        "docker.service",
        "containerd",
        "docker ps",
        "cannot connect to the docker daemon",
        "is the docker daemon running",
    ])


def answer(bundle, question):
    report = bundle.get("report", "") or ""
    docker_ps = _has_docker_ps(bundle)
    docker_access = _has_docker_access(bundle)
    mentions = _docker_mentions(report)

    lines = []
    lines.append("- This is a Docker daemon diagnostic question.")
    lines.append("- The layer checks same-report Docker evidence before suggesting repair steps.")

    lines.append("")
    lines.append("### Same-report Docker evidence")
    lines.append(f"- Docker ps evidence parsed: {'yes' if docker_ps else 'no'}")
    lines.append(f"- Docker inspect / bind-mount evidence parsed: {'yes' if docker_access else 'no'}")
    lines.append(f"- Docker daemon/service error text found in report: {'yes' if mentions else 'no'}")

    if not docker_ps and not docker_access and not mentions:
        lines.append("")
        lines.append("- No matching Docker daemon evidence was found in the current report.")
        lines.append("- No matching same-report evidence was found to verify the root cause.")
        return {
            "lines": lines,
            "next_step": "Collect Docker service status, Docker journal logs, filesystem free space, and mount read/write state before giving repair steps.",
            "forum_summary": "The Docker daemon issue is not verified yet. Collect Docker service status, journal logs, filesystem free space, and mount state before attempting repair.",
        }

    lines.append("")
    lines.append("- Some Docker evidence exists in the current report.")
    lines.append("- Root cause is not fully verified from same-report evidence.")

    if docker_ps:
        lines.append("- Docker ps evidence suggests Docker was able to list containers when the report was collected.")
    if docker_access:
        lines.append("- Docker inspect/bind-mount evidence is available and can be used to check app paths.")
    if mentions:
        lines.append("- Report text contains Docker daemon/service related wording.")

    lines.append("")
    lines.append("### Required checks before repair")
    lines.append("- Docker service status")
    lines.append("- Recent Docker journal logs")
    lines.append("- Filesystem free space")
    lines.append("- Whether /var/lib/docker or app storage is read-only")
    lines.append("- Whether containerd is running")
    lines.append("- Whether the issue is daemon-wide or only one app/container")

    lines.append("")
    lines.append("### Do not do yet")
    lines.append("- Do not run `docker system prune`.")
    lines.append("- Do not delete `/var/lib/docker`.")
    lines.append("- Do not reinstall ZimaOS.")
    lines.append("- Do not recreate apps until Docker service and storage evidence are checked.")

    return {
        "lines": lines,
        "next_step": "Check Docker service status and journal logs first, then check free space and read-only mount state before restarting or repairing Docker.",
        "forum_summary": "Docker evidence exists, but the daemon root cause is only partially verified. Check Docker service status, journal logs, free space, and read-only mount state before repair.",
    }
