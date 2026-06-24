def answer(bundle):
    lines = []
    lines.append("- This is a container state question.")
    lines.append("- The answer comes from the Containers Layer using dashboard-parsed Docker state.")
    lines.append("")

    exited = bundle.get("exited", [])
    count = bundle.get("container_count", {}) or {}
    running = count.get("running")
    total = count.get("total")
    not_running = count.get("not_running")

    if running is not None and total is not None:
        lines.append("Dashboard container count:")
        lines.append(f"- {running}/{total} containers running.")
        if not_running and not_running > 0:
            lines.append(f"- {not_running} container(s) are not running according to the visual dashboard count.")
        else:
            lines.append("- All counted containers are running according to the visual dashboard count.")
        lines.append("")

    if exited:
        lines.append("Exited containers parsed from the dashboard layer:")
        for item in exited:
            name = item.get("name", "unknown")
            image = item.get("image", "unknown")
            lines.append(f"- {name} ({image})")
    else:
        if not_running and not_running > 0:
            lines.append("- No named exited containers were parsed, but the dashboard count shows not all containers are running.")
        else:
            lines.append("- No exited containers were parsed from the current dashboard evidence.")

    return {
        "lines": lines,
        "next_step": "Inspect only the affected stopped/exited container logs/status. Do not remove containers in bulk.",
        "forum_summary": "Based on the verified dashboard evidence, review any stopped or exited containers one by one. Do not remove containers in bulk or run Docker prune commands.",
    }
