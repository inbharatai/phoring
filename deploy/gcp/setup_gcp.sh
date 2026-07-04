#!/usr/bin/env bash
# Phoring — one-shot Google Cloud resource setup.
#
# Creates the Cloud Storage bucket, BigQuery dataset + 4 telemetry tables, and a
# service account used by the Phoring backend to write telemetry + artifacts.
# Idempotent: safe to re-run. Run AFTER `gcloud auth login` and with the correct
# project selected (`gcloud config set project phoring-501306`).
#
# Usage:
#   bash deploy/gcp/setup_gcp.sh
#
# Defaults match the live Phoring deployment (project phoring-501306, asia-south1).

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-phoring-501306}"
REGION="${GCP_REGION:-asia-south1}"
BUCKET="${GCS_BUCKET:-phoring-artifacts-501306}"
DATASET="${BIGQUERY_DATASET:-phoring_telemetry}"
SA_NAME="${GCP_SA_NAME:-phoring-telemetry}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_OUT="${KEY_OUT:-deploy/gcp/phoring-telemetry-key.json}"

echo "==> Project:  ${PROJECT_ID}"
echo "==> Region:   ${REGION}"
echo "==> Bucket:   gs://${BUCKET}"
echo "==> Dataset:  ${DATASET}"
echo "==> SA:       ${SA_EMAIL}"
echo

# ---- 1. Enable required APIs ----
echo "==> Enabling APIs (bigquery, storage, container, artifactregistry)..."
gcloud services enable --project="${PROJECT_ID}" \
  bigquery.googleapis.com storage.googleapis.com \
  container.googleapis.com artifactregistry.googleapis.com

# ---- 2. Cloud Storage bucket ----
echo "==> Creating GCS bucket gs://${BUCKET} (region ${REGION})..."
if gcloud storage buckets list --project="${PROJECT_ID}" --format="value(name)" | grep -qx "${BUCKET}"; then
  echo "    bucket already exists — skipping"
else
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="${PROJECT_ID}" --location="${REGION}" \
    --uniform-bucket-level-access
fi

# ---- 3. BigQuery dataset ----
echo "==> Ensuring BigQuery dataset ${DATASET} (location ${REGION})..."
if bq --location="${REGION}" ls --project_id="${PROJECT_ID}" | grep -qw "${DATASET}"; then
  echo "    dataset already exists — skipping"
else
  bq --location="${REGION}" mk --dataset --project_id="${PROJECT_ID}" "${PROJECT_ID}:${DATASET}"
fi

# ---- 4. BigQuery tables (idempotent CREATE IF NOT EXISTS) ----
echo "==> Creating BigQuery tables (idempotent)..."
DS="${PROJECT_ID}:${DATASET}"
bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
  "CREATE TABLE IF NOT EXISTS \`${DATASET}.simulation_runs\`(simulation_id STRING NOT NULL, status STRING, total_rounds INT64, started_at STRING, completed_at STRING, duration_seconds FLOAT64, twitter_actions_count INT64, reddit_actions_count INT64, error STRING, ts STRING NOT NULL)" >/dev/null
bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
  "CREATE TABLE IF NOT EXISTS \`${DATASET}.agent_events\`(simulation_id STRING NOT NULL, round_num INT64, platform STRING, agent_id STRING, agent_name STRING, action_type STRING, success BOOL, ts STRING NOT NULL)" >/dev/null
bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
  "CREATE TABLE IF NOT EXISTS \`${DATASET}.report_evaluations\`(report_id STRING NOT NULL, simulation_id STRING, validators STRING, overall_verdict STRING, overall_confidence FLOAT64, total_predictions INT64, validators_used INT64, ts STRING NOT NULL)" >/dev/null
bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false \
  "CREATE TABLE IF NOT EXISTS \`${DATASET}.user_feedback\`(report_id STRING, simulation_id STRING NOT NULL, user_message STRING, agent_response STRING, tool_calls_count INT64, ts STRING NOT NULL)" >/dev/null
echo "    tables: simulation_runs, agent_events, report_evaluations, user_feedback"
echo "    (schema also in deploy/gcp/bigquery_schema.sql for reference)"

# ---- 5. Service account + roles ----
echo "==> Ensuring service account ${SA_EMAIL}..."
if gcloud iam service-accounts list --project="${PROJECT_ID}" --format="value(email)" | grep -qx "${SA_EMAIL}"; then
  echo "    SA already exists — skipping create"
else
  gcloud iam service-accounts create "${SA_NAME}" --project="${PROJECT_ID}" \
    --display-name="Phoring telemetry + artifact writer"
fi

echo "==> Granting roles (bigquery.dataEditor, storage.objectAdmin)..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.dataEditor" >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin" >/dev/null

# ---- 6. Credential strategy (no JSON key by default) ----
# This project enforces the org policy `iam.disableServiceAccountKeyCreation`,
# which blocks downloading a service-account JSON key. Google recommends
# ADC / Workload Identity over key files anyway, so we use those:
#   * Local dev / GCE VM: Application Default Credentials.
#       Run `gcloud auth application-default login` (or attach the SA to the
#       VM and let the metadata server provide ADC with no key file).
#   * GKE: Workload Identity — bind a Kubernetes ServiceAccount to this GCP
#       SA (see deploy/gke/README.md). The pod then gets ADC automatically.
#
# We attempt a key download only as an optional fallback and never fail.
echo "==> Credential strategy: ADC / Workload Identity (no key file)."
KEY_CREATED=false
if gcloud iam service-accounts keys create "${KEY_OUT}" \
     --project="${PROJECT_ID}" --iam-account="${SA_EMAIL}" 2>/dev/null; then
  chmod 600 "${KEY_OUT}" 2>/dev/null || true
  KEY_CREATED=true
  echo "    (optional) SA key written to ${KEY_OUT} — gitignored, never commit."
else
  echo "    SA key creation blocked by org policy (expected). Using ADC / Workload Identity."
  rm -f "${KEY_OUT}"
fi

echo
echo "=============================================================="
echo "DONE. Resources created:"
echo "  - gs://${BUCKET}  (Cloud Storage, ${REGION})"
echo "  - ${DATASET}  (BigQuery: simulation_runs, agent_events,"
echo "                  report_evaluations, user_feedback)"
echo "  - ${SA_EMAIL}  (roles/bigquery.dataEditor + roles/storage.objectAdmin)"
echo
echo "Add this block to your Phoring .env (backend):"
echo "--------------------------------------------------------------"
cat <<EOF
GCP_PROJECT_ID=${PROJECT_ID}
ENABLE_GCS=true
GCS_BUCKET=${BUCKET}
ENABLE_BIGQUERY=true
BIGQUERY_DATASET=${DATASET}
EOF
echo "--------------------------------------------------------------"
if [ "${KEY_CREATED}" = "true" ]; then
  echo "Optionally set GOOGLE_APPLICATION_CREDENTIALS to ${KEY_OUT}."
else
  echo "For ADC: run 'gcloud auth application-default login' on the host."
  echo "For GKE: use Workload Identity (see deploy/gke/README.md)."
fi
echo "=============================================================="