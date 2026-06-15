def answer(bundle):
    lines = []

    lines.append("- This is a safe system command question.")
    lines.append("- The answer comes from the System Commands Layer.")
    lines.append("")

    lines.append("### Verdict")
    lines.append("- Use read-only system commands first.")
    lines.append("- These commands check uptime, memory, swap, failed services, load, and recent errors without changing anything.")
    lines.append("- Do not restart services, repair packages, clear logs, or reboot until the outputs are reviewed.")
    lines.append("")

    lines.append("### Safe read-only commands")
    lines.append("- Copy and paste these commands exactly as shown.")
    lines.append("- Share the output before making any system changes.")
    lines.append("")
    lines.append("```bash")
    lines.append("uptime")
    lines.append("free -h")
    lines.append("systemctl --failed --no-pager")
    lines.append("```")
    lines.append("")

    lines.append("### Optional deeper read-only checks")
    lines.append("- Use these if the system feels slow, unstable, or services are failing.")
    lines.append("")
    lines.append("```bash")
    lines.append("top -b -n 1 | head -30")
    lines.append("journalctl -p warning..alert -b --no-pager | tail -120")
    lines.append("df -h")
    lines.append("```")
    lines.append("")

    lines.append("### What the commands verify")
    lines.append("- `uptime` shows how long the system has been running and the current load average.")
    lines.append("- `free -h` shows RAM and swap usage.")
    lines.append("- `systemctl --failed` shows failed host services.")
    lines.append("- `top` gives a quick CPU and memory snapshot.")
    lines.append("- `journalctl` shows recent warnings and errors from the current boot.")
    lines.append("- `df -h` confirms whether any filesystem is full.")
    lines.append("")

    lines.append("### What not to touch")
    lines.append("- Do not reboot before checking failed services and logs.")
    lines.append("- Do not restart services until the exact failed unit is confirmed.")
    lines.append("- Do not delete logs or cache folders before confirming disk usage.")
    lines.append("- Do not run repair commands until the cause is verified.")

    return {
        "lines": lines,
        "next_step": "Run the safe read-only system commands and review the output before restarting services, rebooting, or attempting repairs.",
        "forum_summary": "Start with read-only system checks: uptime for load, free -h for memory/swap, systemctl --failed for failed services, top for a quick process snapshot, journalctl for recent warnings/errors, and df -h for filesystem usage. Do not restart, reboot, or repair until the exact issue is verified.",
    }
