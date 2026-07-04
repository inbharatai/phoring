#!/usr/bin/env bash
# Phoring — end-to-end GKE deploy.
#
# Builds the image into Artifact Registry (via Cloud Build), ensures the
# Autopilot cluster exists, wires kubectl, creates the env Secret, applies the
# manifests, and prints the live LoadBalancer + Ingress IPs.
#
# Run after `gcloud auth login` with project phoring-501306 selected.
#   bash deploy/gke/deploy.sh
#
# Idempotent: safe to re-run. Requires the IAM grants from deploy/gcp/setup_gcp.sh
# (Cloud Build SA + Workload Identity binding).

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-phoring-501306}"
REGION="${GCP_REGION:-asia-south1}"
CLUSTER="${GKE_CLUSTER:-phoring}"
AR_REPO="asia-south1-docker.pkg.dev/${PROJECT_ID}/phoring/phoring"
IMAGE="${AR_REPO}:latest"
ENV_FILE="${ENV_FILE:-deploy/gke/.env.gke}"

echo "==> [1/6] Ensure Artifact Registry repo 'phoring' exists..."
gcloud artifacts repositories describe phoring --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1 \
  || gcloud artifacts repositories create phoring --project="${PROJECT_ID}" \
       --repository-format=docker --location="${REGION}"

echo "==> [2/6] Build + push image to ${IMAGE} (Cloud Build)..."
gcloud builds submit . --project="${PROJECT_ID}" --tag="${IMAGE}" \
  --machine-type=e2-highcpu-8 --timeout=1800s

echo "==> [3/6] Ensure GKE Autopilot cluster '${CLUSTER}' exists..."
gcloud container clusters describe "${CLUSTER}" --project="${PROJECT_ID}" --region="${REGION}" >/dev/null 2>&1 \
  || gcloud container clusters create-auto "${CLUSTER}" --project="${PROJECT_ID}" --region="${REGION}"

echo "==> [4/6] Wire kubectl to the cluster..."
gcloud container clusters get-credentials "${CLUSTER}" --project="${PROJECT_ID}" --region="${REGION}"

echo "==> [5/6] Create env Secret from ${ENV_FILE} (if present)..."
if [ -f "${ENV_FILE}" ]; then
  bash "$(dirname "$0")/create-secret.sh" "${ENV_FILE}"
else
  echo "    ${ENV_FILE} not found — skipping Secret creation."
  echo "    Create it then: bash deploy/gke/create-secret.sh ${ENV_FILE}"
fi

echo "==> [6/6] Apply manifests..."
kubectl apply -f "$(dirname "$0")/manifests.yaml"

echo
echo "Waiting for LoadBalancer IP (this can take a couple of minutes)..."
sleep 20
LB_IP=$(kubectl get svc phoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
echo "  LoadBalancer IP: ${LB_IP:-<pending — run 'kubectl get svc phoring -w'>}"
echo "  Ingress IP:      run 'kubectl get ingress phoring'"
echo
echo "Verify:"
echo "  curl http://${LB_IP:-<LB-IP>}/health"
echo
echo "Once DNS A record phoring.inbharat.ai -> Ingress IP is set, the managed"
echo "certificate activates and https://phoring.inbharat.ai goes live."