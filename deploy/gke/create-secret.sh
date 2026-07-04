#!/usr/bin/env bash
# Create the `phoring-env` Kubernetes Secret from a local .env file.
#
# Usage:
#   bash deploy/gke/create-secret.sh /path/to/.env.gke
#
# The .env file must contain the real Phoring runtime keys (LLM_API_KEY,
# ZEP_API_KEY, etc.) plus the Google Cloud block from deploy/gcp/setup_gcp.sh:
#   GCP_PROJECT_ID=phoring-501306
#   ENABLE_GCS=true
#   GCS_BUCKET=phoring-artifacts-501306
#   ENABLE_BIGQUERY=true
#   BIGQUERY_DATASET=phoring_telemetry
# Do NOT set GOOGLE_APPLICATION_CREDENTIALS on GKE — Workload Identity provides
# ADC automatically to pods using the `phoring-telemetry` service account.

set -euo pipefail

ENV_FILE="${1:-deploy/gke/.env.gke}"
if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: env file not found: ${ENV_FILE}" >&2
  echo "Create one from deploy/gce/.env.gce.example + the GCP block." >&2
  exit 1
fi

echo "==> Creating/updating Secret phoring-env from ${ENV_FILE}..."
kubectl create secret generic phoring-env \
  --namespace=default \
  --from-env-file="${ENV_FILE}" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "==> Secret phoring-env applied (namespace=default)."
echo "    (Keys are base64-encoded at rest; never commit ${ENV_FILE}.)"