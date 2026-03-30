'use client'

import { useRef, useEffect, useCallback } from 'react'

/* ──────────────────────────────────────────────────────────────
   IntelligenceField — Full-viewport canvas-rendered particle
   network that continuously animates signal pulses traveling
   between interconnected nodes. This is the atmospheric
   foundation of the hero — it should feel like watching
   a neural intelligence network processing information.
   ────────────────────────────────────────────────────────────── */

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  alpha: number
  pulsePhase: number
  pulseSpeed: number
  color: [number, number, number]
}

interface Signal {
  fromIdx: number
  toIdx: number
  progress: number
  speed: number
  color: [number, number, number]
  alpha: number
}

const COLORS: [number, number, number][] = [
  [61, 107, 255],   // blue
  [34, 211, 238],   // cyan
  [16, 185, 129],   // green
  [229, 166, 10],   // amber
]

export function IntelligenceField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)
  const particlesRef = useRef<Particle[]>([])
  const signalsRef = useRef<Signal[]>([])
  const mouseRef = useRef({ x: -1000, y: -1000 })
  const dimsRef = useRef({ w: 0, h: 0 })

  const initParticles = useCallback((w: number, h: number) => {
    const count = Math.min(Math.floor((w * h) / 12000), 120)
    const particles: Particle[] = []
    for (let i = 0; i < count; i++) {
      const color = COLORS[Math.floor(Math.random() * COLORS.length)]
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 1.8 + 0.8,
        alpha: Math.random() * 0.4 + 0.15,
        pulsePhase: Math.random() * Math.PI * 2,
        pulseSpeed: Math.random() * 0.008 + 0.003,
        color,
      })
    }
    particlesRef.current = particles
    signalsRef.current = []
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      dimsRef.current = { w: rect.width, h: rect.height }
      initParticles(rect.width, rect.height)
    }
    resize()
    window.addEventListener('resize', resize)

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top }
    }
    window.addEventListener('mousemove', onMove, { passive: true })

    const CONNECTION_DIST = 140
    const SIGNAL_SPAWN_RATE = 0.012
    let lastTime = 0

    const animate = (time: number) => {
      const dt = Math.min((time - lastTime) / 16.667, 2); // normalize to ~60fps
      lastTime = time

      const { w, h } = dimsRef.current
      const particles = particlesRef.current
      const signals = signalsRef.current
      const mouse = mouseRef.current

      ctx.clearRect(0, 0, w, h)

      // Update + draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        p.x += p.vx * dt
        p.y += p.vy * dt
        p.pulsePhase += p.pulseSpeed * dt

        // Wrap around edges
        if (p.x < -10) p.x = w + 10
        if (p.x > w + 10) p.x = -10
        if (p.y < -10) p.y = h + 10
        if (p.y > h + 10) p.y = -10

        // Mouse repulsion — subtle
        const mdx = p.x - mouse.x
        const mdy = p.y - mouse.y
        const mDist = Math.sqrt(mdx * mdx + mdy * mdy)
        if (mDist < 150 && mDist > 0) {
          const force = (150 - mDist) / 150 * 0.15
          p.vx += (mdx / mDist) * force * dt
          p.vy += (mdy / mDist) * force * dt
        }

        // Damping
        p.vx *= 0.999
        p.vy *= 0.999

        // Draw node
        const pulse = Math.sin(p.pulsePhase) * 0.5 + 0.5
        const drawAlpha = p.alpha * (0.5 + pulse * 0.5)
        const [r, g, b] = p.color

        // Glow
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b},${drawAlpha * 0.12})`
        ctx.fill()

        // Core
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b},${drawAlpha})`
        ctx.fill()
      }

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i], b = particles[j]
          const dx = a.x - b.x, dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < CONNECTION_DIST) {
            const strength = 1 - dist / CONNECTION_DIST
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.strokeStyle = `rgba(61,107,255,${strength * 0.07})`
            ctx.lineWidth = 0.5
            ctx.stroke()

            // Maybe spawn signal
            if (Math.random() < SIGNAL_SPAWN_RATE * strength * dt && signals.length < 40) {
              const color = COLORS[Math.floor(Math.random() * COLORS.length)]
              signals.push({
                fromIdx: i, toIdx: j,
                progress: 0,
                speed: 0.008 + Math.random() * 0.012,
                color,
                alpha: 0.6 + Math.random() * 0.3,
              })
            }
          }
        }
      }

      // Update + draw signals (traveling light pulses)
      for (let i = signals.length - 1; i >= 0; i--) {
        const s = signals[i]
        s.progress += s.speed * dt
        if (s.progress > 1) {
          signals.splice(i, 1)
          continue
        }

        const a = particles[s.fromIdx], b = particles[s.toIdx]
        const sx = a.x + (b.x - a.x) * s.progress
        const sy = a.y + (b.y - a.y) * s.progress
        const [r, g, b2] = s.color
        const fadeAlpha = s.alpha * Math.sin(s.progress * Math.PI) // fade in/out

        // Signal glow
        ctx.beginPath()
        ctx.arc(sx, sy, 6, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b2},${fadeAlpha * 0.2})`
        ctx.fill()

        // Signal core
        ctx.beginPath()
        ctx.arc(sx, sy, 2, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b2},${fadeAlpha})`
        ctx.fill()
      }

      animRef.current = requestAnimationFrame(animate)
    }

    animRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMove)
    }
  }, [initParticles])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-auto"
      style={{ opacity: 0.55 }}
      aria-hidden="true"
    />
  )
}
