# ZimaBrain CE

**Local ZimaOS Knowledge Assistant**

ZimaBrain CE is a verifier-first diagnostic assistant for ZimaOS.

The goal is to help users understand what is happening on their ZimaOS machine by combining local system evidence, official ZimaOS manual knowledge, verified app install guidance, and safe command recommendations.

## Current version

`v1.6.0-beta`

## Current mode

- Reliable Flask mode
- Local verifier
- Layered diagnostic engine
- Evidence-first answers
- Safe command guidance

## Core idea

ZimaBrain CE follows this order:

1. Verify real system evidence
2. Explain the finding in plain language
3. Recommend safe next checks
4. Avoid destructive commands unless clearly required
5. Separate verified facts from guidance

## Current layers

The current beta includes layered checks and knowledge areas such as:

- Official Manual Knowledge Engine
- App Verified Install Guides
- Third-Party App Store Index
- Storage mounts
- Docker bind mounts
- Docker daemon diagnostics
- Container state
- Disk health
- Disk inventory
- Filesystem usage
- Network exposure
- App storage paths
- Backup/Borg checks
- ZimaOS regression notes
- GPU / AI runtime checks
- SMB share diagnostics
- Permission and ownership diagnostics
- Report comparison
- Forum issue intake

## Safety model

This project is built around a verifier-first workflow.

It should not assume:

- Docker images exist locally
- Volumes are on the expected disk
- App paths are correct without checking
- ZimaOS containers use systemd
- Repair commands are safe without evidence

Generated reports, raw source downloads, private evidence, logs, tarballs, secrets, and local backups are excluded from Git.

## Repository status

This repository is private and currently prepared for internal review and development.

