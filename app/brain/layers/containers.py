def answer(bundle):
    lines = []
    lines.append("- This is a container state question.")
    lines.append("- The answer comes from the Containers Layer using dashboard-parsed Docker state.")
    lines.append("")

    exited = bundle.get("exited", [])

    if exited:
        lines.append("Exited containers parsed from the dashboard layer:")
        for item in exited:
            name = item.get("name", "unknown")
            image = item.get("image", "unknown")
            lines.append(f"- {name} ({image})")
    else:
        lines.append("- No exited containers were parsed from the current dashboard evidence.")

    return {
        "lines": lines,
        "next_step": "Inspect only the affected exited container logs/status. Do not remove containers in bulk.",
        "forum_summary": "Based on the verified dashboard evidence, several containers are exited. Inspect only the affected container logs and status one by one. Do not remove containers in bulk or run Docker prune commands.",
    }
