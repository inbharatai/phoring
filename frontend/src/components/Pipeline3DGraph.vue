<template>
  <div ref="wrapRef" class="pipeline-3d-wrap">
    <canvas ref="canvasRef" class="pipeline-canvas"></canvas>
    <div v-if="hoveredNode" class="node-tooltip" :style="tooltipStyle">
      <strong>{{ hoveredNode.label }}</strong>
      <p>{{ hoveredNode.desc }}</p>
    </div>
    <div class="graph-hint">Drag to rotate &middot; Scroll to zoom</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

/* ── Pipeline stages ─────────────────────────────── */
const STAGES = [
  { id: 'upload',  label: '01 — Upload',          desc: 'PDF, MD, TXT documents + scenario prompt',                              color: 0x0d6f70, pos: [-6.0,  2.0,  0.0] },
  { id: 'extract', label: '02 — Entity Extraction',desc: 'LLM-driven ontology: entities, relationships, domain concepts',         color: 0x0d6f70, pos: [-3.4,  0.4,  1.6] },
  { id: 'graph',   label: '03 — Knowledge Graph',  desc: 'Zep Cloud graph — nodes, edges, community detection',                   color: 0x0d8f90, pos: [-0.6, -1.0,  2.6] },
  { id: 'enrich',  label: '04 — Web Enrichment',   desc: 'Serper + Event Registry — real-time news & social signals',              color: 0x2a9d8f, pos: [ 1.8, -0.4,  1.6] },
  { id: 'agents',  label: '05 — Agent Profiles',   desc: 'LLM-generated personas with stance, traits, platform behaviour',        color: 0x3aafa9, pos: [ 4.0,  0.8,  0.4] },
  { id: 'sim',     label: '06 — OASIS Simulation', desc: 'Multi-agent Twitter + Reddit — parallel, 12–72 rounds',                 color: 0xe76f51, pos: [ 5.6,  2.6, -1.0] },
  { id: 'report',  label: '07 — Forecast Report',  desc: 'Source-cited predictions, confidence scoring, consensus validation',     color: 0xdb5d3b, pos: [ 3.6,  4.2, -2.0] },
]

/* ── Refs ─────────────────────────────────────────── */
const canvasRef = ref(null)
const wrapRef   = ref(null)
const hoveredNode  = ref(null)
const tooltipStyle = ref({})

let renderer, scene, camera, controls, animId
const nodeMeshes = []
const rings      = []
const labels     = []
const particles  = []
const clock      = new THREE.Clock()
const raycaster  = new THREE.Raycaster()
const mouse      = new THREE.Vector2()

/* ── Helpers ──────────────────────────────────────── */
function glowMat(color) {
  return new THREE.MeshPhongMaterial({
    color, emissive: color, emissiveIntensity: 0.35,
    shininess: 90, transparent: true, opacity: 0.92,
  })
}

function textSprite(text, size = 40) {
  const c = document.createElement('canvas')
  const x = c.getContext('2d')
  c.width = 512; c.height = 64
  x.font = `bold ${size}px "JetBrains Mono","Space Grotesk",monospace`
  x.fillStyle = '#ffffff'
  x.textAlign = 'center'
  x.textBaseline = 'middle'
  x.fillText(text, 256, 32)
  const t = new THREE.CanvasTexture(c)
  const m = new THREE.SpriteMaterial({ map: t, transparent: true, opacity: 0.82, depthTest: false })
  const s = new THREE.Sprite(m)
  s.scale.set(3.0, 0.38, 1)
  return s
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
  scene.fog = new THREE.FogExp2(0x060a10, 0.02)

  camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 100)
  camera.position.set(0, 3, 13)

  controls = new OrbitControls(camera, canvas)
  controls.enableDamping  = true
  controls.dampingFactor  = 0.06
  controls.autoRotate     = true
  controls.autoRotateSpeed = 0.5
  controls.enableZoom     = true
  controls.minDistance     = 7
  controls.maxDistance     = 22
  controls.enablePan      = false
  controls.maxPolarAngle  = Math.PI * 0.72
  controls.minPolarAngle  = Math.PI * 0.22

  /* Lights */
  scene.add(new THREE.AmbientLight(0x334455, 0.7))
  const p1 = new THREE.PointLight(0x0d6f70, 1.6, 35); p1.position.set(-6, 6, 6);  scene.add(p1)
  const p2 = new THREE.PointLight(0xdb5d3b, 1.3, 35); p2.position.set(7, 4, -4);  scene.add(p2)
  const dl = new THREE.DirectionalLight(0xffffff, 0.25); dl.position.set(0, 10, 5); scene.add(dl)

  /* ── Nodes ── */
  STAGES.forEach((s) => {
    const geo  = new THREE.SphereGeometry(0.44, 32, 32)
    const mesh = new THREE.Mesh(geo, glowMat(s.color))
    mesh.position.set(...s.pos)
    mesh.userData = { label: s.label, desc: s.desc }
    scene.add(mesh)
    nodeMeshes.push(mesh)

    // Halo ring
    const rGeo = new THREE.RingGeometry(0.54, 0.64, 32)
    const rMat = new THREE.MeshBasicMaterial({ color: s.color, transparent: true, opacity: 0.14, side: THREE.DoubleSide })
    const ring = new THREE.Mesh(rGeo, rMat)
    ring.position.copy(mesh.position)
    scene.add(ring)
    rings.push(ring)

    // Label sprite
    const lbl = textSprite(s.label, 34)
    lbl.position.set(mesh.position.x, mesh.position.y - 0.88, mesh.position.z)
    scene.add(lbl)
    labels.push(lbl)
  })

  /* ── Edges (curved tubes + flowing particles) ── */
  for (let i = 0; i < STAGES.length - 1; i++) {
    const a = new THREE.Vector3(...STAGES[i].pos)
    const b = new THREE.Vector3(...STAGES[i + 1].pos)
    const mid = new THREE.Vector3().lerpVectors(a, b, 0.5)
    mid.y += 0.7 + Math.random() * 0.5
    mid.z += (Math.random() - 0.5) * 1.4

    const curve = new THREE.QuadraticBezierCurve3(a, mid, b)

    // Thin tube geometry for the edge
    const tubeGeo = new THREE.TubeGeometry(curve, 48, 0.03, 8, false)
    const tubeMat = new THREE.MeshBasicMaterial({ color: STAGES[i].color, transparent: true, opacity: 0.28 })
    scene.add(new THREE.Mesh(tubeGeo, tubeMat))

    // Glowing particles that travel along the edge
    for (let p = 0; p < 3; p++) {
      const pGeo = new THREE.SphereGeometry(0.055, 8, 8)
      const pMat = new THREE.MeshBasicMaterial({ color: STAGES[i].color, transparent: true, opacity: 0 })
      const pMesh = new THREE.Mesh(pGeo, pMat)
      scene.add(pMesh)
      particles.push({ mesh: pMesh, curve, t: -(p * 1.1), speed: 0.28 + Math.random() * 0.12 })
    }
  }

  /* ── Background star field ── */
  const starGeo = new THREE.BufferGeometry()
  const starPos = new Float32Array(600)
  for (let i = 0; i < 600; i += 3) {
    starPos[i]   = (Math.random() - 0.5) * 34
    starPos[i+1] = (Math.random() - 0.5) * 24
    starPos[i+2] = (Math.random() - 0.5) * 24
  }
  starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPos, 3))
  scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0x0d6f70, size: 0.04, transparent: true, opacity: 0.25 })))
}

/* ── Animation loop ───────────────────────────────── */
function animate() {
  animId = requestAnimationFrame(animate)
  const dt = clock.getDelta()
  const t  = clock.getElapsedTime()
  controls.update()

  // Node breathing
  nodeMeshes.forEach((m, i) => {
    m.position.y = STAGES[i].pos[1] + Math.sin(t * 0.7 + i * 1.3) * 0.1
  })

  // Labels follow nodes
  labels.forEach((l, i) => {
    l.position.y = nodeMeshes[i].position.y - 0.88
  })

  // Rings face camera + pulse
  rings.forEach((r, i) => {
    r.position.y = nodeMeshes[i].position.y
    r.lookAt(camera.position)
    r.material.opacity = 0.1 + Math.sin(t * 1.4 + i) * 0.06
  })

  // Particles flow along edges
  particles.forEach((p) => {
    p.t += dt * p.speed
    if (p.t < 0) { p.mesh.visible = false; return }
    if (p.t >= 1) { p.t = -0.6 - Math.random() * 1.4; p.mesh.visible = false; return }
    p.mesh.visible = true
    p.mesh.position.copy(p.curve.getPointAt(p.t))
    const fade = Math.sin(p.t * Math.PI)
    p.mesh.material.opacity = fade * 0.85
    const s = 0.75 + fade * 0.6
    p.mesh.scale.set(s, s, s)
  })

  renderer.render(scene, camera)
}

/* ── Hover interaction ────────────────────────────── */
function onPointerMove(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  mouse.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1
  mouse.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1
  raycaster.setFromCamera(mouse, camera)
  const hits = raycaster.intersectObjects(nodeMeshes)

  if (hits.length) {
    const obj = hits[0].object
    hoveredNode.value = obj.userData
    const wrapRect = wrapRef.value.getBoundingClientRect()
    tooltipStyle.value = {
      left: `${e.clientX - wrapRect.left + 16}px`,
      top:  `${e.clientY - wrapRect.top  - 10}px`,
    }
    obj.material.emissiveIntensity = 0.85
    obj.scale.set(1.22, 1.22, 1.22)
    canvasRef.value.style.cursor = 'pointer'
  } else {
    hoveredNode.value = null
    nodeMeshes.forEach((m) => { m.material.emissiveIntensity = 0.35; m.scale.set(1, 1, 1) })
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
  scene?.traverse((obj) => {
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
  height: 480px;
  border-radius: 20px;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 28% 38%, rgba(13,111,112,0.10) 0%, transparent 60%),
    radial-gradient(ellipse at 72% 62%, rgba(219,93,59,0.07) 0%, transparent 50%),
    #060a10;
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
  background: rgba(8,12,20,0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(13,111,112,0.45);
  border-radius: 10px;
  padding: 10px 14px;
  max-width: 270px;
  z-index: 10;
}
.node-tooltip strong {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.76rem;
  letter-spacing: 0.06em;
  color: #5ce0d6;
  display: block;
  margin-bottom: 4px;
}
.node-tooltip p {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 0.82rem;
  color: rgba(255,255,255,0.72);
  line-height: 1.45;
  margin: 0;
}

.graph-hint {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.1em;
  color: rgba(255,255,255,0.25);
  pointer-events: none;
}
</style>
