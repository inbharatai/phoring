<template>
  <div ref="wrapRef" class="pipeline-3d-wrap">
    <canvas ref="canvasRef" class="pipeline-canvas"></canvas>
    <div v-if="hoveredNode" class="node-tooltip" :style="tooltipStyle">
      <div class="tooltip-tag">{{ hoveredNode.tag }}</div>
      <strong>{{ hoveredNode.label }}</strong>
      <p>{{ hoveredNode.desc }}</p>
      <div v-if="hoveredNode.detail" class="tooltip-detail">{{ hoveredNode.detail }}</div>
    </div>
    <div class="graph-hint">Drag to rotate &middot; Scroll to zoom &middot; Hover nodes for details</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

/*
 * REAL ARCHITECTURE GRAPH — branching & merging topology
 *
 * Layer 0 (INPUT):      Documents + Scenario
 * Layer 1 (PROCESS):    Text Processor ─┬─ Ontology Generator
 *                                       └─ Web Intelligence ──┬─ Serper API
 *                                                             ├─ Event Registry
 *                                                             └─ Social Scraping
 * Layer 2 (GRAPH):      Zep Knowledge Graph (central hub)
 * Layer 3 (AGENTS):     OASIS Profile Gen ─┬─ Persona LLM
 *                                          └─ Zep Entity Search
 * Layer 4 (SIMULATION): SimRunner ─┬─ Twitter Env (parallel)
 *                                  ├─ Reddit Env  (parallel)
 *                                  └─ Zep Memory Updater (live writeback)
 * Layer 5 (REPORT):     Report Agent ─┬─ Insight Forge (Zep deep)
 *                                     ├─ Panorama Search
 *                                     ├─ Agent Interviews (IPC)
 *                                     └─ Web Context (fresh)
 * Layer 6 (VALIDATE):   Consensus ─┬─ AI Validator 1 (Primary)
 *                                  ├─ AI Validator 2 (Claude)
 *                                  └─ AI Validator 3 (Gemini)
 * Layer 7 (OUTPUT):     Source-Cited Forecast
 */

/* ── Node definitions — the REAL branching architecture ─── */
const NODES = [
  // LAYER 0 — Input
  { id: 'docs',       label: 'Documents',          tag: 'INPUT',       desc: 'PDF, MD, TXT uploads + scenario prompt',                                  detail: 'Max 50MB per file · Accepts PDF, Markdown, plaintext',            color: 0x6b7280, pos: [-8,  3.5,  0],    shape: 'box'      },

  // LAYER 1 — Processing (branches out)
  { id: 'textproc',   label: 'Text Processor',      tag: 'PARSE',       desc: 'Document parsing, chunking (500 char windows, 50 overlap)',               detail: 'Chunks batched for Zep ingestion · 50K char max',                 color: 0x0d6f70, pos: [-5,  3.5,  1.2],  shape: 'sphere'   },
  { id: 'ontology',   label: 'Ontology Generator',  tag: 'LLM',        desc: 'LLM extracts 10 entity types + 6-10 edge types from documents',           detail: 'Person, Organization, Company, University... · temp=0.3',         color: 0x0d8f90, pos: [-5,  1.5,  -0.5], shape: 'octahedron' },

  // LAYER 1b — Web Intelligence (3 parallel sources)
  { id: 'webintel',   label: 'Web Intelligence',    tag: 'SEARCH',      desc: 'Entity-scoped multi-source enrichment engine',                            detail: 'Queries built from key phrases, capitalized entities, domain markers', color: 0x2a9d8f, pos: [-5,  5.5,  -1],  shape: 'sphere'   },
  { id: 'serper',     label: 'Serper API',           tag: 'NEWS',        desc: 'Google News search — Reuters, Bloomberg, FT, BBC, Guardian',              detail: '≤5 results · Financial vs Global source routing · 7-day recency', color: 0x3b82f6, pos: [-3,  6.5,  -2],  shape: 'diamond'  },
  { id: 'eventReg',   label: 'Event Registry',       tag: 'NEWS',        desc: 'newsapi.ai fallback — 300K+ global sources',                             detail: 'Triggers when Serper returns <3 results · Domain-filtered',       color: 0x8b5cf6, pos: [-3,  5.0,  -3],  shape: 'diamond'  },
  { id: 'scraper',    label: 'Social Scraping',      tag: 'SCRAPE',      desc: 'Reddit, Twitter/X, Facebook, LinkedIn, TikTok via Google indexing',       detail: 'BeautifulSoup · domain-specific CSS selectors · 4K chars/article', color: 0xec4899, pos: [-3,  4.0,  -1.5], shape: 'diamond'  },

  // LAYER 2 — Central Hub
  { id: 'zepgraph',   label: 'Zep Knowledge Graph',  tag: 'GRAPH',       desc: 'Central graph DB — entities, edges, communities, episodes',              detail: 'Batch ingestion · Episode polling · Community detection · Live updates from sim', color: 0x10b981, pos: [-0.5, 3.5,  0],  shape: 'icosahedron' },

  // LAYER 3 — Agent Generation (branches from graph)
  { id: 'profgen',    label: 'Profile Generator',    tag: 'AGENTS',      desc: 'Per-entity: Zep search + web intel + LLM persona generation',            detail: 'MBTI, age, gender, country, profession, interested_topics · Twitter & Reddit formats', color: 0xf59e0b, pos: [2.5, 5,   1],    shape: 'sphere'   },
  { id: 'simconfig',  label: 'Simulation Config',    tag: 'CONFIG',      desc: 'Time config, event scheduling, agent calibration, platform tuning',       detail: '4 calibration modes: realism / aggressive / fast / express',      color: 0xf59e0b, pos: [2.5, 2,   1],    shape: 'sphere'   },

  // LAYER 4 — Simulation (parallel split)
  { id: 'simrunner',  label: 'OASIS SimRunner',      tag: 'ENGINE',      desc: 'Subprocess manager — launches parallel platform simulations',             detail: 'Auto-restart on crash · Orphan recovery · run_params.json persistence', color: 0xe76f51, pos: [5,   3.5,  0],   shape: 'sphere'   },
  { id: 'twitter',    label: 'Twitter Environment',   tag: 'PLATFORM',    desc: 'Synthetic Twitter: posts, likes, reposts, quotes, follows, mutes',       detail: 'recency=0.4 · popularity=0.3 · viral_threshold=10 · echo_chamber=0.5', color: 0x1da1f2, pos: [7.5, 5,    1.5], shape: 'box'      },
  { id: 'reddit',     label: 'Reddit Environment',    tag: 'PLATFORM',    desc: 'Synthetic Reddit: posts, comments, upvotes, karma, subreddits',          detail: 'recency=0.3 · popularity=0.4 · viral_threshold=15 · echo_chamber=0.6', color: 0xff4500, pos: [7.5, 2,    1.5], shape: 'box'      },
  { id: 'zepmemory',  label: 'Zep Memory Updater',    tag: 'WRITEBACK',   desc: 'Live graph writeback — agent actions batched into Zep episodes',          detail: 'Buffer per platform · batch=5 · retry 3x · 0.5s rate limit',     color: 0x10b981, pos: [7.5, 3.5, -1.5], shape: 'octahedron' },

  // LAYER 4b — Geopolitical events inject into simulation
  { id: 'geoevents',  label: 'Geopolitical Events',   tag: 'DISRUPTION',  desc: '14 event categories injected mid-simulation',                            detail: 'natural_disaster, armed_conflict, trade_war, sanctions, election_upheaval...', color: 0xef4444, pos: [5,   5.5, -2],   shape: 'octahedron' },

  // LAYER 5 — Report (merges multiple inputs)
  { id: 'reportagent',label: 'Report Agent',          tag: 'REACT',       desc: 'ReACT loop: Thought → Tool Call → Answer, max 10 iterations/section',    detail: 'Planning phase → per-section generation with 4 tool types',       color: 0xdb5d3b, pos: [10.5, 3.5, 0],   shape: 'sphere'   },
  { id: 'insightforge',label:'Insight Forge',         tag: 'TOOL',        desc: 'Deep multi-step analysis — decomposes into sub-questions',                detail: 'Zep graph deep retrieval + entity analysis + relation analysis',  color: 0xa855f7, pos: [12,  5.5,  1.5], shape: 'diamond'  },
  { id: 'panorama',   label: 'Panorama Search',       tag: 'TOOL',        desc: 'Full simulation relationship view + historical state evolution',          detail: 'Entity relationships, changes over time, state snapshots',        color: 0xa855f7, pos: [12,  4,    2.5], shape: 'diamond'  },
  { id: 'interviews', label: 'Agent Interviews',      tag: 'TOOL',        desc: 'Real-time IPC to running OASIS agents — not LLM-simulated',              detail: 'Batch interviews across Twitter + Reddit simultaneously',         color: 0xa855f7, pos: [12,  2.5,  1.5], shape: 'diamond'  },
  { id: 'freshweb',   label: 'Fresh Web Context',     tag: 'TOOL',        desc: 'Live news retrieval at report time for fact-grounding',                   detail: 'Same Serper + Event Registry pipeline, ≤6000 chars',             color: 0xa855f7, pos: [12,  1.5,  0],   shape: 'diamond'  },

  // LAYER 6 — Consensus Validation (hub-and-spoke: validators orbit the engine)
  { id: 'consensus',  label: 'Consensus Engine',      tag: 'VALIDATE',    desc: 'Extracts 3-7 predictions, gathers fresh web context, dispatches to multi-AI validators, consolidates scores', detail: 'Levels: unanimous → majority → split → dissent · Confidence 0-1 · One-way append to report', color: 0xfbbf24, pos: [15,  3.5, -0.5], shape: 'icosahedron' },
  { id: 'ai1',        label: 'Primary AI',             tag: 'VALIDATOR',   desc: 'OpenAI GPT-4o-mini — always present, primary scorer',                    detail: 'agreement + confidence_score + reasoning + risk_factors → returns to engine', color: 0x22c55e, pos: [15,  5.8,  0.5], shape: 'cone'     },
  { id: 'ai2',        label: 'Claude (Validator 2)',   tag: 'VALIDATOR',   desc: 'Anthropic Claude — optional cross-model verification',                   detail: 'Independent scoring: coherence, precedent, completeness → returns to engine', color: 0xf97316, pos: [16.8, 3.5, -1.8], shape: 'cone'    },
  { id: 'ai3',        label: 'Gemini (Validator 3)',   tag: 'VALIDATOR',   desc: 'Google Gemini — optional third perspective',                             detail: 'Alternative viewpoints + risk factor identification → returns to engine',     color: 0x06b6d4, pos: [15,  1.2, -1.5], shape: 'cone'     },

  // LAYER 7 — Output
  { id: 'forecast',   label: 'Source-Cited Forecast',  tag: 'OUTPUT',      desc: 'Final report: outline, sections, citations [1][2][3], confidence [HIGH/MED/LOW]', detail: 'Markdown + JSON · Consensus appendix · Interactive Q&A', color: 0xfbbf24, pos: [18.5, 3.5, 0],  shape: 'dodecahedron' },
]

/* ── Edges — the REAL data flow connections ───────── */
const EDGES = [
  // Input → Processing (fan-out)
  { from: 'docs',      to: 'textproc',    color: 0x6b7280 },
  { from: 'docs',      to: 'ontology',    color: 0x6b7280 },
  { from: 'docs',      to: 'webintel',    color: 0x6b7280 },

  // Web Intelligence → 3 parallel sources (fan-out)
  { from: 'webintel',  to: 'serper',      color: 0x3b82f6 },
  { from: 'webintel',  to: 'eventReg',    color: 0x8b5cf6 },
  { from: 'webintel',  to: 'scraper',     color: 0xec4899 },

  // Everything feeds into Zep Graph (fan-in / merge)
  { from: 'textproc',  to: 'zepgraph',    color: 0x0d6f70 },
  { from: 'ontology',  to: 'zepgraph',    color: 0x0d8f90 },
  { from: 'serper',    to: 'zepgraph',    color: 0x3b82f6 },
  { from: 'eventReg',  to: 'zepgraph',    color: 0x8b5cf6 },
  { from: 'scraper',   to: 'zepgraph',    color: 0xec4899 },

  // Graph → Agent Generation (fan-out)
  { from: 'zepgraph',  to: 'profgen',     color: 0x10b981 },
  { from: 'zepgraph',  to: 'simconfig',   color: 0x10b981 },
  { from: 'webintel',  to: 'profgen',     color: 0x2a9d8f },  // web enriches profiles too

  // Agent Gen → Simulation
  { from: 'profgen',   to: 'simrunner',   color: 0xf59e0b },
  { from: 'simconfig', to: 'simrunner',   color: 0xf59e0b },

  // Simulation → parallel platforms (fan-out)
  { from: 'simrunner', to: 'twitter',     color: 0x1da1f2 },
  { from: 'simrunner', to: 'reddit',      color: 0xff4500 },
  { from: 'geoevents', to: 'simrunner',   color: 0xef4444 },  // events inject

  // Live writeback loop (sim → Zep)
  { from: 'twitter',   to: 'zepmemory',   color: 0x1da1f2 },
  { from: 'reddit',    to: 'zepmemory',   color: 0xff4500 },
  { from: 'zepmemory', to: 'zepgraph',    color: 0x10b981 },  // LOOP back to graph

  // Simulation → Report (merge)
  { from: 'twitter',   to: 'reportagent', color: 0x1da1f2 },
  { from: 'reddit',    to: 'reportagent', color: 0xff4500 },
  { from: 'zepgraph',  to: 'reportagent', color: 0x10b981 },

  // Report Agent → 4 tools (fan-out)
  { from: 'reportagent', to: 'insightforge', color: 0xa855f7 },
  { from: 'reportagent', to: 'panorama',     color: 0xa855f7 },
  { from: 'reportagent', to: 'interviews',   color: 0xa855f7 },
  { from: 'reportagent', to: 'freshweb',     color: 0xa855f7 },

  // Report → Consensus
  { from: 'reportagent', to: 'consensus',    color: 0xdb5d3b },

  // Consensus independently fetches fresh web context for fact-checking
  { from: 'webintel',    to: 'consensus',    color: 0x2a9d8f },

  // Consensus → 3 AI validators (fan-out dispatch)
  { from: 'consensus',   to: 'ai1',          color: 0x22c55e },
  { from: 'consensus',   to: 'ai2',          color: 0xf97316 },
  { from: 'consensus',   to: 'ai3',          color: 0x06b6d4 },

  // Validators → back to Consensus (assessment consolidation)
  { from: 'ai1',         to: 'consensus',    color: 0x22c55e },
  { from: 'ai2',         to: 'consensus',    color: 0xf97316 },
  { from: 'ai3',         to: 'consensus',    color: 0x06b6d4 },

  // Consensus → Final output (one-way append to report)
  { from: 'consensus',   to: 'forecast',     color: 0xfbbf24 },
]

/* ── Refs ─────────────────────────────────────────── */
const canvasRef     = ref(null)
const wrapRef       = ref(null)
const hoveredNode   = ref(null)
const tooltipStyle  = ref({})

let renderer, scene, camera, controls, animId
const nodeMeshes  = []  // { mesh, node, ring, label }
const edgeObjects = []  // { tube, particles[] }
const nodeMap     = {}
const clock       = new THREE.Clock()
const raycaster   = new THREE.Raycaster()
const mouse       = new THREE.Vector2()

/* ── Material factories ───────────────────────────── */
function nodeMat(color) {
  return new THREE.MeshPhongMaterial({
    color, emissive: color, emissiveIntensity: 0.3,
    shininess: 100, transparent: true, opacity: 0.88,
  })
}

/* ── Shape factory — different geometry per role ──── */
function makeGeometry(shape) {
  switch (shape) {
    case 'box':          return new THREE.BoxGeometry(0.5, 0.5, 0.5)
    case 'octahedron':   return new THREE.OctahedronGeometry(0.35)
    case 'icosahedron':  return new THREE.IcosahedronGeometry(0.5, 0)  // central hub — larger
    case 'diamond': {
      const g = new THREE.OctahedronGeometry(0.28)
      g.scale(1, 1.4, 1)
      return g
    }
    case 'cone':         return new THREE.ConeGeometry(0.28, 0.55, 16)
    case 'dodecahedron': return new THREE.DodecahedronGeometry(0.45)
    default:             return new THREE.SphereGeometry(0.38, 24, 24)
  }
}

/* ── Text sprite (billboard label) ────────────────── */
function makeLabel(text, size = 32) {
  const c = document.createElement('canvas')
  const ctx = c.getContext('2d')
  c.width = 512; c.height = 56
  ctx.font = `600 ${size}px "JetBrains Mono","Space Grotesk",sans-serif`
  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, 256, 28)
  const tex = new THREE.CanvasTexture(c)
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.72, depthTest: false })
  const sprite = new THREE.Sprite(mat)
  sprite.scale.set(2.8, 0.32, 1)
  return sprite
}

/* ── Build a curved tube edge + flowing particles ─── */
function buildEdge(fromPos, toPos, color) {
  const mid = new THREE.Vector3().lerpVectors(fromPos, toPos, 0.5)
  // Offset mid-point perpendicular for curvature
  const dir = new THREE.Vector3().subVectors(toPos, fromPos)
  const up  = new THREE.Vector3(0, 1, 0)
  const perp = new THREE.Vector3().crossVectors(dir, up).normalize()
  mid.addScaledVector(perp, (Math.random() - 0.5) * 1.2)
  mid.y += 0.4 + Math.random() * 0.5

  const curve = new THREE.QuadraticBezierCurve3(fromPos.clone(), mid, toPos.clone())
  const tubeGeo = new THREE.TubeGeometry(curve, 36, 0.018, 6, false)
  const tubeMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.22 })
  const tube = new THREE.Mesh(tubeGeo, tubeMat)

  const particleList = []
  for (let p = 0; p < 2; p++) {
    const pGeo = new THREE.SphereGeometry(0.045, 6, 6)
    const pMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0 })
    const pMesh = new THREE.Mesh(pGeo, pMat)
    particleList.push({ mesh: pMesh, curve, t: -(p * 1.5), speed: 0.22 + Math.random() * 0.1 })
  }

  return { tube, particles: particleList }
}

/* ── Create a mini-graph cluster around the Zep hub ─ */
function buildMiniGraph(center, scene) {
  const miniNodes = 8
  const miniGeo = new THREE.SphereGeometry(0.06, 8, 8)
  const miniMat = new THREE.MeshBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.5 })
  const miniEdgeMat = new THREE.LineBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.15 })
  const orbitNodes = []

  for (let i = 0; i < miniNodes; i++) {
    const angle = (i / miniNodes) * Math.PI * 2
    const r = 0.9 + Math.random() * 0.4
    const y = (Math.random() - 0.5) * 0.8
    const pos = new THREE.Vector3(
      center.x + Math.cos(angle) * r,
      center.y + y,
      center.z + Math.sin(angle) * r
    )
    const m = new THREE.Mesh(miniGeo, miniMat.clone())
    m.position.copy(pos)
    scene.add(m)
    orbitNodes.push(m)

    // Connect some to center
    if (i % 2 === 0) {
      const pts = [center.clone(), pos.clone()]
      const lineGeo = new THREE.BufferGeometry().setFromPoints(pts)
      scene.add(new THREE.Line(lineGeo, miniEdgeMat))
    }
    // Connect to neighbor
    if (i > 0 && Math.random() > 0.4) {
      const prev = orbitNodes[i - 1].position
      const lineGeo = new THREE.BufferGeometry().setFromPoints([prev.clone(), pos.clone()])
      scene.add(new THREE.Line(lineGeo, miniEdgeMat))
    }
  }
  return orbitNodes
}

/* ── Scene setup ──────────────────────────────────── */
function init() {
  const canvas = canvasRef.value
  const wrap   = wrapRef.value
  const { width, height } = wrap.getBoundingClientRect()

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setClearColor(0x000000, 0)

  scene  = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x050810, 0.018)

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 120)
  camera.position.set(5, 6, 18)

  controls = new OrbitControls(camera, canvas)
  controls.enableDamping   = true
  controls.dampingFactor   = 0.06
  controls.autoRotate      = true
  controls.autoRotateSpeed = 0.3
  controls.enableZoom      = true
  controls.minDistance      = 8
  controls.maxDistance       = 35
  controls.enablePan       = false
  controls.target.set(5, 3.5, 0)
  controls.maxPolarAngle   = Math.PI * 0.72
  controls.minPolarAngle   = Math.PI * 0.18

  /* Lights — multi-point for depth */
  scene.add(new THREE.AmbientLight(0x1a2030, 0.6))
  const lights = [
    { color: 0x0d6f70, intensity: 1.2, pos: [-8, 8, 6]   },
    { color: 0xdb5d3b, intensity: 1.0, pos: [18, 6, -4]   },
    { color: 0x3b82f6, intensity: 0.8, pos: [-4, 2, -6]   },
    { color: 0xfbbf24, intensity: 0.9, pos: [16, 8, 2]    },
  ]
  lights.forEach(l => {
    const pl = new THREE.PointLight(l.color, l.intensity, 40)
    pl.position.set(...l.pos)
    scene.add(pl)
  })
  const dl = new THREE.DirectionalLight(0xffffff, 0.2)
  dl.position.set(5, 15, 10)
  scene.add(dl)

  /* ── Build Nodes ── */
  const meshList = []
  NODES.forEach(n => {
    const geo  = makeGeometry(n.shape)
    const mat  = nodeMat(n.color)
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.set(...n.pos)
    mesh.userData = { id: n.id, label: n.label, desc: n.desc, tag: n.tag, detail: n.detail }
    scene.add(mesh)

    // Halo ring
    const rGeo = new THREE.RingGeometry(0.48, 0.56, 24)
    const rMat = new THREE.MeshBasicMaterial({ color: n.color, transparent: true, opacity: 0.1, side: THREE.DoubleSide })
    const ring = new THREE.Mesh(rGeo, rMat)
    ring.position.copy(mesh.position)
    scene.add(ring)

    // Label
    const lbl = makeLabel(n.label, 28)
    lbl.position.set(mesh.position.x, mesh.position.y - 0.75, mesh.position.z)
    scene.add(lbl)

    const entry = { mesh, node: n, ring, label: lbl }
    nodeMeshes.push(entry)
    meshList.push(mesh)
    nodeMap[n.id] = entry
  })

  /* ── Mini knowledge graph cluster around Zep hub ── */
  const zepEntry = nodeMap['zepgraph']
  if (zepEntry) {
    buildMiniGraph(zepEntry.mesh.position, scene)
  }

  /* ── Build Edges ── */
  EDGES.forEach(e => {
    const fromEntry = nodeMap[e.from]
    const toEntry   = nodeMap[e.to]
    if (!fromEntry || !toEntry) return
    const edgeData = buildEdge(fromEntry.mesh.position, toEntry.mesh.position, e.color)
    scene.add(edgeData.tube)
    edgeData.particles.forEach(p => scene.add(p.mesh))
    edgeObjects.push(edgeData)
  })

  /* ── Star field background ── */
  const starGeo = new THREE.BufferGeometry()
  const starPos = new Float32Array(900)
  for (let i = 0; i < 900; i += 3) {
    starPos[i]   = (Math.random() - 0.5) * 50 + 5
    starPos[i+1] = (Math.random() - 0.5) * 30 + 3
    starPos[i+2] = (Math.random() - 0.5) * 30
  }
  starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPos, 3))
  scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0x0d6f70, size: 0.035, transparent: true, opacity: 0.2 })))
}

/* ── Animation loop ───────────────────────────────── */
function animate() {
  animId = requestAnimationFrame(animate)
  const dt = clock.getDelta()
  const t  = clock.getElapsedTime()
  controls.update()

  // Node breathing + shape rotation
  nodeMeshes.forEach((entry, i) => {
    const n = entry.node
    entry.mesh.position.y = n.pos[1] + Math.sin(t * 0.6 + i * 0.9) * 0.08
    // Rotate non-sphere shapes for visual interest
    if (n.shape !== 'sphere') {
      entry.mesh.rotation.y = t * 0.3 + i
      entry.mesh.rotation.x = Math.sin(t * 0.2 + i) * 0.15
    }
    // Label follows
    entry.label.position.y = entry.mesh.position.y - 0.75
    // Ring follows + faces camera + pulses
    entry.ring.position.y = entry.mesh.position.y
    entry.ring.lookAt(camera.position)
    entry.ring.material.opacity = 0.08 + Math.sin(t * 1.2 + i * 0.7) * 0.05
  })

  // Edge particles
  edgeObjects.forEach(e => {
    e.particles.forEach(p => {
      p.t += dt * p.speed
      if (p.t < 0)   { p.mesh.visible = false; return }
      if (p.t >= 1)  { p.t = -0.8 - Math.random() * 1.5; p.mesh.visible = false; return }
      p.mesh.visible = true
      p.mesh.position.copy(p.curve.getPointAt(p.t))
      const fade = Math.sin(p.t * Math.PI)
      p.mesh.material.opacity = fade * 0.8
      const s = 0.6 + fade * 0.6
      p.mesh.scale.set(s, s, s)
    })
  })

  renderer.render(scene, camera)
}

/* ── Hover interaction ────────────────────────────── */
function onPointerMove(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  mouse.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1
  mouse.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1
  raycaster.setFromCamera(mouse, camera)
  const allMeshes = nodeMeshes.map(e => e.mesh)
  const hits = raycaster.intersectObjects(allMeshes)

  if (hits.length) {
    const obj = hits[0].object
    hoveredNode.value = obj.userData
    const wrapRect = wrapRef.value.getBoundingClientRect()
    tooltipStyle.value = {
      left: `${Math.min(e.clientX - wrapRect.left + 16, wrapRect.width - 290)}px`,
      top:  `${e.clientY - wrapRect.top - 10}px`,
    }
    obj.material.emissiveIntensity = 0.75
    obj.scale.set(1.25, 1.25, 1.25)
    canvasRef.value.style.cursor = 'pointer'
  } else {
    hoveredNode.value = null
    nodeMeshes.forEach(entry => {
      entry.mesh.material.emissiveIntensity = 0.3
      entry.mesh.scale.set(1, 1, 1)
    })
    canvasRef.value.style.cursor = 'grab'
  }
}

/* ── Responsive ───────────────────────────────────── */
function onResize() {
  const wrap = wrapRef.value
  if (!wrap || !renderer) return
  const { width, height } = wrap.getBoundingClientRect()
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

/* ── Lifecycle ────────────────────────────────────── */
onMounted(() => {
  init()
  animate()
  window.addEventListener('resize', onResize)
  canvasRef.value.addEventListener('pointermove', onPointerMove)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  window.removeEventListener('resize', onResize)
  canvasRef.value?.removeEventListener('pointermove', onPointerMove)
  controls?.dispose()
  renderer?.dispose()
  scene?.traverse(obj => {
    if (obj.geometry) obj.geometry.dispose()
    if (obj.material) {
      if (obj.material.map) obj.material.map.dispose()
      obj.material.dispose()
    }
  })
})
</script>

<style scoped>
.pipeline-3d-wrap {
  position: relative;
  width: 100%;
  height: 540px;
  border-radius: 20px;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 15% 35%, rgba(13,111,112,0.10) 0%, transparent 55%),
    radial-gradient(ellipse at 85% 65%, rgba(219,93,59,0.07) 0%, transparent 45%),
    radial-gradient(ellipse at 50% 50%, rgba(59,130,246,0.04) 0%, transparent 60%),
    #050810;
}

.pipeline-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
}
.pipeline-canvas:active { cursor: grabbing; }

.node-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(5,8,16,0.94);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(13,111,112,0.35);
  border-radius: 12px;
  padding: 12px 16px;
  max-width: 280px;
  z-index: 10;
}
.tooltip-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: rgba(255,255,255,0.35);
  text-transform: uppercase;
  margin-bottom: 4px;
}
.node-tooltip strong {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  color: #5ce0d6;
  display: block;
  margin-bottom: 5px;
}
.node-tooltip p {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 0.8rem;
  color: rgba(255,255,255,0.72);
  line-height: 1.48;
  margin: 0 0 6px 0;
}
.tooltip-detail {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: rgba(255,255,255,0.38);
  line-height: 1.4;
  border-top: 1px solid rgba(255,255,255,0.08);
  padding-top: 6px;
}

.graph-hint {
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  color: rgba(255,255,255,0.2);
  pointer-events: none;
}
</style>
