# ZimaBrain CE — ZimaOS Community App

Local ZimaOS diagnostic assistant for ZimaOS.

## App details

- App name: ZimaBrain CE
- Image: `gelbuilding/zimabrain-ce:1.6.2-beta`
- Web UI port: `8601`
- Persistent data path: `/DATA/AppData/zimabrain-ce`
- Web UI: `http://<your-zima-ip>:8601`

## Install by Docker Compose

```bash
mkdir -p /DATA/AppData/zimabrain-ce
cd /DATA/AppData/zimabrain-ce
curl -fsSL https://raw.githubusercontent.com/Jacko88888/zimabrain-ce/main/packaging/zimaos-community-app/docker-compose.yml -o docker-compose.yml
docker compose up -d
docker ps --filter name=zimabrain-ce --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

```

Then open:

```text
http://<your-zima-ip>:8601
```
