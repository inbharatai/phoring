'use client'

import { useRef, useEffect, useState } from 'react'
import { ScrollReveal } from './ScrollReveal'

function SignalCanvas({ r, g, b }: { r: number; g: number; b: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  useEffect(() => {
    if (!mounted) return
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = 120 * dpr
    canvas.height = 80 * dpr
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    const points: { x: number; phase: number; speed: number }[] = []
    for (let i = 0; i < 5; i++) {
      points.push({
        x: 10 + i * 25,
        phase: Math.random() * Math.PI * 2,
        speed: 0.02 + Math.random() * 0.02,
      })
    }

    const animate = () => {
      ctx.clearRect(0, 0, 120, 80)
      ctx.beginPath()
      for (let i = 0; i < points.length; i++) {
        const p = points[i]
        p.phase += p.speed
        const y = 40 + Math.sin(p.phase) * 18
        if (i === 0) ctx.moveTo(p.x, y)
        else ctx.lineTo(p.x, y)
      }
      ctx.strokeStyle = `rgba(${r},${g},${b},0.15)`
      ctx.lineWidth = 1
      ctx.stroke()

      for (const p of points) {
        const y = 40 + Math.sin(p.phase) * 18
        const pulse = Math.sin(p.phase * 1.5) * 0.3 + 0.7
        ctx.beginPath()
        ctx.arc(p.x, y, 6, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b},${0.06 * pulse})`
        ctx.fill()
        ctx.beginPath()
        ctx.arc(p.x, y, 2.5, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${r},${g},${b},${0.5 * pulse})`
        ctx.fill()
      }
      animRef.current = requestAnimationFrame(animate)
    }
    animRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animRef.current)
  }, [mounted, r, g, b])

  if (!mounted) return <div className="w-[120px] h-[80px]" />
  return <canvas ref={ref} className="w-[120px] h-[80px]" aria-hidden="true" />
}

const CAPABILITIES = [
  {
    tag: 'SIGNAL',
    title: 'Signal Ingestion',
    description:
      'Ingests public, policy, and market sources, extracts entities and relationships, and builds a traceable knowledge graph for instability monitoring.',
    r: 61, g: 107, b: 255,
  },
  {
    tag: 'MODEL',
    title: 'Scenario Simulation',
    description:
      'Deploys agent personas into synthetic environments to test how geopolitical and policy shocks could propagate across narratives and risk drivers.',
    r: 34, g: 211, b: 238,
  },
  {
    tag: 'OUTPUT',
    title: 'Risk Scenarios',
    description:
      'Generates source-cited risk scenarios with confidence-scored reports and early-warning alerts. Every claim traces back to evidence.',
    r: 16, g: 185, b: 129,
  },
]

export function WhatPhoring() {
  return (
    <section className="relative py-28 lg:py-44">
      <div
        className="absolute top-[20%] right-[-5%] w-[500px] h-[400px] rounded-full bg-accent-blue/[0.02] blur-[120px] pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="absolute bottom-[10%] left-[-3%] w-[400px] h-[300px] rounded-full bg-accent-emerald/[0.015] blur-[100px] pointer-events-none"
        aria-hidden="true"
      />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-16 lg:mb-20">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              What Phoring Does
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              From signals and evidence
              <br />
              <span className="text-text-secondary">
                to early-warning scenarios.
              </span>
            </h2>
          </div>
        </ScrollReveal>

        <div className="grid md:grid-cols-3 gap-5 lg:gap-6">
          {CAPABILITIES.map((cap, i) => (
            <ScrollReveal key={cap.tag} delay={i * 0.12}>
              <div className="card card-shine group p-8 lg:p-10 h-full relative overflow-hidden">
                <div
                  className="absolute top-0 left-8 right-8 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-600"
                  style={{
                    background: `linear-gradient(90deg, transparent, rgba(${cap.r},${cap.g},${cap.b},0.3), transparent)`,
                  }}
                />

                <div className="mb-5 -ml-2">
                  <SignalCanvas r={cap.r} g={cap.g} b={cap.b} />
                </div>

                <span
                  className="inline-block font-mono text-[10px] tracking-[0.12em] uppercase px-2.5 py-1 rounded border mb-5 transition-all duration-400"
                  style={{
                    color: `rgba(${cap.r},${cap.g},${cap.b},0.8)`,
                    borderColor: `rgba(${cap.r},${cap.g},${cap.b},0.15)`,
                    backgroundColor: `rgba(${cap.r},${cap.g},${cap.b},0.05)`,
                  }}
                >
                  {cap.tag}
                </span>

                <h3 className="text-[1.1rem] font-semibold text-text-primary mb-3 tracking-[-0.01em]">
                  {cap.title}
                </h3>
                <p className="text-sm leading-[1.75] text-text-secondary">
                  {cap.description}
                </p>

                <div
                  className="absolute -top-20 -right-20 w-40 h-40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"
                  style={{
                    background: `radial-gradient(circle, rgba(${cap.r},${cap.g},${cap.b},0.06) 0%, transparent 70%)`,
                  }}
                />
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}
