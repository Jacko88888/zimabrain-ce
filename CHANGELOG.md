# Changelog

## 1.6.0-beta

### Added
- First-run password setup.
- Session login/logout support.
- CSRF protection for POST actions.
- Redacted support/session export.
- JSON API v1 endpoints.
- Structured JSON answer/session downloads.
- SMART / NVMe health layer.
- SMART visibility limitation detection.
- Network exposure and firewall verification layer.
- Bind-aware port reachability self-check.
- Grouped reachability results:
  - LAN reachable
  - intentional localhost-only
  - possible firewall / ZFW / VLAN / bind block
- Docker healthcheck for dev and community app compose.
- ZimaBrain CE self-audit warning for elevated host access.
- Safer third-party app index matching for reverse proxy / Nginx queries.

### Improved
- Reduced false positives in reverse proxy app-store searches.
- Improved firewall diagnostics by separating localhost-only binds from possible firewall blocks.
- Improved network exposure summaries for published ports, tunnel/proxy containers, and Docker DOCKER-USER evidence.
- Improved SMART answers to avoid calling a disk fully healthy when SMART visibility is incomplete.

### Security
- Password protection is enabled by first-run setup.
- Optional `ZIMABRAIN_PASSWORD` environment override remains supported.
- Secrets and password hash files are ignored by git.
- Redacted export is available for safer support sharing.

### Known limitations
- ZimaBrain CE still requires elevated host visibility for local diagnostics.
- Least-privilege hardened compose is not yet the default.
- MCP, persistence/trends, proactive alerts, CI, and multi-arch release workflow are future items.
