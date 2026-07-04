# Phoring — Google Kubernetes Engine deployment

Phoring ships as a single container image (frontend + landing + backend API in
one process). This folder deploys that image to a **GKE Autopilot** cluster in
`asia-south1` with **Workload Identity** (no service-account JSON keys — the
org policy `iam.disableServiceAccountKeyCreation` blocks keys, and Google
recommends Workload Identity anyway).

## What this gives you

- **GKE Autopilot** cluster `phoring` in `asia-south1`.
- **Artifact Registry** repo `asia-south1-docker.pkg.dev/phoring-501306/phoring`
  holding `phoring:latest` (built by **Cloud Build** from the repo source).
- A **Deployment** (1 replica) + **LoadBalancer Service** + **Google-managed
  TLS Ingress** for `phoring.in` on a reserved global static IP
  (`phoring-ingress-ip` → `136.69.52.125`).
- **Workload Identity**: the pod's Kubernetes ServiceAccount `phoring-telemetry`
  is bound to the GCP service account
  `phoring-telemetry@phoring-501306.iam.gserviceaccount.com`, so the backend's
  BigQuery + Cloud Storage calls authenticate with ADC — zero key files.

## Prerequisites

```bash
gcloud auth login
gcloud config set project phoring-501306
# One-shot: create the GCS bucket, BigQuery dataset/tables, and the
# phoring-telemetry GCP service account + Workload Identity binding:
bash deploy/gcp/setup_gcp.sh
```

`setup_gcp.sh` grants the IAM roles Cloud Build needs and creates the
`roles/iam.workloadIdentityUser` binding on the GCP SA for the Kubernetes SA
`default/phoring-telemetry`.

## Deploy

1. **Create the env Secret.** Copy `deploy/gce/.env.gce.example` to
   `deploy/gke/.env.gke`, fill in the real keys, and append the GCP block:

   ```env
   GCP_PROJECT_ID=phoring-501306
   ENABLE_GCS=true
   GCS_BUCKET=phoring-artifacts-501306
   ENABLE_BIGQUERY=true
   BIGQUERY_DATASET=phoring_telemetry
   ```

   Do **not** set `GOOGLE_APPLICATION_CREDENTIALS` on GKE — Workload Identity
   supplies ADC. Then:

   ```bash
   bash deploy/gke/create-secret.sh deploy/gke/.env.gke
   ```

2. **Build, apply, and go live:**

   ```bash
   bash deploy/gke/deploy.sh
   ```

   This runs Cloud Build → ensures the cluster → wires kubectl → applies the
   manifests → prints the LoadBalancer IP.

3. **Verify:**

   ```bash
   kubectl get pods
   curl http://$(kubectl get svc phoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}')/health
   ```

4. **Point DNS.** Add an A record `phoring.in` → Ingress IP
   (`136.69.52.125`, the reserved global static IP `phoring-ingress-ip`). The
   `ManagedCertificate` activates and `https://phoring.in` goes live within
   ~10–30 minutes of DNS propagation. Verify with
   `kubectl get managedcertificate phoring-cert` (status → `Active`).

## Files

| File | Purpose |
|---|---|
| `manifests.yaml` | KSA (Workload Identity), Deployment, Service, **BackendConfig** (300s LB timeout), Ingress, ManagedCertificate, HPA |
| `deploy.sh` | End-to-end: build → cluster → kubectl → apply |
| `create-secret.sh` | Create the `phoring-env` Secret from a `.env` file |

> **BackendConfig (300s timeout):** the GCE HTTP(S) Load Balancer used by the
> GKE Ingress defaults to a 30-second backend timeout, which 502s the
> synchronous `/api/graph/ontology/generate` step (Gemini 2.5 Pro, ~33s).
> `manifests.yaml` ships a `BackendConfig` (`timeoutSec: 300`) linked to the
> Service via `cloud.google.com/backend-config` so the ontology build completes
> through the Ingress.

## Telemetry + artifacts

With `ENABLE_BIGQUERY=true` + `ENABLE_GCS=true` in the Secret, the GKE pod:

- Logs every simulation run, agent event (batched), report evaluation, and
  report Q&A exchange to BigQuery dataset `phoring_telemetry`.
- Mirrors uploaded documents + generated report Markdown to
  `gs://phoring-artifacts-501306`.

Both authenticate via Workload Identity (the `phoring-telemetry` KSA → GCP SA),
which has `roles/bigquery.dataEditor` + `roles/storage.objectAdmin`.