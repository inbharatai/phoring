'use client'

import { useRef, useEffect } from 'react'

/* ──────────────────────────────────────────────────────────────
   ScenarioGraph — Accurate Phoring Intelligence Pipeline
   
   Renders the real data-flow architecture:
   
   DOCUMENTS ──→ ONTOLOGY ──→ ZEP GRAPH
                                  │
              ┌───────────┬───────┴───────┬────────────┐
           ENTITIES   PROFILES    WEB INTEL    CONFIG
              └───────────┴───────┬───────┴────────────┘
                                  │
                           OASIS SIMULATION
                                  │
                        ┌─────────┴─────────┐
                   REPORT AGENT       ZEP TOOLS
                        └─────────┬─────────┘
                                  │
                          CONSENSUS (Multi-AI)
                                  │
                           INTELLIGENCE
   ────────────────────────────────────────────────────────────── */

const BLUE: [number, number, number] = [61, 107, 255]
const CYAN: [number, number, number] = [34, 211, 238]
const AMBER: [number, number, number] = [229, 166, 10]
const GREEN: [number, number, number] = [16, 185, 129]
const PURPLE: [number, number, number] = [147, 51, 234]
const ROSE: [number, number, number] = [244, 63, 94]

interface PNode {
  x: number; y: number; r: number
  color: [number, number, number]
  label: string
  tech?: string          // technology badge
  baseAlpha: number
}

interface PEdge {
  from: number; to: number
}

interface Signal {
  edgeIdx: number
  progress: number
  speed: number
  size: number
}

// Actual pipeline nodes (normalized 0-1 coords, bottom→top flow)
const NODES: PNode[] = [
  // Row 0 — Input (bottom)
  { x: 0.50, y: 0.92, r: 9, color: BLUE, label: 'DOCUMENTS', tech: 'PDF · MD · TXT', baseAlpha: 1.0 },

  // Row 1 — Extraction
  { x: 0.30, y: 0.76, r: 6, color: CYAN, label: 'ONTOLOGY', tech: 'LLM', baseAlpha: 0.85 },
  { x: 0.70, y: 0.76, r: 7, color: BLUE, label: 'ZEP GRAPH', tech: 'Zep Cloud', baseAlpha: 0.9 },

  // Row 2 — Parallel enrichment (4 branches from graph)
  { x: 0.12, y: 0.55, r: 4.5, color: GREEN, label: 'ENTITIES', tech: 'Zep', baseAlpha: 0.7 },
  { x: 0.37, y: 0.52, r: 5, color: PURPLE, label: 'PROFILES', tech: 'LLM + OASIS', baseAlpha: 0.75 },
  { x: 0.63, y: 0.52, r: 5, color: AMBER, label: 'WEB INTEL', tech: 'Serper · News', baseAlpha: 0.75 },
  { x: 0.88, y: 0.55, r: 4.5, color: CYAN, label: 'CONFIG', tech: 'LLM', baseAlpha: 0.7 },

  // Row 3 — Simulation (convergence)
  { x: 0.50, y: 0.36, r: 8, color: AMBER, label: 'SIMULATION', tech: 'OASIS · CAMEL', baseAlpha: 0.9 },

  // Row 4 — Report generation (branches)
  { x: 0.32, y: 0.20, r: 5.5, color: GREEN, label: 'REPORT AGENT', tech: 'ReACT Loop', baseAlpha: 0.8 },
  { x: 0.68, y: 0.20, r: 4.5, color: BLUE, label: 'ZEP TOOLS', tech: 'Search · Query', baseAlpha: 0.7 },

  // Row 5 — Consensus
  { x: 0.50, y: 0.08, r: 6, color: ROSE, label: 'CONSENSUS', tech: 'Multi-AI', baseAlpha: 0.85 },
]

const EDGES: PEdge[] = [
  // Documents → Ontology, Zep Graph
  { from: 0, to: 1 }, { from: 0, to: 2 },
  // Ontology ↔ Zep Graph
  { from: 1, to: 2 },
  // Zep Graph → 4 parallel branches
  { from: 2, to: 3 }, { from: 2, to: 4 }, { from: 2, to: 5 }, { from: 2, to: 6 },
  // Entities → Profiles (feed)
  { from: 3, to: 4 },
  // All 4 branches → Simulation
  { from: 3, to: 7 }, { from: 4, to: 7 }, { from: 5, to: 7 }, { from: 6, to: 7 },
  // Simulation → Report Agent, Zep Tools
  { from: 7, to: 8 }, { from: 7, to: 9 },
  // Zep Tools ↔ Report Agent
  { from: 9, to: 8 },
  // Report → Consensus
  { from: 8, to: 10 },
]

function bezierPoint(
  ax: number, ay: number, bx: number, by: number, t: number
) {
  // Quadratic bezier with control point pulled toward vertical center
  const mx = (ax + bx) / 2
  const my = ay - (ay - by) * 0.6
  const u = 1 - t
  return {
    x: u * u * ax + 2 * u * t * mx + t * t * bx,
    y: u * u * ay + 2 * u * t * my + t * t * by,
  }
}

export function ScenarioGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    let w = 0, h = 0
    const phases = NODES.map(() => Math.random() * Math.PI * 2)
    const signals: Signal[] = []

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      w = rect.width; h = rect.height
      canvas.width = w * dpr; canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const startTime = performance.now()
    const INTRO = 4000

    const animate = (time: number) => {
      const elapsed = time - startTime
      ctx.clearRect(0, 0, w, h)

      const intro = Math.min(elapsed / INTRO, 1)
      const ease = 1 - Math.pow(1 - intro, 3)

      const nx = (v: number) => v * w
      const ny = (v: number) => v * h

      // ── Edges ──
      for (let i = 0; i < EDGES.length; i++) {
        const e = EDGES[i]
        const a = NODES[e.from], b = NODES[e.to]
        const [r, g, bb] = b.color

        // Stagger by depth
        const depthFactor = 1 - b.y
        const edgeDelay = depthFactor * 0.5
        const edgeIntro = Math.max(0, Math.min((ease - edgeDelay) / (1 - edgeDelay), 1))
        if (edgeIntro <= 0) continue

        // Draw edge
        const steps = 50
        const drawSteps = Math.floor(steps * edgeIntro)

        ctx.beginPath()
        for (let s = 0; s <= drawSteps; s++) {
          const t = s / steps
          const p = bezierPoint(nx(a.x), ny(a.y), nx(b.x), ny(b.y), t)
          if (s === 0) ctx.moveTo(p.x, p.y)
          else ctx.lineTo(p.x, p.y)
        }
        ctx.strokeStyle = `rgba(${r},${g},${bb},${0.18 * edgeIntro})`
        ctx.lineWidth = 1.2
        ctx.stroke()

        // Glow version (wider, fainter)
        if (edgeIntro > 0.5) {
          ctx.beginPath()
          for (let s = 0; s <= drawSteps; s++) {
            const t = s / steps
            const p = bezierPoint(nx(a.x), ny(a.y), nx(b.x), ny(b.y), t)
            if (s === 0) ctx.moveTo(p.x, p.y)
            else ctx.lineTo(p.x, p.y)
          }
          ctx.strokeStyle = `rgba(${r},${g},${bb},${0.04 * edgeIntro})`
          ctx.lineWidth = 4
          ctx.stroke()
        }
      }

      // ── Nodes ──
      for (let i = 0; i < NODES.length; i++) {
        const n = NODES[i]
        phases[i] += 0.015 + (i % 3) * 0.003

        const depthFactor = 1 - n.y
        const nodeDelay = depthFactor * 0.5
        const nodeIntro = Math.max(0, Math.min((ease - nodeDelay) / (1 - nodeDelay), 1))
        if (nodeIntro <= 0) continue

        const pulse = Math.sin(phases[i]) * 0.3 + 0.7
        const alpha = n.baseAlpha * nodeIntro * pulse
        const [r, g, b] = n.color
        const px = nx(n.x), py = ny(n.y)
        const rr = n.r * nodeIntro

        // Outer atmospheric glow
        const outerGrad = ctx.createRadialGradient(px, py, 0, px, py, rr * 6)
        outerGrad.addColorStop(0, `rgba(${r},${g},${b},${alpha * 0.12})`)
        outerGrad.addColorStop(0.5, `rgba(${r},${g},${b},${alpha * 0.03})`)
        outerGrad.addColorStop(1, `rgba(${r},${g},${b},0)`)
        ctx.beginPath()
        ctx.arc(px, py, rr * 6, 0, Math.PI * 2)
        ctx.fillStyle = outerGrad
        ctx.fill()

        // Mid glow ring
        ctx.beginPath()
        ctx.arc(px, py, rr * 2.5, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(${r},${g},${b},${alpha * 0.12})`
        ctx.lineWidth = 0.8
        ctx.stroke()

        // Core fill
        const coreGrad = ctx.createRadialGradient(px, py, 0, px, py, rr)
        coreGrad.addColorStop(0, `rgba(${r},${g},${b},${alpha * 0.9})`)
        coreGrad.addColorStop(0.7, `rgba(${r},${g},${b},${alpha * 0.6})`)
        coreGrad.addColorStop(1, `rgba(${r},${g},${b},${alpha * 0.2})`)
        ctx.beginPath()
        ctx.arc(px, py, rr, 0, Math.PI * 2)
        ctx.fillStyle = coreGrad
        ctx.fill()

        // Bright center
        ctx.beginPath()
        ctx.arc(px, py, rr * 0.35, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`
        ctx.fill()

        // Pulse rings for key nodes (DOCUMENTS, SIMULATION, CONSENSUS)
        if ((i === 0 || i === 7 || i === 10) && nodeIntro > 0.5) {
          const ringA = Math.sin(time * 0.002 + i) * 0.3 + 0.5
          ctx.beginPath()
          ctx.arc(px, py, rr * 3 * nodeIntro, 0, Math.PI * 2)
          ctx.strokeStyle = `rgba(${r},${g},${b},${ringA * 0.15 * nodeIntro})`
          ctx.lineWidth = 0.7
          ctx.stroke()
        }

        // Label — stage name
        if (nodeIntro > 0.6) {
          const labAlpha = (nodeIntro - 0.6) / 0.4
          const fontSize = Math.max(7, Math.min(9.5, w * 0.012))
          ctx.font = `600 ${fontSize}px var(--font-mono)`
          ctx.textAlign = 'center'
          ctx.fillStyle = `rgba(${r},${g},${b},${labAlpha * 0.92})`
          ctx.fillText(n.label, px, py - rr - 10)

          // Tech badge
          if (n.tech) {
            const techSize = Math.max(6, Math.min(7.5, w * 0.009))
            ctx.font = `400 ${techSize}px var(--font-mono)`
            ctx.fillStyle = `rgba(${r},${g},${b},${labAlpha * 0.60})`
            ctx.fillText(n.tech, px, py - rr - 1)
          }
        }
      }

      // ── Spawn data signals ──
      if (ease > 0.5 && signals.length < 18 && Math.random() < 0.04) {
        const edgeIdx = Math.floor(Math.random() * EDGES.length)
        signals.push({
          edgeIdx,
          progress: 0,
          speed: 0.003 + Math.random() * 0.005,
          size: 1.5 + Math.random() * 2,
        })
      }

      // ── Draw data signals ──
      for (let i = signals.length - 1; i >= 0; i--) {
        const s = signals[i]
        s.progress += s.speed
        if (s.progress > 1) { signals.splice(i, 1); continue }

        const e = EDGES[s.edgeIdx]
        const a = NODES[e.from], b = NODES[e.to]
        const pos = bezierPoint(nx(a.x), ny(a.y), nx(b.x), ny(b.y), s.progress)
        const [r, g, bb] = b.color
        const fadeAlpha = Math.sin(s.progress * Math.PI)

        // Trail glow
        const trail = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, s.size * 6)
        trail.addColorStop(0, `rgba(${r},${g},${bb},${fadeAlpha * 0.25})`)
        trail.addColorStop(1, `rgba(${r},${g},${bb},0)`)
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, s.size * 6, 0, Math.PI * 2)
        ctx.fillStyle = trail
        ctx.fill()

        // Core particle
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, s.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${bb},${fadeAlpha * 0.85})`
        ctx.fill()
      }

      // ── Stage region labels (edges of canvas) ──
      if (ease > 0.85) {
        const regionAlpha = (ease - 0.85) / 0.15
        const smallFont = Math.max(6.5, Math.min(8, w * 0.009))
        ctx.font = `500 ${smallFont}px var(--font-mono)`
        ctx.textAlign = 'left'

        // Left side — stage numbers
        const stages = [
          { y: 0.92, label: 'INPUT', color: BLUE },
          { y: 0.76, label: 'STAGE 1  ·  KNOWLEDGE GRAPH', color: CYAN },
          { y: 0.53, label: 'STAGE 2  ·  ENVIRONMENT SETUP', color: PURPLE },
          { y: 0.36, label: 'STAGE 3  ·  MULTI-AGENT SIM', color: AMBER },
          { y: 0.20, label: 'STAGE 4  ·  REPORT', color: GREEN },
          { y: 0.08, label: 'OUTPUT  ·  VALIDATION', color: ROSE },
        ]

        for (const st of stages) {
          const [r, g, b] = st.color
          ctx.fillStyle = `rgba(${r},${g},${b},${regionAlpha * 0.55})`
          ctx.fillText(st.label, 6, ny(st.y) + 3)
        }
      }

      animRef.current = requestAnimationFrame(animate)
    }

    animRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      aria-hidden="true"
    />
  )
}
