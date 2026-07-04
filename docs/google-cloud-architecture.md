# Phoring — Google Cloud architecture

This is the reviewer-facing proof layer for Phoring's Google Cloud usage. Every
claim below maps to a concrete file path or live resource you can inspect.

## Services used (and where they're wired)

| Service | Role in Phoring | Where it's wired / created |
|---|---|---|
| **Google Kubernetes Engine** | Hosts the containerized Phoring frontend + backend image (Autopilot cluster `phoring`, `asia-south1`). A `BackendConfig` (`timeoutSec: 300`) raises the GCE Ingress backend timeout so the ~30s synchronous ontology build doesn't 502 under the default 30s limit. | `deploy/gke/manifests.yaml` (Deployment, Service, BackendConfig, Ingress, ManagedCertificate), `deploy/gke/deploy.sh`, `deploy/gke/README.md` |
| **Artifact Registry + Cloud Build** | Builds the image from repo source and stores it at `asia-south1-docker.pkg.dev/phoring-501306/phoring/phoring:latest` | `deploy/gke/deploy.sh` (`gcloud builds submit --tag ...`), `.gcloudignore` |
| **Cloud Storage** | Mirrors uploaded documents, generated report Markdown + section files, and simulation artifacts to `gs://phoring-artifacts-501306`; report download streams from GCS when the local cache is missing | `backend/app/utils/gcp_clients.py` (`GcsService`), wired in `backend/app/models/project.py` (`save_file_to_project`), `backend/app/services/report_agent.py` (`save_section`, `assemble_full_report`, `save_report`), `backend/app/api/report.py` (`download_report`) |
| **BigQuery** | Append-only telemetry: `simulation_runs`, `agent_events` (batched), `report_evaluations`, `user_feedback` in dataset `phoring_telemetry` | `backend/app/utils/gcp_clients.py` (`BigQueryLogger`), wired in `backend/app/services/simulation_runner.py` (run start/complete, agent events), `backend/app/services/report_agent.py` (consensus evaluation), `backend/app/api/report.py` (Q&A). Schema: `deploy/gcp/bigquery_schema.sql` |
| **Gemini API** | Primary reasoning + report generation (Gemini 2.5 Pro) and Validator-3 consensus (Gemini 2.0 Flash) via `generativelanguage.googleapis.com` | `backend/app/config.py` (`LLM_BASE_URL`, `LLM_VALIDATOR_3_*`), `backend/app/utils/llm_client.py`. See README "Multi-AI Consensus Validation" |
| **Compute Engine** | Original host: `e2-standard-2` VM `phoring` in `asia-south1-a` with a 100 GB persistent disk | `deploy/gce/` (`create-vm.sh`, `vm-setup.sh`, `phoring.service`, `Caddyfile`, `README.md`) |

> **Honest scope note:** Gemini usage is the **Gemini API**, not Vertex AI /
> Gemini Enterprise Agent Platform. BigQuery is **append-only telemetry**
> (not a BI/query layer) — Looker and Managed Service for Apache Spark are
> not used. Local disk remains the primary working store; Cloud Storage is a
> durable mirror + the download fallback.

## Architecture diagram

```
                 ┌──────────────────────────────────────────────┐
                 │  Google Kubernetes Engine (asia-south1)      │
                 │  Autopilot cluster "phoring"                 │
                 │                                              │
                 │  Pod (image: AR phoring:latest)              │
                 │   ├─ Vue frontend + landing (static)         │
                 │   ├─ Flask backend (run.py)                  │
                 │   └─ KSA phoring-telemetry ──┐               │
                 │      (Workload Identity)     │               │
                 └──────────────────────────────┼──────────────┘
                                                │ ADC (no key file)
                       ┌────────────────────────┼────────────────┐
                       ▼                        ▼                ▼
              ┌─────────────────┐    ┌──────────────────┐  ┌──────────────┐
              │ Cloud Storage   │    │ BigQuery         │  │ Gemini API   │
              │ gs://phoring-   │    │ phoring_telemetry│  │ 2.5 Pro +    │
              │   artifacts-    │    │  simulation_runs │  │ 2.0 Flash    │
              │   501306        │    │  agent_events    │  │ (reasoning + │
              │ uploads +       │    │  report_evals    │  │  validation) │
              │ reports mirror  │    │  user_feedback   │  └──────────────┘
              └─────────────────┘    └──────────────────┘
                       ▲                        ▲
                       │ mirror writes          │ telemetry rows
                       │ (GcsService)           │ (BigQueryLogger)
                       └────────────────────────┘
```

## Enable it (env vars, all default-off)

```env
GCP_PROJECT_ID=phoring-501306
ENABLE_GCS=true
GCS_BUCKET=phoring-artifacts-501306
ENABLE_BIGQUERY=true
BIGQUERY_DATASET=phoring_telemetry
# Tables default to simulation_runs / agent_events / report_evaluations / user_feedback
```

When `ENABLE_*` is `false` (or the `google-cloud-*` package is missing, or
config is unset), every call degrades to a no-op and **never** raises — the
pipeline is unaffected. See `backend/app/utils/gcp_clients.py` for the
graceful-degradation contract.

## One-shot resource setup

```bash
gcloud auth login
gcloud config set project phoring-501306
bash deploy/gcp/setup_gcp.sh
```

This creates the GCS bucket, the BigQuery dataset + 4 tables, the
`phoring-telemetry` service account with `roles/bigquery.dataEditor` +
`roles/storage.objectAdmin`, and the Workload Identity binding for GKE. It does
**not** download a JSON key (blocked by the `iam.disableServiceAccountKeyCreation`
org policy) — use ADC locally (`gcloud auth application-default login`) or
Workload Identity on GKE.

## Verify it live

```bash
# BigQuery: see the latest run rows
bq query --use_legacy_sql=false \
  "SELECT simulation_id, status, total_rounds, duration_seconds FROM \`phoring_telemetry.simulation_runs\` ORDER BY ts DESC LIMIT 10"

# Cloud Storage: list mirrored reports
gcloud storage ls gs://phoring-artifacts-501306/reports/

# GKE: pods + service
kubectl get pods
kubectl get svc phoring
curl http://$(kubectl get svc phoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/health
```

## Tests (no GCP credentials required)

```bash
cd backend && python -m pytest tests/test_gcp_integrations.py -q
```

Asserts config-gating guards, disabled-by-default no-op behavior, and that a
monkeypatched BigQuery client captures the expected rows.