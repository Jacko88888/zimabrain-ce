def answer(bundle, question):
    evidence = bundle.get("same_report_evidence", {}) or {}
    report = bundle.get("report", "") or ""

    network_keys = ["ip_addr", "ip_route", "resolv", "ping", "tailscale", "cloudflared", "docker_ps"]
    found = [k for k in network_keys if evidence.get(k)]

    lines = []
    lines.append("- This is a network connectivity diagnostic question.")
    lines.append("- The layer separates LAN access, DNS, gateway, tunnel/proxy, and container exposure problems.")
    lines.append("")
    lines.append("### Same-report evidence")
    lines.append(f"- Network evidence keys found: {', '.join(found) if found else 'none'}")
    lines.append(f"- General report evidence present: {'yes' if report.strip() else 'no'}")

    if not found:
        lines.append("")
        lines.append("- No matching same-report network connectivity evidence was found.")
        return {
            "lines": lines,
            "next_step": "Collect IP address, route, DNS, ping, and tunnel status evidence before changing network settings.",
            "forum_summary": "Network issue is not verified yet. Collect IP, route, DNS, ping, and tunnel evidence first.",
        }

    lines.append("")
    lines.append("- Some network evidence exists, but the connectivity root cause is not fully verified from same-report evidence.")
    lines.append("")
    lines.append("### Diagnostic focus")
    lines.append("- Confirm local IP address.")
    lines.append("- Confirm default gateway.")
    lines.append("- Confirm DNS resolution.")
    lines.append("- Confirm LAN access versus remote/tunnel access.")
    lines.append("- Confirm whether the affected service is a host service or Docker container.")
    return {
        "lines": lines,
        "next_step": "Check IP, default route, DNS, ping result, and tunnel status before changing firewall or container settings.",
        "forum_summary": "Network evidence is partial. Confirm IP, gateway, DNS, ping, and tunnel path before repair.",
    }
