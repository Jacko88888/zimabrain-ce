def answer(bundle):
    lines = []

    lines.append("- This is a safe network command question.")
    lines.append("- The answer comes from the Network Commands Layer.")
    lines.append("")

    lines.append("### Verdict")
    lines.append("- Use read-only network commands first.")
    lines.append("- These commands check IP address, routes, DNS, listening ports, and basic connectivity without changing anything.")
    lines.append("- Do not change DNS, firewall, routes, or network settings until the outputs are reviewed.")
    lines.append("")

    lines.append("### Safe read-only commands")
    lines.append("- Copy and paste these commands exactly as shown.")
    lines.append("- Share the output before making any network changes.")
    lines.append("")
    lines.append("```bash")
    lines.append("ip addr")
    lines.append("ip route")
    lines.append("cat /etc/resolv.conf")
    lines.append("```")
    lines.append("")

    lines.append("### Optional connectivity checks")
    lines.append("- These only test connectivity and do not change the system.")
    lines.append("")
    lines.append("```bash")
    lines.append("ping -c 4 1.1.1.1")
    lines.append("ping -c 4 google.com")
    lines.append("ss -tulpn")
    lines.append("```")
    lines.append("")

    lines.append("### What the commands verify")
    lines.append("- `ip addr` shows interfaces and assigned IP addresses.")
    lines.append("- `ip route` shows the default gateway and routing table.")
    lines.append("- `cat /etc/resolv.conf` shows DNS resolver configuration.")
    lines.append("- `ping 1.1.1.1` checks raw internet reachability without DNS.")
    lines.append("- `ping google.com` checks internet plus DNS resolution.")
    lines.append("- `ss -tulpn` shows listening ports and the processes using them.")
    lines.append("")

    lines.append("### What not to touch")
    lines.append("- Do not change DNS until resolver output is verified.")
    lines.append("- Do not change firewall rules until listening ports and access path are confirmed.")
    lines.append("- Do not restart network services until IP, route, and DNS are reviewed.")
    lines.append("- Do not expose ports publicly without confirming the service and risk.")

    return {
        "lines": lines,
        "next_step": "Run the safe read-only network commands and review IP, route, DNS, and port output before changing firewall, DNS, routes, or network services.",
        "forum_summary": "Start with read-only network checks: ip addr for interfaces, ip route for gateway, resolv.conf for DNS, ping 1.1.1.1 for raw connectivity, ping google.com for DNS/internet, and ss -tulpn for listening ports. Do not change firewall, DNS, routes, or exposed ports until the outputs are verified.",
    }
