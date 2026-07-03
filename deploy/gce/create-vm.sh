#!/usr/bin/env bash
# ============================================================================
# Phoring — Create GCE VM for cohort submission.
# Run this from a machine with `gcloud` authed (Cloud Shell or your laptop).
#
# Spec (per decision):
#   Machine:  e2-standard-2   (2 vCPU, 8 GB)  -> bump to e2-standard-4 on OOM
#   Region:   asia-south1
#   Boot:     30 GB Debian 12
#   Data:     100 GB persistent disk (mounted at /app/backend/uploads)
#   Net:      static external IP + HTTP/HTTPS firewall + Caddy auto-TLS
# ============================================================================
set -euo pipefail

PROJECT="phoring-501306"              # your GCP project id
REGION="asia-south1"
ZONE="asia-south1-a"
VM="phoring"
DOMAIN="${DOMAIN:-phoring.inbharat.ai}"   # point this A record at the static IP

echo "==> Using project: $PROJECT  zone: $ZONE  domain: $DOMAIN"
gcloud config set project "$PROJECT" 2>/dev/null || true

# 1) Reserve a static external IP (idempotent)
if ! gcloud compute addresses describe phoring-ip --region="$REGION" >/dev/null 2>&1; then
  echo "==> Reserving static IP phoring-ip ..."
  gcloud compute addresses create phoring-ip --region="$REGION"
fi
STATIC_IP=$(gcloud compute addresses describe phoring-ip --region="$REGION" --format='value(address)')
echo "==> Static IP: $STATIC_IP"

# 2) Firewall: allow 80/443 to the VM tag 'phoring' (idempotent)
if ! gcloud compute firewall-rules describe allow-http-phoring >/dev/null 2>&1; then
  gcloud compute firewall-rules create allow-http-phoring \
    --allow tcp:80 --source-ranges 0.0.0.0/0 --target-tags phoring
fi
if ! gcloud compute firewall-rules describe allow-https-phoring >/dev/null 2>&1; then
  gcloud compute firewall-rules create allow-https-phoring \
    --allow tcp:443 --source-ranges 0.0.0.0/0 --target-tags phoring
fi

# 3) Create the VM with attached 100 GB data disk + startup script
echo "==> Creating VM $VM (e2-standard-2, $ZONE) ..."
gcloud compute instances create "$VM" \
  --zone="$ZONE" \
  --machine-type=e2-standard-2 \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-balanced \
  --create-disk=name="phoring-data-1",size=100GB,type=pd-standard,mode=rw \
  --address="$STATIC_IP" \
  --tags=phoring \
  --metadata DOMAIN="$DOMAIN" \
  --metadata-from-file startup-script=vm-setup.sh

echo ""
echo "==> Done. VM booting. Next steps:"
echo "    1) gcloud compute ssh $VM --zone=$ZONE"
echo "    2) sudo cp /opt/phoring/.env.example /opt/phoring/.env"
echo "    3) sudo nano /opt/phoring/.env   # fill real keys"
echo "    4) sudo systemctl restart phoring"
echo "    5) curl http://$STATIC_IP/health"
echo ""
echo "==> Point $DOMAIN A record -> $STATIC_IP for auto HTTPS."
echo "==> If simulations OOM, upgrade:"
echo "    gcloud compute instances set-machine-type $VM --zone=$ZONE --machine-type=e2-standard-4"