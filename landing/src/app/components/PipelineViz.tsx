'use client'

import { useRef, useEffect } from 'react'

/* ──────────────────────────────────────────────────────────────
   PipelineViz — Canvas-rendered animated flow visualization
   showing data traveling through the 4-stage Phoring pipeline:
   Graph Build → Agent Setup → Simulation → Intelligence Report
   
   Particles flow along glowing paths from left to right,
   branching at each stage and converging at the output.
   ────────────────────────────────────────────────────────────── */

const BLUE: [number, number, number] = [61, 107, 255]
const CYAN: [number, number, number] = [34, 211, 238]
const AMBER: [number, number, number] = [229, 166, 10]
const GREEN: [number, number, number] = [16, 185, 129]

interface StageHub {
  x: number
  y: number
  r: number
  color: [number, number, number]
  label: string
}

interface FlowParticle {
  fromStage: number
  toStage: number
  progress: number
  speed: number
  color: [number, number, number]
  size: number
  yOffset: number
}

const STAGES: StageHub[] = [
  { x: 0.12, y: 0.5, r: 22, color: BLUE, label: 'GRAPH' },
  { x: 0.37, y: 0.5, r: 22, color: CYAN, label: 'AGENTS' },
  { x: 0.63, y: 0.5, r: 22, color: AMBER, label: 'SIM' },
  { x: 0.88, y: 0.5, r: 22, color: GREEN, label: 'REPORT' },
]

export function PipelineViz() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    let w = 0, h = 0

    const particles: FlowParticle[] = []

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      w = rect.width
      h = rect.height
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const animate = (time: number) => {
      ctx.clearRect(0, 0, w, h)

      // ── Draw connecting paths ──
      for (let i = 0; i < STAGES.length - 1; i++) {
        const a = STAGES[i], b = STAGES[i + 1]
        const ax = a.x * w, ay = a.y * h
        const bx = b.x * w, by = b.y * h

        // Main path
        ctx.beginPath()
        ctx.moveTo(ax + a.r, ay)
        ctx.lineTo(bx - b.r, by)
        ctx.strokeStyle = `rgba(${b.color[0]},${b.color[1]},${b.color[2]},0.08)`
        ctx.lineWidth = 2
        ctx.stroke()

        // Branch paths (above and below)
        for (const offset of [-0.18, 0.18]) {
          const midY = ay + offset * h
          ctx.beginPath()
          ctx.moveTo(ax + a.r, ay)
          const cpx1 = ax + (bx - ax) * 0.35
          const cpx2 = ax + (bx - ax) * 0.65
          ctx.bezierCurveTo(cpx1, midY, cpx2, midY, bx - b.r, by)
          ctx.strokeStyle = `rgba(${b.color[0]},${b.color[1]},${b.color[2]},0.04)`
          ctx.lineWidth = 1
          ctx.stroke()
        }
      }

      // ── Draw stage hubs ──
      for (let i = 0; i < STAGES.length; i++) {
        const s = STAGES[i]
        const sx = s.x * w, sy = s.y * h
        const [r, g, b] = s.color
        const pulse = Math.sin(time * 0.002 + i * 1.5) * 0.3 + 0.7

        // Outer glow
        const grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, s.r * 3)
        grad.addColorStop(0, `rgba(${r},${g},${b},${0.06 * pulse})`)
        grad.addColorStop(1, `rgba(${r},${g},${b},0)`)
        ctx.beginPath()
        ctx.arc(sx, sy, s.r * 3, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()

        // Ring
        ctx.beginPath()
        ctx.arc(sx, sy, s.r, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(${r},${g},${b},${0.3 * pulse})`
        ctx.lineWidth = 1.5
        ctx.stroke()

        // Inner fill
        ctx.beginPath()
        ctx.arc(sx, sy, s.r - 1, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b},${0.05 * pulse})`
        ctx.fill()

        // Core dot
        ctx.beginPath()
        ctx.arc(sx, sy, 3, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b},${0.6 * pulse})`
        ctx.fill()

        // Label
        ctx.font = `600 ${Math.max(8, Math.min(10, w * 0.012))}px var(--font-mono)`
        ctx.textAlign = 'center'
        ctx.fillStyle = `rgba(${r},${g},${b},0.5)`
        ctx.fillText(s.label, sx, sy + s.r + 18)
      }

      // ── Spawn flow particles ──
      if (particles.length < 25 && Math.random() < 0.06) {
        const fromStage = Math.floor(Math.random() * (STAGES.length - 1))
        const toStage = fromStage + 1
        const color = STAGES[toStage].color
        particles.push({
          fromStage,
          toStage,
          progress: 0,
          speed: 0.003 + Math.random() * 0.005,
          color,
          size: 1.5 + Math.random() * 2,
          yOffset: (Math.random() - 0.5) * 0.3,
        })
      }

      // ── Update + draw flow particles ──
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i]
        p.progress += p.speed
        if (p.progress > 1) { particles.splice(i, 1); continue }

        const a = STAGES[p.fromStage], b = STAGES[p.toStage]
        const ax = a.x * w, ay = a.y * h
        const bx = b.x * w, by = b.y * h
        const midY = ay + p.yOffset * h

        // Bezier position
        const t = p.progress
        const u = 1 - t
        const cpx1 = ax + (bx - ax) * 0.35
        const cpx2 = ax + (bx - ax) * 0.65
        const px = u*u*u*ax + 3*u*u*t*cpx1 + 3*u*t*t*cpx2 + t*t*t*bx
        const py = u*u*u*ay + 3*u*u*t*midY + 3*u*t*t*midY + t*t*t*by

        const [r, g, bb] = p.color
        const fadeAlpha = Math.sin(p.progress * Math.PI)

        // Trail glow
        const trailGrad = ctx.createRadialGradient(px, py, 0, px, py, p.size * 5)
        trailGrad.addColorStop(0, `rgba(${r},${g},${bb},${fadeAlpha * 0.25})`)
        trailGrad.addColorStop(1, `rgba(${r},${g},${bb},0)`)
        ctx.beginPath()
        ctx.arc(px, py, p.size * 5, 0, Math.PI * 2)
        ctx.fillStyle = trailGrad
        ctx.fill()

        // Core
        ctx.beginPath()
        ctx.arc(px, py, p.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${bb},${fadeAlpha * 0.7})`
        ctx.fill()
      }

      // ── Input/output labels ──
      ctx.font = `500 ${Math.max(7, Math.min(9, w * 0.01))}px var(--font-mono)`
      ctx.textAlign = 'center'

      // Input arrow
      ctx.fillStyle = 'rgba(61,107,255,0.3)'
      ctx.fillText('INPUT', STAGES[0].x * w, STAGES[0].y * h - STAGES[0].r - 12)

      // Output arrow
      ctx.fillStyle = 'rgba(16,185,129,0.3)'
      ctx.fillText('OUTPUT', STAGES[3].x * w, STAGES[3].y * h - STAGES[3].r - 12)

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
      style={{ minHeight: 180 }}
      aria-hidden="true"
    />
  )
}
