<div align="center">

<img src="./static/image/phoring_logo.png" alt="Phoring Logo" width="68%" />

# Phoring

### Document → Knowledge Graph → Multi-Agent Simulation → Source-Cited Forecast

[![License](https://img.shields.io/badge/License-MIT-2563eb?style=for-the-badge)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)](#quick-start)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue_3-22c55e?style=for-the-badge&logo=vuedotjs&logoColor=white)](#architecture)
[![OASIS](https://img.shields.io/badge/Simulation-OASIS_0.2.5-f97316?style=for-the-badge)](#simulation-engine)
[![Zep](https://img.shields.io/badge/Memory-Zep_Cloud-8b5cf6?style=for-the-badge)](#knowledge-graph)
[![Primary LLM](https://img.shields.io/badge/Primary_LLM-Gemini_2.5_Pro-8b5cf6?style=for-the-badge&logo=google&logoColor=white)](#multi-ai-consensus-validation)
[![Validator 2](https://img.shields.io/badge/Validator_2-GPT_4o_mini-10a37f?style=for-the-badge&logo=openai&logoColor=white)](#multi-ai-consensus-validation)
[![Validator 3](https://img.shields.io/badge/Validator_3-Gemini_2.0_Flash-06b6d4?style=for-the-badge&logo=google&logoColor=white)](#multi-ai-consensus-validation)
[![Web Intel](https://img.shields.io/badge/Web_Intel-Serper-3b82f6?style=for-the-badge)](#web-intelligence)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker&logoColor=white)](#quick-start)
[![GKE](https://img.shields.io/badge/Hosted-GKE_Autopilot-4285f4?style=for-the-badge&logo=googlecloud&logoColor=white)](#google-cloud-usage)
[![BigQuery](https://img.shields.io/badge/Telemetry-BigQuery-4285f4?style=for-the-badge&logo=googlecloud&logoColor=white)](#google-cloud-usage)
[![Cloud Storage](https://img.shields.io/badge/Artifacts-Cloud_Storage-4285f4?style=for-the-badge&logo=googlecloud&logoColor=white)](#google-cloud-usage)
[![Live](https://img.shields.io/badge/Live-GKE_phoring.in-10b981?style=for-the-badge)](https://phoring.in)

**Upload documents. Describe a scenario. Get a simulation-backed, source-cited prediction report.**

[Live Demo](https://phoring.in) · [Quick Start](#quick-start) · [How It Works](#how-it-works) · [API Reference](#api-surface) · [Roadmap](#roadmap)

</div>

---

## What Is Phoring?

Phoring is an **open-source decision intelligence platform** that converts unstructured documents into multi-agent social simulations and delivers source-cited forecast reports.

Upload PDFs, Markdown, or plain text. Describe your scenario objective. Phoring extracts a knowledge graph, generates behaviorally-aligned agent profiles, enriches context with live web intelligence, runs a multi-agent simulation across Twitter and Reddit via [OASIS](https://github.com/camel-ai/oasis), and produces a structured report with inline citations and optional multi-model consensus validation.

```
Documents + Scenario Objective
         │
         ▼
  Knowledge Graph (Zep Cloud)
         │
         ▼
  Agent Profiles + Simulation Config
         │
         ├── Live News (Serper + Event Registry)
         │
         ▼
  OASIS Multi-Agent Simulation
    (Twitter + Reddit in parallel)
         │
         ▼
  Source-Cited Report + Consensus Validation + Q&A
```

**You provide:** source files (`.pdf`, `.md`, `.txt`) and a scenario objective in plain language.

**Phoring produces:**
- A domain ontology and knowledge graph extracted from your documents
- Persona-rich OASIS agent profiles aligned to your scenario
- A parallel Twitter + Reddit multi-agent simulation with real-time action streaming
- A source-cited prediction report with confidence scoring, optional multi-AI consensus validation, and interactive Q&A

---

## Live Demo

**Live (GKE): [https://phoring.in](https://phoring.in)** — the containerized
Phoring image running on a **GKE Autopilot** cluster (`phoring`, `asia-south1`),
image built by Cloud Build and pulled from Artifact Registry, authenticating to
BigQuery + Cloud Storage via **Workload Identity** (no service-account key
file). Served by a GKE Ingress on a reserved global static IP (`136.69.52.125`)
with a **Google-managed TLS certificate** for `phoring.in`; `/health`, the landing
page, and the synchronous `/api/graph/ontology/generate` step all serve 200, and
BigQuery + GCS writes from the pod are verified end-to-end. HTTP-only fallback on
the LoadBalancer VIP: [http://34.14.223.238](http://34.14.223.238). *(The
`phoring.in` A record points at the GKE Ingress IP `136.69.52.125`; the managed
certificate is activating — `https://phoring.in` goes live within ~10–30 min of
the DNS flip. Until the cert is `Active`, `http://phoring.in` serves the same GKE
pod over plain HTTP.)* A `BackendConfig` raises the GCE Ingress backend timeout
to 300s so the ~30s Gemini-2.5-Pro ontology build doesn't 502 under the default
30s limit.

> **Live key configuration:** both hosts run the full key set — primary LLM
> (Google Gemini 2.5 Pro), both consensus validators (OpenAI GPT-4o-mini +
> Google Gemini 2.0 Flash), Zep Cloud, and web intelligence (Serper + News).
> Verified via `/health` and `/api/report/validators` (all 3 slots
> `configured:true`).

**Also running on Compute Engine:** [http://35.200.201.102](http://35.200.201.102)
(secondary / backup) — an `e2-standard-2` VM with a 100 GB persistent disk
(mounted at `/app/backend/uploads`) holding uploads, reports, simulation state,
and task files, fronted by Caddy with Let's Encrypt TLS. Same image, identical
full key set (primary + both validators + Serper + News), same Gemini 2.5 Pro
primary.

---

## Google Cloud Usage

Phoring runs on Google Cloud across the data and application layer. Full
wiring details: [`docs/google-cloud-architecture.md`](docs/google-cloud-architecture.md).

```mermaid
flowchart LR
    pod["GKE Pod<br/>(AR image: phoring:latest)"]
    ksa(("KSA phoring-telemetry<br/>Workload Identity"))
    gcs[["Cloud Storage<br/>gs://phoring-artifacts-501306<br/>uploads + reports"]]
    bq[["BigQuery<br/>phoring_telemetry<br/>runs · events · evals · feedback"]]
    gemini{{"Gemini API<br/>2.5 Pro + 2.0 Flash"}}
    pod --> ksa
    ksa -.ADC.-> gcs
    ksa -.ADC.-> bq
    pod -->|reasoning + validation| gemini
    pod -->|mirror writes| gcs
    pod -->|telemetry rows| bq
    classDef gke fill:#4285f4,stroke:#2a56c6,color:#fff
    classDef data fill:#0f9d58,stroke:#0b7a44,color:#fff
    classDef ai fill:#ea4335,stroke:#c13328,color:#fff
    class pod,gke gke
    class ksa gke
    class gcs,bq data
    class gemini ai
```

| Service | What it does in Phoring | Where it's wired |
|---|---|---|
| **Google Kubernetes Engine** | Hosts the containerized frontend + backend as an Autopilot cluster (`phoring`, `asia-south1`) | [`deploy/gke/`](deploy/gke) — `manifests.yaml`, `deploy.sh`, `README.md` |
| **Artifact Registry + Cloud Build** | Builds the image from repo source and stores `phoring:latest` | `deploy/gke/deploy.sh`, `.gcloudignore` |
| **Cloud Storage** | Mirrors uploaded documents, generated report Markdown + sections, and simulation artifacts to `gs://phoring-artifacts-501306`; report download streams from GCS when the local cache is missing | `backend/app/utils/gcp_clients.py` (`GcsService`); wired in `models/project.py`, `services/report_agent.py`, `api/report.py` |
| **BigQuery** | Append-only telemetry — `simulation_runs`, `agent_events` (batched), `report_evaluations`, `user_feedback` in dataset `phoring_telemetry` | `backend/app/utils/gcp_clients.py` (`BigQueryLogger`); wired in `services/simulation_runner.py`, `services/report_agent.py`, `api/report.py`; schema in `deploy/gcp/bigquery_schema.sql` |
| **Gemini API** | Primary reasoning + report generation (Gemini 2.5 Pro) and Validator-3 consensus (Gemini 2.0 Flash) via the Gemini API | `backend/app/config.py`, `backend/app/utils/llm_client.py` |
| **Compute Engine** | Original host — `e2-standard-2` VM + 100 GB persistent disk | [`deploy/gce/`](deploy/gce) |

Both BigQuery and Cloud Storage are **config-gated** (`ENABLE_BIGQUERY` /
`ENABLE_GCS`, default off) and degrade to no-ops that **never** raise — the
pipeline is unaffected when they're unconfigured. One-shot resource setup:
`bash deploy/gcp/setup_gcp.sh` (creates the bucket, dataset, tables, and a
Workload-Identity-bound service account — no JSON keys, per Google
recommendation and the project's `iam.disableServiceAccountKeyCreation` policy).

> **Honest scope:** Gemini usage is the **Gemini API** (not Vertex AI / Gemini
> Enterprise Agent Platform). BigQuery is **append-only telemetry**, not a BI
> layer (Looker and Managed Service for Apache Spark are not used). Local disk
> is the primary working store; Cloud Storage is the durable mirror + download
> fallback.

---

## Why It Exists

| Problem | What Phoring Does |
|---|---|
| Strategic decisions rely on static documents | Converts documents into dynamic simulation inputs enriched with live news context |
| Scenario intent gets lost between pipeline stages | Propagates `simulation_requirement` end-to-end — graph → profiles → config → simulation → report |
| Simulations lack real-world context | Injects geopolitical events sourced from Serper + Event Registry with full article scraping |
| Reports are hard to trust | Produces inline source citations `[1][2][3]` with a numbered references section |
| Single-model hallucination risk | Multi-AI consensus validation cross-checks predictions across up to 3 independent LLM providers |
| Interrupted simulations are lost | Auto-restarts simulations that were interrupted by server restarts or OOM events |

---

## How It Works

> **Interactive 3D version** of this graph available on the [live demo](https://phoring.in)

```mermaid
flowchart LR
    subgraph INPUT["INPUT"]
        docs["Documents + Scenario"]
    end

    subgraph PROCESSING["PROCESSING"]
        textproc("Text Processor")
        ontology("Ontology Generator")
        webintel("Web Intelligence")
    end

    subgraph SOURCES["WEB SOURCES"]
        serper{"Serper API"}
        eventReg{"Event Registry"}
        scraper{"Social Scraping"}
    end

    subgraph KG["KNOWLEDGE GRAPH"]
        zepgraph(("Zep Knowledge Graph"))
    end

    subgraph AGENTS["AGENT GENERATION"]
        profgen("Profile Generator")
        simconfig("Simulation Config")
    end

    subgraph SIM["SIMULATION"]
        geoevents{"Geopolitical Events"}
        simrunner("OASIS SimRunner")
        twitter["Twitter Environment"]
        reddit["Reddit Environment"]
        zepmemory{"Zep Memory Updater"}
    end

    subgraph REPORT["REPORT"]
        reportagent("Report Agent")
        insightforge{"Insight Forge"}
        panorama{"Panorama Search"}
        interviews{"Agent Interviews"}
        freshweb{"Fresh Web Context"}
    end

    subgraph CONSENSUS["CONSENSUS VALIDATION"]
        consensus(("Consensus Engine"))
        ai1{{"Primary AI (Gemini 2.5 Pro)"}}
        ai2{{"GPT-4o-mini (Validator 2)"}}
        ai3{{"Gemini (Validator 3)"}}
    end

    subgraph OUTPUT["OUTPUT"]
        forecast[["Source-Cited Forecast"]]
    end

    %% Input → Processing fan-out
    docs --> textproc
    docs --> ontology
    docs --> webintel

    %% Web Intelligence → 3 parallel sources
    webintel --> serper
    webintel --> eventReg
    webintel --> scraper

    %% Fan-in to Knowledge Graph
    textproc --> zepgraph
    ontology --> zepgraph
    serper --> zepgraph
    eventReg --> zepgraph
    scraper --> zepgraph

    %% Graph → Agent Generation
    zepgraph --> profgen
    zepgraph --> simconfig
    webintel -.-> profgen

    %% Agents → Simulation
    profgen --> simrunner
    simconfig --> simrunner
    geoevents -.-> simrunner

    %% Parallel platform execution
    simrunner --> twitter
    simrunner --> reddit

    %% Live writeback loop
    twitter -.-> zepmemory
    reddit -.-> zepmemory
    zepmemory -.->|writeback| zepgraph

    %% Simulation → Report
    twitter --> reportagent
    reddit --> reportagent
    zepgraph --> reportagent

    %% Report Agent → 4 tools
    reportagent --> insightforge
    reportagent --> panorama
    reportagent --> interviews
    reportagent --> freshweb

    %% Report → Consensus
    reportagent --> consensus
    webintel -.->|independent fetch| consensus

    %% Hub-spoke: Consensus ↔ Validators
    consensus --> ai1
    consensus --> ai2
    consensus --> ai3
    ai1 --> consensus
    ai2 --> consensus
    ai3 --> consensus

    %% Final output
    consensus --> forecast

    %% Node colors matching the interactive 3D graph
    classDef inputNode fill:#6b7280,stroke:#4b5563,color:#fff
    classDef parseNode fill:#0d6f70,stroke:#0a5a5b,color:#fff
    classDef searchNode fill:#2a9d8f,stroke:#1e7a6e,color:#fff
    classDef newsNode fill:#3b82f6,stroke:#2563eb,color:#fff
    classDef eventNode fill:#8b5cf6,stroke:#7c3aed,color:#fff
    classDef scrapeNode fill:#ec4899,stroke:#db2777,color:#fff
    classDef graphNode fill:#10b981,stroke:#059669,color:#fff
    classDef agentNode fill:#f59e0b,stroke:#d97706,color:#000
    classDef engineNode fill:#e76f51,stroke:#c44a33,color:#fff
    classDef twitterNode fill:#1da1f2,stroke:#0c85d0,color:#fff
    classDef redditNode fill:#ff4500,stroke:#cc3700,color:#fff
    classDef writebackNode fill:#10b981,stroke:#059669,color:#fff
    classDef disruptNode fill:#ef4444,stroke:#dc2626,color:#fff
    classDef reportNode fill:#db5d3b,stroke:#b44830,color:#fff
    classDef toolNode fill:#a855f7,stroke:#9333ea,color:#fff
    classDef validateNode fill:#fbbf24,stroke:#d97706,color:#000
    classDef validatorNode fill:#22c55e,stroke:#16a34a,color:#fff
    classDef claudeNode fill:#f97316,stroke:#ea580c,color:#fff
    classDef geminiNode fill:#06b6d4,stroke:#0891b2,color:#fff
    classDef outputNode fill:#fbbf24,stroke:#d97706,color:#000

    class docs inputNode
    class textproc,ontology parseNode
    class webintel searchNode
    class serper newsNode
    class eventReg eventNode
    class scraper scrapeNode
    class zepgraph graphNode
    class profgen,simconfig agentNode
    class simrunner engineNode
    class twitter twitterNode
    class reddit redditNode
    class zepmemory writebackNode
    class geoevents disruptNode
    class reportagent reportNode
    class insightforge,panorama,interviews,freshweb toolNode
    class consensus validateNode
    class ai1 validatorNode
    class ai2 claudeNode
    class ai3 geminiNode
    class forecast outputNode
```

**25 nodes · 38 edges · 9 pipeline stages** — solid lines show primary data flow, dashed lines show secondary enrichment and feedback loops.

### Five-Step Pipeline

| Step | What Happens |
|---|---|
| **1 · Graph Build** | Upload documents → generate domain ontology → build Zep knowledge graph |
| **2 · Environment Setup** | Configure LLM provider, select validators, set simulation speed mode |
| **3 · Simulation** | Execute parallel OASIS simulation (Twitter + Reddit); monitor per-agent actions in real time |
| **4 · Report** | View source-cited forecast with confidence scores; download as Markdown |
| **5 · Q&A** | Ask follow-up questions answered by the Report Agent using graph tools + web intelligence |

---

## Simulation Engine

Simulations run as **isolated subprocesses** managed by the backend. The runner tracks per-agent actions, round progress, and platform-specific state across Twitter and Reddit in parallel.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Intel as Web Intelligence
    participant Runtime as OASIS Runtime
    participant Report as Report Agent

    User->>Frontend: Upload documents + scenario objective
    Frontend->>Backend: Generate ontology + build Zep graph
    Backend->>Intel: Fetch live news (Serper + Event Registry)
    Backend->>Backend: Generate OASIS profiles + simulation config
    Backend->>Runtime: Spawn parallel subprocess (Twitter + Reddit)
    Runtime-->>Backend: Stream agent actions + round summaries
    Backend->>Report: Generate source-cited report (ReACT loop)
    Report-->>Frontend: Final report + confidence scores + Q&A
```

**Key runtime features:**
- **Parallel execution**: Twitter and Reddit simulations run concurrently via `asyncio.gather()`
- **Real-time streaming**: Agent actions are streamed to the frontend via JSONL action logs polled every 2 seconds
- **Stall detection**: Adaptive timeout (15 min base + 30s per agent, capped at 45 min) auto-kills stuck simulations
- **Auto-restart on crash**: If the backend restarts mid-simulation (OOM, deploy), orphaned simulations are automatically relaunched from saved parameters
- **Speed modes**: `normal` (full fidelity), `fast` (~24 rounds), `express` (~12 rounds)

---

## Core Capabilities

### Knowledge Graph
Documents are parsed, chunked, and processed through an LLM-driven ontology generator that extracts entities, relationships, and domain structure. These are stored as a graph in **Zep Cloud**, serving as the memory layer for profile generation, simulation context, and report Q&A.

### Web Intelligence
Before simulation, the platform fetches live context from multiple sources:

| Source | Method |
|---|---|
| **Serper** | Google Search queries → full article bodies scraped at 4,000+ characters |
| **Event Registry** | Geopolitical event articles via `eventregistry.org` API (7-day recency window) |
| **Social content** | Site-specific Serper `site:` queries targeting Reddit, X/Twitter, Facebook, Instagram, LinkedIn, TikTok as indexed by Google Search |

> **Note:** Social platform content is retrieved via Google Search indexing, not direct platform APIs.

### Agent Profile Generation
Graph entities are converted into structured OASIS agent profiles with persona, bio, MBTI, profession, interests, and platform-specific attributes (follower count, karma, etc.). The generator distinguishes individuals from abstract entities and assigns stance-aware behavioral parameters aligned to the scenario objective.

### Source-Cited Reports
The Report Agent uses a **ReACT-style loop** over Zep graph tools, web intelligence, and simulation output. Every prediction is backed by inline citations:

> _"Consumer sentiment toward EV adoption has shifted positively `[1][2]`, though supply chain risks remain elevated `[3]`."_

Each section receives a confidence level (HIGH / MEDIUM / LOW) based on citation density and evidence quality. A full references section with numbered URLs is appended.

### Multi-AI Consensus Validation
Up to 3 independent LLM validators score predictions on logical coherence, historical precedent, completeness, and risk factors:

```
Primary (Gemini 2.5 Pro)  Validator 2 (GPT-4o-mini)  Validator 3 (Gemini 2.0 Flash)
     │                      │                        │
     └──────────────────────┴────────────────────────┘
                            ▼
                   Consensus Engine
             ┌─────────────────────────┐
             │  full_consensus         │
             │  majority               │
             │  split                  │
             │  dissent                │
             └─────────────────────────┘
```

Validation is additive — it never modifies OASIS or CAMEL internals.

---

## Security

| Layer | Implementation |
|---|---|
| **Input validation** | Strict regex on all ID parameters (`^proj_[a-f0-9]{12}$`, etc.) at API and filesystem boundary |
| **Path traversal** | Double-check regex validation in `ProjectManager` and `SimulationManager` |
| **XSS protection** | All markdown rendering passes through DOMPurify before DOM insertion |
| **Concurrent state** | Per-entity `threading.Lock` with atomic writes (`tempfile.mkstemp` → `os.replace`) |
| **Error isolation** | Global Flask error handlers — internal tracebacks logged server-side only, never exposed |
| **Request tracing** | Every request receives a unique `X-Request-ID` propagated through response headers |
| **Debug mode** | `FLASK_DEBUG` defaults to `False` — Werkzeug debugger never exposed in production |

For security vulnerabilities, contact **info@inbharat.ai** — do not open public issues.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (20 LTS recommended)
- API keys: `LLM_API_KEY`, `ZEP_API_KEY` (required); `SERPER_API_KEY`, `NEWS_API_KEY` (recommended)

### 1. Install dependencies

```bash
# Frontend
cd frontend && npm install && cd ..

# Backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # macOS/Linux
.venv\Scripts\pip install -r requirements.txt     # Windows
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys (any OpenAI SDK-compatible provider — live deploy uses Google Gemini 2.5 Pro):
```env
LLM_API_KEY=your_gemini_api_key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL_NAME=gemini-2.5-pro
ZEP_API_KEY=your_zep_api_key
```

Optional (recommended):
```env
SERPER_API_KEY=your_serper_key          # Web intelligence
NEWS_API_KEY=your_newsapi_key           # News enrichment
SIMULATION_SPEED_MODE=normal            # normal | fast | express
ENABLE_GEOPOLITICAL_EVENTS=true         # Inject real-time geopolitical events
```

Optional (multi-AI consensus — live deploy uses OpenAI as Validator 2 for family diversity):
```env
LLM_VALIDATOR_2_API_KEY=your_openai_api_key
LLM_VALIDATOR_2_BASE_URL=https://api.openai.com/v1
LLM_VALIDATOR_2_MODEL_NAME=gpt-4o-mini

LLM_VALIDATOR_3_API_KEY=your_gemini_key
LLM_VALIDATOR_3_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_VALIDATOR_3_MODEL_NAME=gemini-2.0-flash
```

### 3. Run

```bash
# Backend (http://localhost:5001)
python run.py

# Frontend (http://localhost:3000)
cd frontend && npm run dev
```

### 4. Docker (single command)

```bash
docker compose up -d
# → http://localhost:3000 (frontend)
# → http://localhost:5001 (backend)
```

> **Google Cloud deployment (production):**
> - **GKE Autopilot (primary):** [`deploy/gke/README.md`](deploy/gke/README.md) — Cloud Build → Artifact Registry → GKE with Workload Identity.
> - **Compute Engine (secondary):** [`deploy/gce/README.md`](deploy/gce/README.md) — one-command VM + 100 GB persistent disk + Caddy HTTPS.

### 5. Verify

```bash
curl http://localhost:5001/health
# → {"status":"ok","checks":{...}}
```

---

## API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service health with dependency status |
| `POST` | `/api/graph/ontology/generate` | Generate ontology from uploaded documents |
| `POST` | `/api/graph/build` | Build knowledge graph in Zep |
| `GET` | `/api/graph/project/<id>` | Retrieve project state |
| `GET` | `/api/graph/data/<graph_id>` | Retrieve graph data for visualization |
| `DELETE` | `/api/graph/project/<id>` | Delete project and associated data |
| `GET` | `/api/simulation/entities/<graph_id>` | List entities in a graph |
| `POST` | `/api/simulation/prepare` | Generate profiles + simulation config |
| `POST` | `/api/simulation/start` | Launch OASIS simulation subprocess |
| `GET` | `/api/simulation/<id>/run-status` | Lightweight progress polling |
| `GET` | `/api/simulation/<id>/run-status/detail` | Full status + recent actions |
| `POST` | `/api/simulation/stop` | Stop a running simulation |
| `POST` | `/api/report/generate` | Start source-cited report generation |
| `GET` | `/api/report/<id>` | Retrieve completed report |
| `GET` | `/api/report/<id>/download` | Download report as Markdown |
| `POST` | `/api/report/chat` | Interactive Q&A with Report Agent |
| `GET` | `/api/report/<id>/progress` | Real-time generation progress |
| `GET` | `/api/report/validators` | List configured AI validators |

All ID parameters are validated against strict regex patterns — malformed IDs return `400`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Vue 3 + Vite + Pinia |
| **Backend** | Flask (Python 3.11+) |
| **Simulation** | OASIS 0.2.5 + CAMEL-AI 0.2.78 |
| **Knowledge Graph** | Zep Cloud 3.13.0 |
| **Web Intelligence** | Serper API + Event Registry |
| **LLM** | Any OpenAI SDK-compatible provider · live: Gemini 2.5 Pro (primary) + GPT-4o-mini & Gemini 2.0 Flash (consensus) |
| **Deployment** | Docker (multi-stage build) · Google Kubernetes Engine (Autopilot) · Google Cloud Compute Engine · Cloud Build + Artifact Registry |
| **Data layer** | Google Cloud Storage (artifact mirror) · BigQuery (telemetry) |
| **CI** | GitHub Actions builds & pushes Docker image to GHCR on tag push · Cloud Build → Artifact Registry for GKE |

---

## Project Status

Phoring is actively developed. Current limitations:

| Area | State |
|---|---|
| **Storage** | Local filesystem (primary) mirrored to Google Cloud Storage; no relational DB backend |
| **Telemetry** | BigQuery append-only logging of runs, agent events, report evaluations, and Q&A (config-gated) |
| **Authentication** | None — suitable for local or trusted-network use |
| **Social content** | Via Google Search indexing, not direct platform APIs |
| **Scalability** | GKE-hosted (Autopilot, HPA-scaled); Flask is single-process per pod |

---

## Roadmap

- [x] Stage-level observability and runtime telemetry → BigQuery (`simulation_runs`, `agent_events`)
- [x] Durable artifact storage → Cloud Storage mirror of uploads + reports
- [x] Containerized hosting on managed Kubernetes → GKE Autopilot
- [ ] Persistent relational database backend (replace JSON file storage)
- [ ] Authentication and authorization layer
- [ ] Objective benchmark suite for simulation quality scoring
- [ ] Replay and post-run analysis interface (over BigQuery telemetry)
- [ ] Plugin system for custom intelligence sources
- [ ] Real-time collaborative sessions

---

## Repository Structure

```
backend/
  app/
    __init__.py              Flask factory, error handlers, SPA serving
    config.py                Environment config, speed modes, validation
    api/
      graph.py               Graph / ontology / project endpoints
      simulation.py          Simulation lifecycle endpoints
      report.py              Report generation, chat, streaming
    services/
      graph_builder.py       Zep graph construction
      ontology_generator.py  Ontology extraction via LLM
      oasis_profile_generator.py  Agent profile generation
      simulation_config_generator.py  Geopolitical-aware config generation
      simulation_runner.py   OASIS subprocess manager + auto-restart
      simulation_manager.py  State management with atomic writes
      web_intelligence.py    Serper + Event Registry scraping
      report_agent.py        ReACT-style report generation
      consensus_validator.py Multi-AI cross-validation engine
      zep_entity_reader.py   Graph entity extraction
      zep_tools.py           Graph search tools for Report Agent
    utils/
      validators.py          Strict ID regex validation
      file_parser.py         PDF / MD / TXT parsing
      llm_client.py          LLM client wrapper
      gcp_clients.py         BigQuery telemetry + Cloud Storage mirror (config-gated)
  scripts/
    run_parallel_simulation.py   OASIS parallel runner (Twitter + Reddit)

frontend/
  src/
    components/
      Step1GraphBuild.vue    Document upload + graph construction
      Step2EnvSetup.vue      LLM + simulation configuration
      Step3Simulation.vue    Real-time simulation monitor
      Step4Report.vue        Source-cited report viewer
      Step5Interaction.vue   Post-report Q&A interface
      GraphPanel.vue         Knowledge graph visualization
```

---

## Acknowledgments

- [OASIS](https://github.com/camel-ai/oasis) — Multi-agent social simulation framework
- [CAMEL-AI](https://github.com/camel-ai) — Communicative agent framework
- [Zep](https://www.getzep.com/) — Knowledge graph memory service

---

## Author

**Reeturaj Goswami** — Creator & Lead Developer
- Email: info@inbharat.ai
- GitHub: [@inbharatai](https://github.com/inbharatai)

---

## License

[MIT License](./LICENSE)

---

<div align="center">

**Built by [Reeturaj Goswami](https://github.com/inbharatai)** · [Live Demo](https://phoring.in) · info@inbharat.ai

</div>
