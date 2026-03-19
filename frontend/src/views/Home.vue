<template>
  <div class="home-shell">
    <div class="ambient ambient-a"></div>
    <div class="ambient ambient-b"></div>

    <header class="topbar">
      <div class="brand">
        <img src="../assets/logo/phoring_logo.png" alt="Phoring" class="brand-logo" />
        <span class="brand-text">PHORING</span>
      </div>
      <a class="repo-link" href="https://github.com/inbharatai/phoring" target="_blank" rel="noopener noreferrer">
        Repository
      </a>
    </header>

    <main class="main-grid">
      <section class="hero-card panel reveal-1">
        <div class="hero-copy">
          <p class="eyebrow">Open-Source Decision Intelligence</p>
          <h1>From documents to simulation-backed forecasts.</h1>
          <p class="subtitle">
            Upload source documents, define a scenario, and let Phoring build a knowledge graph,
            enrich it with web context, run a multi-agent social simulation via OASIS,
            and generate a structured report with inline source citations.
          </p>
          <div class="hero-badges">
            <span>Source-Cited Reports</span>
            <span>Knowledge Graph</span>
            <span>Confidence Scoring</span>
            <span>OASIS Simulation</span>
            <span>Early Stage</span>
          </div>
        </div>
        <div class="hero-logo-wrap">
          <img src="../assets/logo/phoring_logo.png" alt="Phoring Logo" class="hero-logo" />
        </div>
      </section>

      <section class="pipeline-card panel reveal-2">
        <h2>How It Works</h2>
        <div class="pipeline-list">
          <article>
            <span>01</span>
            <div>
              <h3>Graph Build</h3>
              <p>Upload documents (PDF, MD, TXT). Phoring extracts entities, maps relationships, and builds a knowledge graph in Zep.</p>
            </div>
          </article>
          <article>
            <span>02</span>
            <div>
              <h3>Agent Setup</h3>
              <p>LLM-generated agent profiles are created from graph entities — each with persona, stance, and platform-specific attributes.</p>
            </div>
          </article>
          <article>
            <span>03</span>
            <div>
              <h3>Simulation</h3>
              <p>OASIS runs a synthetic multi-agent simulation across simulated Twitter and Reddit environments, enriched with web-sourced context.</p>
            </div>
          </article>
          <article>
            <span>04</span>
            <div>
              <h3>Report</h3>
              <p>A structured, source-cited report with confidence scoring and optional multi-model consensus validation.</p>
            </div>
          </article>
        </div>
      </section>

      <section class="features-card panel reveal-3">
        <div class="fc-header">
          <p class="eyebrow">What Powers the Output</p>
          <h2>Core Capabilities</h2>
          <p class="fc-sub">Each stage of the pipeline is a discrete, inspectable step — from document parsing and knowledge graph construction, through web context enrichment, to multi-agent simulation and report generation with inline citations.</p>
        </div>

        <!-- Animated pipeline flow -->
        <div class="pf-flow" aria-hidden="true">
          <div class="pf-node">
            <div class="pf-circle">01</div>
            <span class="pf-lbl">Doc + Prompt</span>
          </div>
          <div class="pf-rail"><div class="pf-bead"></div></div>
          <div class="pf-node">
            <div class="pf-circle">02</div>
            <span class="pf-lbl">Entity Extract</span>
          </div>
          <div class="pf-rail"><div class="pf-bead" style="--delay:0.5s"></div></div>
          <div class="pf-node">
            <div class="pf-circle">03</div>
            <span class="pf-lbl">Web &amp; News</span>
          </div>
          <div class="pf-rail"><div class="pf-bead" style="--delay:1s"></div></div>
          <div class="pf-node">
            <div class="pf-circle">04</div>
            <span class="pf-lbl">Web Context</span>
          </div>
          <div class="pf-rail"><div class="pf-bead" style="--delay:1.5s"></div></div>
          <div class="pf-node">
            <div class="pf-circle">05</div>
            <span class="pf-lbl">Agent Graph</span>
          </div>
          <div class="pf-rail"><div class="pf-bead" style="--delay:2s"></div></div>
          <div class="pf-node">
            <div class="pf-circle">06</div>
            <span class="pf-lbl">Simulation</span>
          </div>
          <div class="pf-rail"><div class="pf-bead" style="--delay:2.5s"></div></div>
          <div class="pf-node pf-node--out">
            <div class="pf-circle">07</div>
            <span class="pf-lbl">Forecast</span>
          </div>
        </div>

        <div class="feature-grid">
          <article>
            <div class="fg-icon-row">
              <span class="fg-tag">GRAPH</span>
              <h3>Knowledge Graph Construction</h3>
            </div>
            <p>Documents are parsed, chunked, and processed by an LLM-driven ontology generator. Entities, relationships, and domain concepts are stored as a graph in Zep Cloud — used downstream for agent profiles, simulation context, and report Q&amp;A.</p>
          </article>
          <article>
            <div class="fg-icon-row">
              <span class="fg-tag">SEARCH</span>
              <h3>Web &amp; News Enrichment</h3>
            </div>
            <p>Entity-scoped queries via Serper and NewsAPI retrieve relevant articles (scraped up to 4,000 chars each). Social platform content is sourced via Google Search indexing — not direct API access. Coverage depends on what Google has indexed.</p>
          </article>
          <article>
            <div class="fg-icon-row">
              <span class="fg-tag">SIM</span>
              <h3>Multi-Agent Simulation</h3>
            </div>
            <p>OASIS spawns synthetic Twitter and Reddit environments where LLM-generated agents interact based on their assigned personas, stances, and behavioral parameters. Actions and round summaries are streamed back in real time.</p>
          </article>
          <article>
            <div class="fg-icon-row">
              <span class="fg-tag">CITE</span>
              <h3>Source-Cited Reports</h3>
            </div>
            <p>The Report Agent generates structured output in a ReACT loop, pulling from the knowledge graph, web intelligence, and simulation results. Claims are backed by inline numbered references [1][2][3] with a full sources section.</p>
          </article>
          <article>
            <div class="fg-icon-row">
              <span class="fg-tag">SCORE</span>
              <h3>Confidence Scoring</h3>
            </div>
            <p>Each report section is tagged [HIGH], [MEDIUM], or [LOW] based on how many independent tool-sourced data points support it. This reflects evidence density — not a guarantee of factual accuracy.</p>
          </article>
          <article>
            <div class="fg-icon-row">
              <span class="fg-tag">VERIFY</span>
              <h3>Multi-Model Consensus (Optional)</h3>
            </div>
            <p>When configured, up to 3 independent LLM validators score predictions on coherence, precedent, and risk. A consensus summary is appended to the report. Requires additional API keys (e.g. Claude, Gemini).</p>
          </article>
        </div>

        <div class="tech-stack-row">
          <span class="ts-label">Built on</span>
          <a class="ts-chip" href="https://github.com/camel-ai/oasis" target="_blank" rel="noopener noreferrer">OASIS</a>
          <span class="ts-sep">·</span>
          <a class="ts-chip" href="https://github.com/camel-ai/camel" target="_blank" rel="noopener noreferrer">CAMEL AI</a>
          <span class="ts-sep">·</span>
          <span class="ts-chip ts-plain">Zep Knowledge Graph</span>
          <span class="ts-sep">·</span>
          <span class="ts-chip ts-plain">Serper</span>
          <span class="ts-sep">·</span>
          <span class="ts-chip ts-plain">NewsAPI</span>
          <span class="ts-sep">·</span>
          <span class="ts-chip ts-plain">OpenAI</span>
        </div>
      </section>

      <section class="status-card panel reveal-4">
        <div class="status-header">
          <p class="eyebrow">Transparency</p>
          <h2>Current Status</h2>
        </div>
        <div class="status-grid">
          <div class="status-col">
            <h3>What works today</h3>
            <ul>
              <li>Document-to-knowledge-graph pipeline (Zep Cloud)</li>
              <li>LLM-driven ontology extraction and agent profile generation</li>
              <li>OASIS multi-agent simulation (synthetic Twitter + Reddit)</li>
              <li>Web enrichment via Serper and NewsAPI</li>
              <li>Source-cited report generation with confidence tags</li>
              <li>Interactive post-report Q&amp;A</li>
              <li>Input validation, XSS protection, atomic file writes</li>
            </ul>
          </div>
          <div class="status-col">
            <h3>Known limitations</h3>
            <ul>
              <li>Flat JSON file storage — no database backend yet</li>
              <li>No authentication — local or trusted-network use only</li>
              <li>Social content sourced via Google Search indexing, not platform APIs</li>
              <li>Single-process Flask — not designed for high concurrency</li>
              <li>Confidence scores reflect evidence density, not factual accuracy</li>
              <li>Multi-model consensus requires manually configured API keys</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="workbench panel reveal-5">
        <div class="workbench-head">
          <h2>New Simulation</h2>
          <p>Upload source documents and describe your scenario to begin.</p>
        </div>

        <div
          class="dropzone"
          :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleDrop"
          @click="triggerFileInput"
        >
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".pdf,.md,.txt"
            @change="handleFileSelect"
            style="display: none"
            :disabled="loading"
          />

          <div v-if="files.length === 0" class="dropzone-empty">
            <strong>Drop files here or click to browse</strong>
            <small>Accepted: PDF, MD, TXT</small>
          </div>

          <div v-else class="file-list">
            <div v-for="(file, index) in files" :key="index" class="file-item">
              <span class="file-name">{{ file.name }}</span>
              <button class="remove-btn" @click.stop="removeFile(index)">Remove</button>
            </div>
          </div>
        </div>

        <label class="input-label" for="scenario-input">Scenario Prompt</label>
        <textarea
          id="scenario-input"
          v-model="formData.simulationRequirement"
          class="scenario-input"
          placeholder="Example: Simulate the public reaction to a university policy announcement over 72 hours."
          rows="6"
          :disabled="loading"
        ></textarea>

        <!-- Inline validation errors -->
        <div v-if="validationErrors.length" class="validation-errors">
          <p v-for="err in validationErrors" :key="err" class="validation-error">⚠ {{ err }}</p>
        </div>

        <button class="launch-btn" @click="startSimulation" :disabled="!canSubmit || loading">
          <span v-if="loading">Initializing...</span>
          <span v-else>Start Simulation</span>
        </button>
      </section>
    </main>

    <section class="history-wrap reveal-6">
      <HistoryDatabase />
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import { useAppStore } from '../stores/app'

const router = useRouter()
const store = useAppStore()

const MAX_FILE_SIZE_MB = 50
const WARN_FILE_SIZE_MB = 10
const MIN_REQUIREMENT_LENGTH = 20

const formData = ref({
  simulationRequirement: ''
})

const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

const validationErrors = computed(() => {
  const errors = []
  const req = formData.value.simulationRequirement.trim()
  if (req.length > 0 && req.length < MIN_REQUIREMENT_LENGTH) {
    errors.push(`Scenario prompt is too short — please describe your prediction scenario in at least ${MIN_REQUIREMENT_LENGTH} characters.`)
  }
  for (const f of files.value) {
    const mb = f.size / (1024 * 1024)
    if (mb > MAX_FILE_SIZE_MB) {
      errors.push(`"${f.name}" exceeds the ${MAX_FILE_SIZE_MB} MB limit and will be rejected.`)
    }
  }
  return errors
})

const canSubmit = computed(() => {
  const req = formData.value.simulationRequirement.trim()
  if (req.length < MIN_REQUIREMENT_LENGTH) return false
  if (files.value.length === 0) return false
  if (files.value.some(f => f.size / (1024 * 1024) > MAX_FILE_SIZE_MB)) return false
  return true
})

const triggerFileInput = () => {
  if (!loading.value) fileInput.value?.click()
}

const handleFileSelect = (event) => {
  addFiles(Array.from(event.target.files))
}

const handleDragOver = () => {
  if (!loading.value) isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (event) => {
  isDragOver.value = false
  if (loading.value) return
  addFiles(Array.from(event.dataTransfer.files))
}

const addFiles = (newFiles) => {
  const accepted = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'md', 'txt'].includes(ext)) {
      store.toast.warn(`"${file.name}" is not a supported file type (PDF, MD, TXT).`)
      return false
    }
    const mb = file.size / (1024 * 1024)
    if (mb > MAX_FILE_SIZE_MB) {
      store.toast.error(`"${file.name}" (${mb.toFixed(1)} MB) exceeds the ${MAX_FILE_SIZE_MB} MB limit.`)
      return false
    }
    if (mb > WARN_FILE_SIZE_MB) {
      store.toast.warn(`"${file.name}" is ${mb.toFixed(1)} MB — large files may take longer to process.`)
    }
    return true
  })
  files.value.push(...accepted)
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  store.setPending(files.value, formData.value.simulationRequirement)
  router.push({ name: 'Process', params: { projectId: 'new' } })
}
</script>

<style scoped>
:root {
  --paper: #f6f2ea;
  --ink: #10141f;
  --coral: #db5d3b;
  --teal: #0d6f70;
  --line: #d6cec1;
  --panel: rgba(255, 255, 255, 0.68);
  --shadow: 0 16px 40px rgba(16, 20, 31, 0.08);
  --display: 'Space Grotesk', 'Noto Sans SC', sans-serif;
  --mono: 'JetBrains Mono', 'Noto Sans SC', monospace;
}

.home-shell {
  min-height: 100vh;
  background: radial-gradient(circle at 12% 18%, #f9e4d9 0%, transparent 45%),
    radial-gradient(circle at 80% 2%, #dceced 0%, transparent 35%),
    var(--paper);
  color: var(--ink);
  padding: 26px clamp(16px, 3vw, 40px) 48px;
  position: relative;
  overflow-x: hidden;
}

.ambient {
  position: absolute;
  pointer-events: none;
  z-index: 0;
}

.ambient-a {
  width: 220px;
  height: 220px;
  border: 1px solid rgba(13, 111, 112, 0.2);
  border-radius: 36% 64% 70% 30% / 38% 31% 69% 62%;
  top: 64px;
  right: 6%;
  animation: float 10s ease-in-out infinite;
}

.ambient-b {
  width: 170px;
  height: 170px;
  border: 1px solid rgba(219, 93, 59, 0.22);
  border-radius: 70% 30% 37% 63% / 41% 59% 41% 59%;
  bottom: 100px;
  left: 4%;
  animation: float 12s ease-in-out infinite reverse;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-12px) rotate(4deg);
  }
}

.topbar,
.main-grid,
.history-wrap {
  position: relative;
  z-index: 1;
}

.topbar {
  max-width: 1320px;
  margin: 0 auto 26px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
}

.brand-text {
  font-family: var(--mono);
  font-size: 0.92rem;
  letter-spacing: 0.14em;
  font-weight: 700;
}

.repo-link {
  color: var(--ink);
  text-decoration: none;
  font-family: var(--mono);
  font-size: 0.8rem;
  border: 1px solid var(--line);
  padding: 8px 12px;
  transition: all 0.2s ease;
}

.repo-link:hover {
  border-color: var(--teal);
  color: var(--teal);
}

.main-grid {
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 20px;
}

.panel {
  background: var(--panel);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: var(--shadow);
}

.hero-card {
  grid-column: 1 / 2;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 18px;
  border-radius: 24px;
  padding: clamp(24px, 2.4vw, 34px);
}

.eyebrow {
  font-family: var(--mono);
  font-size: 0.75rem;
  letter-spacing: 0.14em;
  color: var(--teal);
  text-transform: uppercase;
  margin-bottom: 10px;
}

.hero-card h1 {
  font-family: var(--display);
  font-size: clamp(1.8rem, 3vw, 3rem);
  line-height: 1.07;
  letter-spacing: -0.02em;
  margin-bottom: 16px;
}

.subtitle {
  color: rgba(16, 20, 31, 0.76);
  line-height: 1.6;
  max-width: 62ch;
}

.hero-badges {
  margin-top: 18px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.hero-badges span {
  border: 1px solid var(--line);
  padding: 6px 10px;
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
}

.hero-logo-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-logo {
  width: min(100%, 320px);
  object-fit: contain;
}

.pipeline-card {
  grid-column: 2 / 3;
  border-radius: 24px;
  padding: 22px;
}

.features-card {
  grid-column: 1 / 3;
  border-radius: 24px;
  padding: 28px;
  position: relative;
  overflow: hidden;
  background: var(--panel);
}

.pipeline-card h2,
.workbench h2,
.features-card h2 {
  font-family: var(--display);
  font-size: 1.2rem;
  letter-spacing: -0.01em;
  margin-bottom: 6px;
}

.fc-header {
  margin-bottom: 22px;
}

.fc-sub {
  color: rgba(16, 20, 31, 0.7);
  line-height: 1.62;
  max-width: 78ch;
  margin-top: 6px;
  font-size: 0.9rem;
}

/* ── Pipeline flow diagram ───────────────────────── */
.pf-flow {
  display: flex;
  align-items: flex-start;
  margin-bottom: 26px;
  overflow-x: auto;
  padding-bottom: 4px;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.pf-node {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
}

.pf-circle {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  border: 1.5px solid rgba(13, 111, 112, 0.28);
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--teal);
  box-shadow: 0 2px 8px rgba(13, 111, 112, 0.07);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.pf-node:hover .pf-circle {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(13, 111, 112, 0.15);
}

.pf-node--out .pf-circle {
  border-color: var(--coral);
  color: var(--coral);
  background: rgba(219, 93, 59, 0.06);
}

.pf-lbl {
  font-family: var(--mono);
  font-size: 0.59rem;
  letter-spacing: 0.04em;
  color: rgba(16, 20, 31, 0.5);
  white-space: nowrap;
  text-align: center;
}

.pf-rail {
  flex: 1 1 auto;
  min-width: 36px;
  height: 1.5px;
  background: var(--line);
  position: relative;
  align-self: center;
  margin-bottom: 28px;
  overflow: hidden;
  border-radius: 999px;
}

.pf-bead {
  position: absolute;
  top: 50%;
  left: -6px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--teal);
  transform: translateY(-50%);
  animation: beadRun 2.4s ease-in-out infinite;
  animation-delay: var(--delay, 0s);
}

/* ── Feature cards ───────────────────────────────── */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.feature-grid article {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.62);
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
  animation: cardRise 0.5s ease both;
}

.feature-grid article:nth-child(1) { animation-delay: 0.05s; }
.feature-grid article:nth-child(2) { animation-delay: 0.12s; }
.feature-grid article:nth-child(3) { animation-delay: 0.19s; }
.feature-grid article:nth-child(4) { animation-delay: 0.26s; }
.feature-grid article:nth-child(5) { animation-delay: 0.33s; }
.feature-grid article:nth-child(6) { animation-delay: 0.40s; }

.feature-grid article:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(16, 20, 31, 0.09);
  border-color: rgba(13, 111, 112, 0.36);
}

.fg-icon-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.fg-tag {
  font-family: var(--mono);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--teal);
  background: rgba(13, 111, 112, 0.08);
  border: 1px solid rgba(13, 111, 112, 0.18);
  border-radius: 4px;
  padding: 3px 7px;
  flex-shrink: 0;
}

.feature-grid h3 {
  font-size: 0.94rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ink);
}

.feature-grid p {
  font-size: 0.86rem;
  color: rgba(16, 20, 31, 0.67);
  line-height: 1.56;
  margin-top: 5px;
}

/* ── Tech-stack strip ────────────────────────────── */
.tech-stack-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 22px;
  flex-wrap: wrap;
  border-top: 1px solid var(--line);
  padding-top: 18px;
}

.ts-label {
  font-family: var(--mono);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  color: rgba(16, 20, 31, 0.42);
  text-transform: uppercase;
  margin-right: 4px;
}

.ts-chip {
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 4px 10px;
  text-decoration: none;
  transition: border-color 0.2s ease, color 0.2s ease;
}

a.ts-chip:hover {
  border-color: var(--teal);
  color: var(--teal);
}

.ts-sep {
  color: var(--line);
  font-family: var(--mono);
  font-size: 0.9rem;
  line-height: 1;
}

.pipeline-list {
  display: grid;
  gap: 12px;
}

.pipeline-list article {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 10px;
  background: rgba(255, 255, 255, 0.5);
}

.pipeline-list span {
  font-family: var(--mono);
  color: var(--coral);
  font-weight: 700;
}

.pipeline-list h3 {
  font-size: 0.95rem;
  margin-bottom: 4px;
}

.pipeline-list p {
  font-size: 0.88rem;
  color: rgba(16, 20, 31, 0.72);
  line-height: 1.45;
}

.workbench {
  grid-column: 1 / 3;
  border-radius: 24px;
  padding: clamp(20px, 2vw, 30px);
}

.workbench-head p {
  color: rgba(16, 20, 31, 0.76);
  margin-bottom: 16px;
}

.dropzone {
  border: 1px dashed #b8aea1;
  border-radius: 16px;
  min-height: 126px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  margin-bottom: 14px;
  transition: all 0.22s ease;
}

.dropzone.drag-over {
  border-color: var(--teal);
  background: rgba(13, 111, 112, 0.06);
}

.dropzone-empty {
  min-height: 92px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.dropzone-empty strong {
  font-family: var(--display);
  font-size: 1rem;
}

.dropzone-empty small {
  color: rgba(16, 20, 31, 0.66);
  font-family: var(--mono);
}

.file-list {
  display: grid;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  padding: 8px 10px;
}

.file-name {
  font-family: var(--mono);
  font-size: 0.82rem;
}

.remove-btn {
  border: 1px solid var(--line);
  background: #fff;
  padding: 5px 8px;
  border-radius: 8px;
  cursor: pointer;
  font-family: var(--mono);
  font-size: 0.72rem;
}

.input-label {
  display: inline-block;
  margin: 10px 0 8px;
  font-family: var(--mono);
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  color: rgba(16, 20, 31, 0.74);
  text-transform: uppercase;
}

.scenario-input {
  width: 100%;
  border: 1px solid #b8aea1;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.6);
  font-family: var(--mono);
  padding: 14px;
  line-height: 1.55;
  resize: vertical;
  color: var(--ink);
  min-height: 150px;
}

.scenario-input:focus {
  outline: 1px solid var(--teal);
}

.launch-btn {
  margin-top: 14px;
  width: 100%;
  border: none;
  border-radius: 12px;
  padding: 14px 16px;
  background: linear-gradient(92deg, #1f2937 0%, #0d6f70 100%);
  color: #fff;
  font-family: var(--display);
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.launch-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(13, 111, 112, 0.25);
}

.launch-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.validation-errors {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.validation-error {
  font-family: var(--mono);
  font-size: 0.8rem;
  color: #b91c1c;
  background: rgba(185, 28, 28, 0.07);
  border: 1px solid rgba(185, 28, 28, 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  line-height: 1.4;
}

.history-wrap {
  max-width: 1320px;
  margin: 26px auto 0;
}

.reveal-1,
.reveal-2,
.reveal-3,
.reveal-4,
.reveal-5,
.reveal-6 {
  animation: reveal 0.55s ease both;
}

.reveal-2 {
  animation-delay: 0.06s;
}

.reveal-3 {
  animation-delay: 0.12s;
}

.reveal-4 {
  animation-delay: 0.18s;
}

.reveal-5 {
  animation-delay: 0.24s;
}

.reveal-6 {
  animation-delay: 0.30s;
}

@keyframes reveal {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes cardRise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes beadRun {
  0%   { left: -6px;              opacity: 0; }
  8%   { opacity: 1; }
  92%  { opacity: 1; }
  100% { left: calc(100% + 6px); opacity: 0; }
}

/* ── Status / transparency section ────────────────── */
.status-card {
  grid-column: 1 / 3;
  border-radius: 24px;
  padding: 28px;
}

.status-header {
  margin-bottom: 18px;
}

.status-header h2 {
  font-family: var(--display);
  font-size: 1.2rem;
  letter-spacing: -0.01em;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.status-col h3 {
  font-size: 0.88rem;
  font-weight: 700;
  margin-bottom: 10px;
  color: var(--ink);
}

.status-col ul {
  list-style: none;
  display: grid;
  gap: 8px;
}

.status-col ul li {
  font-size: 0.84rem;
  color: rgba(16, 20, 31, 0.72);
  line-height: 1.5;
  padding-left: 14px;
  position: relative;
}

.status-col ul li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--teal);
}

.status-col:last-child ul li::before {
  background: var(--coral);
}

@media (max-width: 980px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .hero-card,
  .pipeline-card,
  .features-card,
  .status-card,
  .workbench {
    grid-column: 1 / 2;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }

  .feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .pf-flow {
    gap: 0;
  }

  .hero-card {
    grid-template-columns: 1fr;
  }

  .hero-logo-wrap {
    justify-content: flex-start;
  }

  .hero-logo {
    width: min(100%, 260px);
  }
}

@media (max-width: 640px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }

  .hero-badges {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
