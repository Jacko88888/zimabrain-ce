# Install ZimaBrain CE

ZimaBrain CE is currently in private beta.

Current tested version:

v1.6.0-beta

## Requirements

- ZimaOS machine
- Docker available
- Docker Compose available
- Access to the private GitHub repository
- A free port for the Flask UI

## Recommended install path

For ZimaOS testing, use an AppData folder:

    /DATA/AppData/zimabrain-ce

For separate test machines, use a different folder name, for example:

    /DATA/AppData/zimabrain-ce-blade-test

## Clone the repository

    cd /DATA/AppData
    git clone https://github.com/Jacko88888/zimabrain-ce.git zimabrain-ce
    cd zimabrain-ce

For private GitHub access, Git may ask for:

    Username: your GitHub username
    Password: GitHub personal access token

GitHub account passwords are not used for Git operations.

## Start the app

From inside the project folder:

    docker compose up -d

## Check container state

    docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

## Open the UI

Open the mapped Flask port shown in docker ps.

Current Cube development path uses:

    /DATA/AppData/zimabrain-ce-flask-8601

Current development UI badge shows:

    App v1.6.0-beta · Reliable Flask mode · Local verifier

## Verify after start

Run:

    docker compose ps
    docker compose logs --tail=80

Then open the UI and confirm the top badge and layer map are visible.

## Current beta notes

- This is a private beta build.
- The app is verifier-first and evidence-first.
- Generated reports, raw downloads, logs, tarballs, private evidence, and secrets are excluded from Git.
- Local ZimaOS evidence should be verified before giving repair guidance.
- ZimaOS containers do not run systemd, so systemctl errors inside containers are expected.
- Do not run destructive Docker cleanup commands unless the evidence clearly supports it.

## Current knowledge sources

Current knowledge sources include:

- Official ZimaOS documentation index
- App-store metadata and third-party app index
- Manually verified app install guides
- Local diagnostic report evidence
- Forum/community issue patterns, used carefully and not treated as official truth
