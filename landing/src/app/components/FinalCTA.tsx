'use client'

import { useRef, useEffect } from 'react'
import Image from 'next/image'
import { ScrollReveal } from './ScrollReveal'

/* Minimal ambient canvas for the CTA section — radiating pulse rings */
function PulseField() {
  const ref = useRef<HTMLCanvasElement>(null)
  const animRef = useRef(0)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.parentElement?.getBoundingClientRect()
      if (!rect) return
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const rings: { born: number; speed: number }[] = []
    let last = 0

    const animate = (t: number) => {
      const rect = canvas.parentElement?.getBoundingClientRect()
      if (!rect) { animRef.current = requestAnimationFrame(animate); return }
      const w = rect.width
      const h = rect.height
      ctx.clearRect(0, 0, w, h)

      // Spawn ring every ~2.5s
      if (t - last > 2500) {
        rings.push({ born: t, speed: 0.04 + Math.random() * 0.02 })
        last = t
        if (rings.length > 6) rings.shift()
      }

      const cx = w / 2
      const cy = h / 2

      for (const ring of rings) {
        const age = (t - ring.born) * ring.speed
        const r = age
        const maxR = Math.max(w, h) * 0.7
        if (r > maxR) continue
        const alpha = Math.max(0, 1 - r / maxR) * 0.08
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(61,107,255,${alpha})`
        ctx.lineWidth = 1
        ctx.stroke()
      }

      animRef.current = requestAnimationFrame(animate)
    }
    animRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={ref} className="absolute inset-0 w-full h-full" aria-hidden="true" />
}

export function FinalCTA() {
  return (
    <section id="start" className="relative py-32 lg:py-44">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Atmospheric glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[450px] bg-accent-blue/[0.035] blur-[140px] rounded-full pointer-events-none"
        aria-hidden="true"
      />

      {/* Pulse rings canvas */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <PulseField />
      </div>

      <div className="container-lg relative z-10 text-center max-w-2xl mx-auto">
        <ScrollReveal>
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <div className="relative">
              <Image
                src="/phoring_logo.png"
                alt="Phoring"
                width={56}
                height={56}
                className="drop-shadow-[0_0_20px_rgba(61,107,255,0.3)]"
              />
              <div className="absolute inset-0 rounded-full border border-accent-blue/15 animate-pulse-ring scale-[1.8]" />
            </div>
          </div>

          <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-6">
            Ready for Early Warning
          </span>

          <h2 className="text-[1.75rem] sm:text-[2.5rem] lg:text-[3.25rem] font-bold tracking-[-0.03em] leading-[1.08] text-text-primary mb-6">
            Start detecting
            <br />
            <span className="text-gradient">instability early.</span>
          </h2>

          <p className="text-[1.05rem] text-text-secondary leading-relaxed max-w-md mx-auto mb-10">
            Upload your sources, define a risk scenario, and let Phoring generate
            source-grounded alerts and confidence-scored reports.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="/process/new"
              className="group relative px-9 py-4 text-[15px] font-semibold bg-accent-blue text-white rounded-xl overflow-hidden transition-all duration-300 hover:shadow-[0_0_60px_rgba(61,107,255,0.3)] hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="relative z-10">Request Demo</span>
              <span className="absolute inset-0 bg-gradient-to-r from-accent-blue via-[#4a78ff] to-accent-blue bg-[length:200%_100%] opacity-0 group-hover:opacity-100 group-hover:animate-[gradient-shift_2s_ease_infinite] transition-opacity duration-300" />
            </a>
            <a
              href="https://github.com/inbharatai/phoring"
              target="_blank"
              rel="noopener noreferrer"
              className="px-9 py-4 text-[15px] text-text-secondary border border-border rounded-xl transition-all duration-300 hover:text-text-primary hover:border-border-hover hover:bg-bg-elevated/50"
            >
              View Sample Report
            </a>
          </div>
        </ScrollReveal>
      </div>
    </section>
  )
}
