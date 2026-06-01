# Deployment Guide — RTS Hub Integration

This file is tracked on the `rts-integration` branch only.
Do NOT submit it upstream.

## Repository layout

```
upstream:         https://github.com/pewdiepie-archdaemon/odysseus  (main)
our fork:         https://github.com/yegorsb/odysseus
our branch:       rts-integration
```

### Remote setup (already configured on the local clone)

```
origin    → git@github.com:yegorsb/odysseus.git   (your fork, push here)
upstream  → https://github.com/pewdiepie-archdaemon/odysseus.git  (pull only)
```

---

## Pulling upstream updates

Run this whenever pewdiepie-archdaemon ships a new release:

```bash
# 1. Fetch upstream changes
git fetch upstream

# 2. Merge into your local main (no custom commits live here)
git checkout main
git merge upstream/main
git push origin main          # keep fork's main in sync

# 3. Rebase rts-integration on the updated main
git checkout rts-integration
git rebase main               # resolve any conflicts here
git push origin rts-integration --force-with-lease
```

---

## First-time deployment on dgx-spark

```bash
ssh ts_dgx

# Clone your fork, rts-integration branch
sudo mkdir -p /srv/odysseus
sudo git clone --branch rts-integration \
    git@github.com:yegorsb/odysseus.git /srv/odysseus

cd /srv/odysseus

# Create .env from the DGX template
sudo cp .env.dgx.example .env
sudo nano .env
# → Fill in WEBUI_URL with your Tailscale hostname
# → Confirm APP_BIND matches your Tailscale IP (tailscale ip -4)
# → Set PUID/PGID to match the /srv owner

# Start all services
sudo docker compose up -d

# Run one-time hardening (disables signup, creates .mgmt.conf)
cd /srv/rts-hub/odysseus
sudo ./setup.sh

# Import existing 'ai' group members as Odysseus users
./sync_users.sh
```

---

## Updating the deployment on dgx-spark

```bash
ssh ts_dgx
cd /srv/odysseus

# Pull latest rts-integration commits
sudo git pull origin rts-integration

# Rebuild and restart (only odysseus container if only Python changed)
sudo docker compose up -d --build odysseus

# Or restart everything
sudo docker compose down && sudo docker compose up -d
```

---

## Adding a new user

```bash
# On dgx-spark:
sudo usermod -aG ai <newusername>        # add to Linux ai group
cd /srv/rts-hub/odysseus
./sync_users.sh                          # creates Odysseus account + prints temp password
# → Send temp password to the user; they must change it on first login
```

## Resetting a user's password

```bash
cd /srv/rts-hub/odysseus
./reset_user.sh <username>
```

---

## Importing the RTS Games Tool into Odysseus

After any fresh database setup, re-import the tool:

1. Open `https://<ts-host>:7000` → Admin → Workspace → Functions
2. [+] New Function → paste contents of `tools/rts_games_tool.py` → Save

See `tools/README.md` for full usage including Monte Carlo group chat setup.

---

## Files tracked on rts-integration (not sent upstream)

| File | Purpose |
|------|---------|
| `docker-compose.override.yml` | DGX port fix (SearXNG 8080→8088) |
| `.env.dgx.example` | .env template for dgx-spark |
| `tools/rts_games_tool.py` | Open WebUI Function for RTS game integration |
| `tools/README.md` | Tool usage docs |
| `DEPLOYMENT.md` | This file |
