#!/usr/bin/env bash
# ============================================================================
# Phoring VM startup script — runs ONCE on first boot (as root).
# Installs Docker + Caddy, formats/mounts the 100 GB data disk, writes the
# Caddyfile + phoring systemd service, and starts everything.
# ============================================================================
set -euo pipefail
exec >> >(tee -a /var/log/phoring-setup.log) 2>&1
echo "===== phoring vm-setup $(date) ====="

# --- Read DOMAIN from instance metadata (default: serve on :80, no TLS) ---
DOMAIN=$(curl -fsS "http://metadata.google.internal/computeMetadata/v1/instance/attributes/DOMAIN" \
  -H "Metadata-Flavor: Google" 2>/dev/null || echo "")
echo "DOMAIN=$DOMAIN"

# ----------------------------------------------------------------------------
# 1) Format + mount the 100 GB persistent disk at /mnt/phoring-data
# ----------------------------------------------------------------------------
DATA_DEV="/dev/disk/by-id/google-persistent-disk-1"
if [ ! -b "$DATA_DEV" ]; then
  # Fallback: pick the largest non-boot disk.
  DATA_DEV=$(lsblk -nbpo name,type,size,mountpoint,type \
    | awk '$2=="disk" && $4=="" {print $1, $3}' \
    | sort -k2 -rn | head -n1 | cut -d' ' -f1)
fi
echo "Data device: $DATA_DEV"

if [ -n "${DATA_DEV:-}" ] && [ -b "$DATA_DEV" ]; then
  if ! blkid "$DATA_DEV" >/dev/null 2>&1; then
    echo "==> Formatting $DATA_DEV (ext4) ..."
    mkfs.ext4 -F "$DATA_DEV"
  fi
  MOUNT=/mnt/phoring-data
  mkdir -p "$MOUNT"
  if ! mountpoint -q "$MOUNT"; then
    mount "$DATA_DEV" "$MOUNT"
  fi
  if ! grep -q "$MOUNT" /etc/fstab; then
    echo "$DATA_DEV $MOUNT ext4 defaults,noatime 0 2" >> /etc/fstab
  fi
  mkdir -p "$MOUNT"/projects "$MOUNT"/reports "$MOUNT"/simulations "$MOUNT"/tasks
  echo "==> Data disk mounted at $MOUNT (projects/reports/simulations/tasks ready)"
else
  echo "!! No data disk found — state will live on boot disk at /mnt/phoring-data"
  mkdir -p /mnt/phoring-data/{projects,reports,simulations,tasks}
fi

# ----------------------------------------------------------------------------
# 2) Install Docker
# ----------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker ..."
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

# ----------------------------------------------------------------------------
# 3) Phoring config dir + env template
# ----------------------------------------------------------------------------
mkdir -p /opt/phoring
if [ ! -f /opt/phoring/.env.example ]; then
  cat > /opt/phoring/.env.example <<'ENV'
# ===== Primary LLM (Gemini 2.5 Pro — strongest reasoning model) =====
LLM_API_KEY=your_gemini_api_key_here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL_NAME=gemini-2.5-pro

# ===== Zep Cloud (required — knowledge graph memory) =====
ZEP_API_KEY=your_zep_api_key_here

# ===== Web intelligence (recommended) =====
SERPER_API_KEY=
NEWS_API_KEY=

# ===== Multi-AI consensus validators (cross-family = real diversity) =====
LLM_VALIDATOR_2_API_KEY=
LLM_VALIDATOR_2_BASE_URL=https://api.openai.com/v1
LLM_VALIDATOR_2_MODEL_NAME=gpt-4o-mini
LLM_VALIDATOR_3_API_KEY=
LLM_VALIDATOR_3_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_VALIDATOR_3_MODEL_NAME=gemini-2.0-flash

# ===== Runtime (do NOT change PORT — container + Caddy expect 10000) =====
PORT=10000
FLASK_HOST=0.0.0.0
FLASK_DEBUG=False
SIMULATION_SPEED_MODE=normal
ENABLE_GEOPOLITICAL_EVENTS=true
# Same-origin (landing + /app + /api all on one host) — set if you split origins.
CORS_ORIGINS=https://REPLACE_YOUR_DOMAIN
ENV
fi
# Ensure a working .env exists so the service can boot in degraded state
# (health will report llm_configured:false) until real keys are filled in.
[ -f /opt/phoring/.env ] || cp /opt/phoring/.env.example /opt/phoring/.env

# ----------------------------------------------------------------------------
# 4) phoring systemd service (runs the GHCR image with the data volume)
# ----------------------------------------------------------------------------
cat > /etc/systemd/system/phoring.service <<'SVC'
[Unit]
Description=Phoring full-stack container (landing + app + api)
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=simple
Restart=always
RestartSec=5
TimeoutStartSec=180
ExecStartPre=-/usr/bin/docker rm -f phoring
ExecStart=/usr/bin/docker run --name phoring \
  --env-file /opt/phoring/.env \
  -p 127.0.0.1:10000:10000 \
  -v /mnt/phoring-data:/app/backend/uploads \
  --restart unless-stopped \
  ghcr.io/inbharatai/phoring:latest
ExecStop=/usr/bin/docker stop phoring

[Install]
WantedBy=multi-user.target
SVC
systemctl daemon-reload
systemctl enable phoring

# ----------------------------------------------------------------------------
# 5) Caddy (HTTPS reverse proxy -> 127.0.0.1:10000, auto Let's Encrypt)
# ----------------------------------------------------------------------------
if ! command -v caddy >/dev/null 2>&1; then
  echo "==> Installing Caddy ..."
  apt-get update -y
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

mkdir -p /etc/caddy
if [ -n "$DOMAIN" ]; then
  echo "==> Writing Caddyfile for domain: $DOMAIN (auto HTTPS)"
  cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
    encode gzip zstd
    reverse_proxy 127.0.0.1:10000 {
        header_up X-Forwarded-Proto {scheme}
    }
}
CADDY
else
  echo "==> No DOMAIN set — writing Caddyfile for :80 (no TLS)"
  cat > /etc/caddy/Caddyfile <<'CADDY'
:80 {
    encode gzip zstd
    reverse_proxy 127.0.0.1:10000 {
        header_up X-Forwarded-Proto {scheme}
    }
}
CADDY
fi
systemctl enable --now caddy
systemctl restart caddy

# ----------------------------------------------------------------------------
# 6) Pull image + start the app container
# ----------------------------------------------------------------------------
echo "==> Pulling image (may be slow first time — OASIS/CAMEL deps are heavy) ..."
systemctl restart phoring

echo "===== phoring vm-setup complete ====="
echo "SSH in, edit /opt/phoring/.env with real keys, then: sudo systemctl restart phoring"