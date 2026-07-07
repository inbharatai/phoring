'use client'

import { ScrollReveal } from './ScrollReveal'

const CAPABILITIES = [
  {
    title: 'Dual-Platform Simulation',
    desc: 'Run Twitter and Reddit environments in parallel to observe how narratives and stakeholder behaviour evolve differently across social contexts.',
    accent: '#3d6bff',
    icon: (
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
        <rect x="3" y="4" width="9" height="18" rx="2" stroke="currentColor" strokeWidth="1.2" />
        <rect x="14" y="4" width="9" height="18" rx="2" stroke="currentColor" strokeWidth="1.2" />
        <line x1="7.5" y1="8" x2="7.5" y2="8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <line x1="18.5" y1="8" x2="18.5" y2="8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <line x1="5.5" y1="12" x2="9.5" y2="12" stroke="currentColor" strokeWidth="0.9" opacity="0.5" />
        <line x1="16.5" y1="12" x2="20.5" y2="12" stroke="currentColor" strokeWidth="0.9" opacity="0.5" />
      </svg>
    ),
  },
  {
    title: 'Live Agent Activity',
    desc: 'Track agent actions, platform activity, round progress and recent interactions while the simulation is running.',
    accent: '#22d3ee',
    icon: (
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
        <polyline points="3,19 8,13 12,16 17,7 23,11" stroke="currentColor" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="17" cy="7" r="2" stroke="currentColor" strokeWidth="1" />
        <line x1="3" y1="22" x2="23" y2="22" stroke="currentColor" strokeWidth="0.6" opacity="0.2" />
      </svg>
    ),
  },
  {
    title: 'Simulated-Agent Interviews',
    desc: 'Let the Report Agent question selected simulated stakeholders and incorporate their stated reasoning, concerns and likely reactions into the analysis.',
    accent: '#e5a60a',
    icon: (
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
        <circle cx="11" cy="9" r="3.5" stroke="currentColor" strokeWidth="1.2" />
        <path d="M4 21c0-3.9 3.1-7 7-7s7 3.1 7 7" stroke="currentColor" strokeWidth="1.2" fill="none" />
        <path d="M18 4l4 4M22 4l-4 4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.6" />
      </svg>
    ),
  },
  {
    title: 'Interactive Report Q&A',
    desc: 'Ask follow-up questions after report generation using the completed report, graph context, simulation evidence and fresh web intelligence.',
    accent: '#10b981',
    icon: (
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
        <path d="M4 6h18v11H9l-5 4z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <line x1="8" y1="10" x2="18" y2="10" stroke="currentColor" strokeWidth="0.9" opacity="0.5" />
        <line x1="8" y1="13" x2="14" y2="13" stroke="currentColor" strokeWidth="0.9" opacity="0.5" />
      </svg>
    ),
  },
  {
    title: 'Disruption Testing',
    desc: 'Introduce configurable geopolitical events at selected simulation rounds and analyse their downstream effects.',
    accent: '#3d6bff',
    icon: (
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
        <path d="M13 3L4 22h18L13 3z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round" />
        <line x1="13" y1="11" x2="13" y2="16" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        <circle cx="13" cy="19" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    title: 'Resilient Runtime',
    desc: 'Isolated simulation processes, adaptive stall handling, saved run parameters, restart recovery and normal, fast or express execution modes.',
    accent: '#22d3ee',
    icon: (
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden="true">
        <path d="M5 13a8 8 0 1 1 5 7.4" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" />
        <path d="M5 13l-2-2M5 13l2-2" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="17" cy="9" r="1.4" fill="currentColor" />
      </svg>
    ),
  },
]

export function BeyondForecast() {
  return (
    <section id="capabilities" className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient */}
      <div className="absolute top-[30%] right-[-4%] w-[400px] h-[300px] rounded-full bg-accent-cyan/[0.015] blur-[120px] pointer-events-none" aria-hidden="true" />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-16 lg:mb-20">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              Beyond a Forecast
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              Inspect how a scenario evolves.
              <br />
              <span className="text-text-secondary">
                Question stakeholders. Trace the evidence.
              </span>
            </h2>
            <p className="mt-6 text-sm sm:text-base leading-[1.7] text-text-secondary max-w-xl">
              Phoring lets you inspect how a scenario evolves, question simulated
              stakeholders and trace the evidence behind the final judgement.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {CAPABILITIES.map((cap, i) => (
            <ScrollReveal key={cap.title} delay={i * 0.08}>
              <div className="card card-shine group p-7 lg:p-8 h-full relative overflow-hidden">
                <div className="mb-5 relative">
                  <div
                    className="w-11 h-11 rounded-xl flex items-center justify-center border transition-all duration-400 group-hover:scale-105"
                    style={{
                      color: cap.accent,
                      borderColor: `${cap.accent}20`,
                      backgroundColor: `${cap.accent}08`,
                    }}
                  >
                    {cap.icon}
                  </div>
                  <div
                    className="absolute -inset-3 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 -z-10"
                    style={{ background: `radial-gradient(circle, ${cap.accent}08 0%, transparent 70%)` }}
                    aria-hidden="true"
                  />
                </div>

                <h3 className="text-[15px] font-semibold text-text-primary mb-2 tracking-[-0.01em]">
                  {cap.title}
                </h3>
                <p className="text-[13px] leading-[1.7] text-text-secondary">
                  {cap.desc}
                </p>

                <div
                  className="absolute bottom-0 left-6 right-6 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-600"
                  style={{ background: `linear-gradient(90deg, transparent, ${cap.accent}30, transparent)` }}
                />
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}