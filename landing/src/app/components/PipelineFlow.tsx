'use client'

import { ScrollReveal } from './ScrollReveal'
import { PipelineViz } from './PipelineViz'

const STAGES = [
  {
    num: '01',
    title: 'Graph Build',
    desc: 'Upload documents — PDF, Markdown, or text. Phoring parses content, extracts entities and relationships via LLM-driven ontology generation, and constructs a knowledge graph in Zep.',
    accent: '#3d6bff',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <circle cx="14" cy="6" r="2.5" stroke="currentColor" strokeWidth="1.2" />
        <circle cx="6" cy="22" r="2.5" stroke="currentColor" strokeWidth="1.2" />
        <circle cx="22" cy="22" r="2.5" stroke="currentColor" strokeWidth="1.2" />
        <line x1="14" y1="8.5" x2="7.5" y2="19.5" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <line x1="14" y1="8.5" x2="20.5" y2="19.5" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <line x1="8.5" y1="22" x2="19.5" y2="22" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      </svg>
    ),
  },
  {
    num: '02',
    title: 'Agent Setup',
    desc: 'LLM-generated agent profiles emerge from graph entities. Each carries a persona, stance, behavioral parameters, and platform-specific interaction models tuned to the scenario.',
    accent: '#22d3ee',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <circle cx="14" cy="10" r="4" stroke="currentColor" strokeWidth="1.2" />
        <path d="M6 24c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="currentColor" strokeWidth="1.2" fill="none" />
        <circle cx="22" cy="8" r="2.5" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
        <circle cx="6" cy="8" r="2.5" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
      </svg>
    ),
  },
  {
    num: '03',
    title: 'Simulation',
    desc: 'OASIS deploys agents into synthetic Twitter and Reddit environments. Actions, reactions, and emergent discourse unfold across configurable rounds — streamed in real time.',
    accent: '#e5a60a',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <rect x="3" y="3" width="22" height="22" rx="3" stroke="currentColor" strokeWidth="1.2" />
        <path d="M3 10h22M10 10v15M18 10v15" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <circle cx="14" cy="17" r="3" stroke="currentColor" strokeWidth="1" opacity="0.6" />
        <path d="M12 17l1.5 1.5 3-3" stroke="currentColor" strokeWidth="1" opacity="0.6" />
      </svg>
    ),
  },
  {
    num: '04',
    title: 'Intelligence Report',
    desc: 'The Report Agent synthesizes graph data, web intelligence, and simulation outcomes into a structured document — source-cited with inline references and per-section confidence scoring.',
    accent: '#10b981',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <rect x="5" y="2" width="18" height="24" rx="2" stroke="currentColor" strokeWidth="1.2" />
        <line x1="9" y1="8" x2="19" y2="8" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <line x1="9" y1="12" x2="19" y2="12" stroke="currentColor" strokeWidth="1" opacity="0.5" />
        <line x1="9" y1="16" x2="16" y2="16" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="9" y1="20" x2="14" y2="20" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      </svg>
    ),
  },
]

export function PipelineFlow() {
  return (
    <section id="how-it-works" className="relative py-28 lg:py-44">
      {/* Section divider */}
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient */}
      <div className="absolute top-[30%] left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-accent-cyan/[0.015] blur-[140px] rounded-full pointer-events-none" aria-hidden="true" />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-12 lg:mb-16">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              How It Works
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              Four-stage pipeline.
              <br />
              <span className="text-text-secondary">
                Each step is discrete and inspectable.
              </span>
            </h2>
          </div>
        </ScrollReveal>

        {/* ── Animated flow visualization ── */}
        <ScrollReveal>
          <div className="card p-6 lg:p-8 mb-10 overflow-hidden">
            <div className="h-[140px] sm:h-[180px] lg:h-[200px]">
              <PipelineViz />
            </div>
          </div>
        </ScrollReveal>

        {/* ── Stage cards ── */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {STAGES.map((stage, i) => (
            <ScrollReveal key={stage.num} delay={i * 0.1}>
              <div className="card card-shine group p-7 lg:p-8 h-full relative overflow-hidden">
                {/* Stage indicator with icon */}
                <div className="flex items-center justify-between mb-6">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center font-mono text-sm font-bold border transition-all duration-400 group-hover:scale-105"
                    style={{
                      color: stage.accent,
                      borderColor: `${stage.accent}25`,
                      backgroundColor: `${stage.accent}08`,
                    }}
                  >
                    {stage.num}
                  </div>
                  <div style={{ color: `${stage.accent}60` }} className="group-hover:scale-110 transition-transform duration-400">
                    {stage.icon}
                  </div>
                </div>

                {/* Active signal */}
                <div className="flex items-center gap-2 mb-4">
                  <div
                    className="w-1.5 h-1.5 rounded-full animate-signal"
                    style={{ backgroundColor: stage.accent }}
                  />
                  <span className="font-mono text-[9px] tracking-[0.1em] uppercase" style={{ color: `${stage.accent}80` }}>
                    Active
                  </span>
                </div>

                <h3 className="text-base font-semibold text-text-primary mb-3 tracking-[-0.01em]">
                  {stage.title}
                </h3>
                <p className="text-[13px] leading-[1.75] text-text-secondary">
                  {stage.desc}
                </p>

                {/* Bottom + side accent on hover */}
                <div
                  className="absolute bottom-0 left-6 right-6 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-600"
                  style={{
                    background: `linear-gradient(90deg, transparent, ${stage.accent}35, transparent)`,
                  }}
                />
                <div
                  className="absolute top-8 bottom-8 left-0 w-px opacity-0 group-hover:opacity-100 transition-opacity duration-600"
                  style={{
                    background: `linear-gradient(to bottom, transparent, ${stage.accent}25, transparent)`,
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
