# 11 · Deployment

**Requirement:** a public URL plus 4 accounts, **kept live through review, the semifinal and the Grand Finale**. That means no free tiers that sleep or expire.

## Primary: Azure for Students VM (free credit) running the same Docker Compose
| Item | Choice |
|---|---|
| VM | Ubuntu 24.04, **B2s** (2 vCPU, 4 GB) or B1ms; region Central India / Southeast Asia (closest to Sri Lanka) |
| Cost | Covered by the $100 student credit (B2s is about $30/month; B1ms about $15/month) |
| DNS | Azure public IP DNS label → `xora-waypoint.<region>.cloudapp.azure.com` |
| HTTPS | **Caddy** reverse proxy (automatic Let's Encrypt), required for the PWA service worker |
| Ports | 80/443 open; 22 restricted to our IPs |

### Steps
```bash
# on the VM
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER && newgrp docker
git clone https://github.com/jtharindudhanushka/Xora_Waypoint.git && cd Xora_Waypoint
cp .env.example .env   # set POSTGRES_PASSWORD, JWT_SECRET, PUBLIC_HOST, DATASET_DIR=/srv/xora/datasets
# from your laptop: copy the dataset pack (never via git)
#   scp -r ./datasets azureuser@<ip>:/srv/xora/datasets
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
`docker-compose.prod.yml` adds the Caddy service (ports 80/443, `Caddyfile` with `{$PUBLIC_HOST}`), sets `restart: unless-stopped`, and mounts `DATASET_DIR` read-only into `api`.

### Live deployment (4 Oct 2026)
- **URL:** https://xora-waypoint.southeastasia.cloudapp.azure.com (Southeast Asia, resource group `xora-rg`, VM `xora-vm`).
- **Size:** **B1ms** (1 vCPU, 2 GB) + 2 GB swap + 30 GB Standard SSD, about $21/month on the student credit. Postgres, API, nginx and Caddy fit; images are built on the VM.
- **SSH** is allowed only from listed team IPs (NSG rule `default-allow-ssh`). Some mobile carriers send SSH from a different address than web traffic: find it with `echo $SSH_CLIENT` on the VM and add that `/32`. Without SSH, use `az vm run-command invoke -g xora-rg -n xora-vm --command-id RunShellScript --scripts '...'`.
- **Redeploy:** `ssh azureuser@<ip> 'cd Xora_Waypoint && git checkout main && git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build'`.
- **Fixed on first real `compose up`:** `CORS_ORIGINS` as a plain string crashed settings (now `NoDecode` + split); the web healthcheck used `localhost` (IPv6) while nginx listens on IPv4.
- **Stop all charges after the finale:** `az group delete -n xora-rg`.

### Operations
- **Health:** `https://<host>/api/v1/health`.
- **Backups:** nightly `pg_dump` to the VM disk (not to git).
- **Freeze after submission.** No deploys during the review window unless something is broken.
- **Reset the demo:** `docker compose exec api python -m app.seed --reset-demo`.

## Fallback: Render (web + API) + Neon (Postgres), free
- Neon free Postgres doesn't expire; Render free web services **sleep after 15 min** (~50 s cold start). Acceptable only as a backup URL.
- The dataset is uploaded once by running the seed from a laptop against the Neon `DATABASE_URL`.

## Environment variables (`.env.example`)
See the root [`.env.example`](../.env.example). The key ones are `DATABASE_URL`, `JWT_SECRET`, `DATASET_DIR`, `DEMO_START`, `PUBLIC_HOST`, `CORS_ORIGINS`.
