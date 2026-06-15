def answer(bundle):
    lines = []

    lines.append("- This is a safe container command question.")
    lines.append("- The answer comes from the Container Commands Layer.")
    lines.append("")

    lines.append("### Verdict")
    lines.append("- Use read-only Docker commands first.")
    lines.append("- These commands check container state, names, images, health, ports, and recent logs without changing anything.")
    lines.append("- Do not remove, recreate, prune, or restart containers until the exact container and issue are verified.")
    lines.append("")

    lines.append("### Safe read-only commands")
    lines.append("- Copy and paste these commands exactly as shown.")
    lines.append("- Share the output before making any container changes.")
    lines.append("")
    lines.append("```bash")
    lines.append("docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'")
    lines.append("docker compose ls")
    lines.append("docker stats --no-stream")
    lines.append("```")
    lines.append("")

    lines.append("### Optional focused checks")
    lines.append("- Use these when you already know the container name.")
    lines.append("- Replace CONTAINER_NAME with the exact name from docker ps.")
    lines.append("")
    lines.append("```bash")
    lines.append("docker inspect CONTAINER_NAME --format '{{json .State}}'")
    lines.append("docker logs --tail 120 CONTAINER_NAME")
    lines.append("```")
    lines.append("")

    lines.append("### What the commands verify")
    lines.append("- `docker ps -a` shows running, exited, restarting, unhealthy, and created containers.")
    lines.append("- `docker compose ls` shows Compose projects known to Docker.")
    lines.append("- `docker stats --no-stream` gives a quick CPU/RAM snapshot.")
    lines.append("- `docker inspect` shows the container state without modifying it.")
    lines.append("- `docker logs --tail 120` shows recent logs only.")
    lines.append("")

    lines.append("### What not to touch")
    lines.append("- Do not run `docker system prune`.")
    lines.append("- Do not remove containers in bulk.")
    lines.append("- Do not recreate an app until the bind mounts and data paths are verified.")
    lines.append("- Do not change compose files until the exact app folder is confirmed.")

    return {
        "lines": lines,
        "next_step": "Run the safe read-only Docker commands and review the output before restarting, removing, recreating, or pruning anything.",
        "forum_summary": "Start with read-only Docker checks: docker ps -a for state, docker compose ls for projects, docker stats --no-stream for resource usage, then inspect/logs for one exact container if needed. Do not prune, remove, recreate, or restart anything until the exact container, bind mounts, and data paths are verified.",
    }
