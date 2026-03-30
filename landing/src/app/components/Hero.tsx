'use client'

import { motion } from 'motion/react'
import Image from 'next/image'
import { IntelligenceField } from './IntelligenceField'
import { ScenarioGraph } from './ScenarioGraph'

const ease: [number, number, number, number] = [0.21, 0.47, 0.32, 0.98]

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden pt-16">
      {/* ── Live intelligence particle field ── */}
      <div className="absolute inset-0 z-0">
        <IntelligenceField />
      </div>

      {/* ── Atmospheric overlays ── */}
      <div className="absolute inset-0 pointer-events-none z-[1]" aria-hidden="true">
        {/* Primary radial bloom */}
        <div className="absolute top-[25%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[700px] rounded-full bg-accent-blue/[0.04] blur-[160px]" />
        {/* Secondary accent bloom */}
        <div className="absolute top-[15%] right-[10%] w-[400px] h-[400px] rounded-full bg-accent-cyan/[0.03] blur-[120px]" />
        {/* Left warm bloom */}
        <div className="absolute bottom-[20%] left-[5%] w-[350px] h-[350px] rounded-full bg-accent-amber/[0.015] blur-[100px]" />
        
        {/* Analytical grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(61,107,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(61,107,255,0.5) 1px, transparent 1px)',
            backgroundSize: '80px 80px',
          }}
        />

        {/* Top vignette */}
        <div className="absolute top-0 inset-x-0 h-40 bg-gradient-to-b from-bg/70 to-transparent" />
      </div>

      {/* ── Content ── */}
      <div className="container-lg relative z-10 grid lg:grid-cols-[1fr_1.1fr] gap-10 lg:gap-16 items-center py-20 lg:py-28">
        {/* ── Text column ── */}
        <div className="max-w-xl">
          {/* Logo + eyebrow */}
          <motion.div
            className="flex items-center gap-3.5 mb-10"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1, ease }}
          >
            <div className="relative">
              <Image
                src="/phoring_logo.png"
                alt="Phoring"
                width={44}
                height={44}
                className="drop-shadow-[0_0_12px_rgba(61,107,255,0.25)]"
                priority
              />
              {/* Logo glow ring */}
              <div className="absolute inset-0 rounded-full border border-accent-blue/15 animate-pulse-ring scale-[1.6]" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono text-[11px] font-semibold tracking-[0.18em] text-accent-blue/80">
                PHORING
              </span>
              <span className="font-mono text-[9px] tracking-[0.12em] text-text-tertiary uppercase">
                Scenario Intelligence
              </span>
            </div>
          </motion.div>

          {/* Headline */}
          <motion.h1
            className="text-[2.5rem] sm:text-[3.25rem] lg:text-[4rem] xl:text-[4.5rem] font-bold leading-[1.02] tracking-[-0.04em] text-text-primary mb-7"
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.25, ease }}
          >
            From raw signals,
            <br />
            <span className="text-gradient">structured foresight.</span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            className="text-base sm:text-lg leading-[1.75] text-text-secondary mb-11 max-w-[440px]"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4, ease }}
          >
            Build knowledge graphs from documents. Run multi-agent 
            simulations. Generate source-cited intelligence reports 
            with confidence scoring.
          </motion.p>

          {/* CTAs */}
          <motion.div
            className="flex flex-col sm:flex-row items-start sm:items-center gap-3.5"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.55, ease }}
          >
            <a
              href="#start"
              className="group relative px-8 py-4 text-[15px] font-semibold bg-accent-blue text-white rounded-xl overflow-hidden transition-all duration-400 hover:shadow-[0_0_60px_rgba(61,107,255,0.35)] hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="relative z-10">Start Forecasting</span>
              <span className="absolute inset-0 bg-gradient-to-r from-accent-blue via-[#4a78ff] to-accent-blue bg-[length:200%_100%] opacity-0 group-hover:opacity-100 group-hover:animate-[gradient-shift_2s_ease_infinite] transition-opacity duration-300" />
            </a>
            <a
              href="#how-it-works"
              className="group px-8 py-4 text-[15px] text-text-secondary border border-border rounded-xl transition-all duration-400 hover:text-text-primary hover:border-border-hover hover:bg-bg-elevated/50"
            >
              <span className="group-hover:translate-x-0.5 transition-transform duration-300 inline-block">
                See How It Works →
              </span>
            </a>
          </motion.div>

          {/* Trust stat strip */}
          <motion.div
            className="flex flex-wrap items-center gap-x-8 gap-y-4 mt-16 pt-8 border-t border-border/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.7, ease }}
          >
            {[
              { value: '4', unit: 'Stage', label: 'Pipeline' },
              { value: '3', unit: 'Model', label: 'Consensus' },
              { value: '100%', unit: 'Source', label: 'Cited' },
              { value: '11', unit: 'Services', label: 'Integrated' },
            ].map((item, i) => (
              <div key={i} className="flex items-baseline gap-1.5 min-w-[80px]">
                <span className="text-xl font-bold text-text-primary font-mono tracking-tight">
                  {item.value}
                </span>
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase tracking-[0.1em] text-text-tertiary font-mono leading-none">
                    {item.unit}
                  </span>
                  <span className="text-[9px] uppercase tracking-[0.08em] text-text-tertiary/60 font-mono">
                    {item.label}
                  </span>
                </div>
              </div>
            ))}
          </motion.div>
        </div>

        {/* ── Scenario graph visual column ── */}
        <motion.div
          className="relative h-[320px] sm:h-[420px] lg:h-[560px] xl:h-[620px]"
          initial={{ opacity: 0, scale: 0.94, x: 30 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          transition={{ duration: 1.4, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          {/* Atmospheric glow behind graph */}
          <div className="absolute inset-0 -m-8 rounded-3xl bg-gradient-to-br from-accent-blue/[0.03] via-transparent to-accent-cyan/[0.02] blur-xl" aria-hidden="true" />
          <ScenarioGraph />
        </motion.div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 inset-x-0 h-48 bg-gradient-to-t from-bg via-bg/80 to-transparent pointer-events-none z-10" />
    </section>
  )
}
