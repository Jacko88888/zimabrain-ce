# ZimaBrain MCP Storage Corrections v0.8.1

This corrective overlay follows live Cube verification of the v0.8 storage layer.

- MCP server version: `0.6.1`
- Storage collector version: `0.1.1`
- ZimaBrain preview version: `v1.7.0-mcp-preview.4`

Corrections:

- Separates collector transport success from evidence health status.
- Detects configured ZFS pools rather than treating a loaded kernel module as a pool.
- Reads NVMe controller identity, state and temperature from host sysfs without granting device-write or broad administrative access.
- Marks endurance, media errors and critical-warning counters as unverified when the safe boundary blocks NVMe administrative ioctls.
- Deduplicates capacity evidence by backing source and removes nested Docker overlay paths.
- Treats read-only ISO9660 and SquashFS media as informational even when `df` reports 100% used.
- Expands inventory answers to list each physical device, size and observed filesystem types.
- Explains historical SATA CRC counts as likely cable, connector or backplane-path evidence rather than disk-media failure by itself.
- Corrects RAID wording when the ZFS module is loaded but no pool is configured.

No persistent data, audit history, password, secret, base Compose file or device permission is included or changed.
