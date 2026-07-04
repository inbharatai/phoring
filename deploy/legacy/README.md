# Legacy deployment configs

Files here are kept for history only and are **not** the current deployment path.

- `render.yaml` — the original Render Blueprint. Phoring migrated off Render to
  Google Cloud (Compute Engine, then GKE Autopilot). The live deployment is
  described in [`../gke/README.md`](../gke/README.md) (GKE) and
  [`../gce/README.md`](../gce/README.md) (Compute Engine). Do not use this file
  for new deploys.