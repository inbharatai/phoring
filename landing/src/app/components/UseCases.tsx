'use client'

import { ScrollReveal } from './ScrollReveal'

const CASES = [
  {
    title: 'Policy Shock Assessment',
    desc: 'Assess how regulatory, fiscal, and central-bank actions could ripple across sectors, institutions, and narratives.',
    accent: '#3d6bff',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M14 3L3 8.5l11 5.5 11-5.5L14 3z" stroke="currentColor" strokeWidth="1.2" />
        <path d="M3 19.5l11 5.5 11-5.5" stroke="currentColor" strokeWidth="1.2" opacity="0.5" />
        <path d="M3 14l11 5.5 11-5.5" stroke="currentColor" strokeWidth="1.2" opacity="0.7" />
      </svg>
    ),
  },
  {
    title: 'Market Narrative Shifts',
    desc: 'Track how market narratives and risk sentiment shift around events and policy signals, with evidence-backed scenarios.',
    accent: '#22d3ee',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <polyline points="3,21 8,14 14,17 20,8 25,12" stroke="currentColor" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="20" cy="8" r="2.5" stroke="currentColor" strokeWidth="1" />
        <line x1="3" y1="24" x2="25" y2="24" stroke="currentColor" strokeWidth="0.6" opacity="0.2" />
      </svg>
    ),
  },
  {
    title: 'Financial Instability Monitoring',
    desc: 'Monitor early signs of stress across markets, funding conditions, and sentiment to trigger early-warning scenarios.',
    accent: '#e5a60a',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M14 3L3 25h22L14 3z" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinejoin="round" />
        <line x1="14" y1="12" x2="14" y2="18" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        <circle cx="14" cy="21" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    title: 'Scenario-Based Risk Reporting',
    desc: 'Produce committee-ready reports that link scenarios to sources, assumptions, and confidence scores.',
    accent: '#10b981',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <circle cx="14" cy="14" r="4" stroke="currentColor" strokeWidth="1.2" />
        <circle cx="6" cy="6" r="2" stroke="currentColor" strokeWidth="0.9" opacity="0.6" />
        <circle cx="22" cy="6" r="2" stroke="currentColor" strokeWidth="0.9" opacity="0.6" />
        <circle cx="6" cy="22" r="2" stroke="currentColor" strokeWidth="0.9" opacity="0.6" />
        <circle cx="22" cy="22" r="2" stroke="currentColor" strokeWidth="0.9" opacity="0.6" />
        <line x1="11" y1="11" x2="7.5" y2="7.5" stroke="currentColor" strokeWidth="0.8" opacity="0.35" />
        <line x1="17" y1="11" x2="20.5" y2="7.5" stroke="currentColor" strokeWidth="0.8" opacity="0.35" />
        <line x1="11" y1="17" x2="7.5" y2="20.5" stroke="currentColor" strokeWidth="0.8" opacity="0.35" />
        <line x1="17" y1="17" x2="20.5" y2="20.5" stroke="currentColor" strokeWidth="0.8" opacity="0.35" />
      </svg>
    ),
  },
  {
    title: 'Geopolitical Risk Tracking',
    desc: 'Track geopolitical events, sanctions, and conflict signals to surface downstream financial exposure.',
    accent: '#3d6bff',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <circle cx="14" cy="14" r="10" stroke="currentColor" strokeWidth="1.2" />
        <ellipse cx="14" cy="14" rx="5" ry="10" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
        <line x1="4" y1="10" x2="24" y2="10" stroke="currentColor" strokeWidth="0.6" opacity="0.35" />
        <line x1="4" y1="18" x2="24" y2="18" stroke="currentColor" strokeWidth="0.6" opacity="0.35" />
      </svg>
    ),
  },
  {
    title: 'Contagion Pathway Analysis',
    desc: 'Model how shocks propagate across sectors, jurisdictions, and narratives to identify spillover pathways.',
    accent: '#22d3ee',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <circle cx="9" cy="9" r="3.5" stroke="currentColor" strokeWidth="1" />
        <circle cx="20" cy="11" r="3" stroke="currentColor" strokeWidth="0.9" opacity="0.7" />
        <circle cx="12" cy="21" r="2.5" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
        <line x1="12" y1="10.5" x2="17.5" y2="11" stroke="currentColor" strokeWidth="0.7" opacity="0.3" />
        <line x1="10.5" y1="12" x2="12" y2="18.8" stroke="currentColor" strokeWidth="0.7" opacity="0.3" />
        <line x1="18" y1="13.5" x2="14" y2="19.3" stroke="currentColor" strokeWidth="0.7" opacity="0.25" />
      </svg>
    ),
  },
]

export function UseCases() {
  return (
    <section id="use-cases" className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient glows */}
      <div
        className="absolute bottom-[10%] left-[-5%] w-[450px] h-[350px] rounded-full bg-accent-cyan/[0.015] blur-[110px] pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="absolute top-[20%] right-[-3%] w-[350px] h-[250px] rounded-full bg-accent-blue/[0.02] blur-[100px] pointer-events-none"
        aria-hidden="true"
      />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-16 lg:mb-20">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              Applications
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              Built for financial risk teams
              <br />
              <span className="text-text-secondary">
                monitoring instability and policy shocks.
              </span>
            </h2>
          </div>
        </ScrollReveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {CASES.map((c, i) => (
            <ScrollReveal key={c.title} delay={i * 0.08}>
              <div className="card card-shine group p-7 lg:p-8 h-full relative overflow-hidden">
                {/* Icon with glow */}
                <div className="mb-6 relative">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center border transition-all duration-400 group-hover:scale-105"
                    style={{
                      color: c.accent,
                      borderColor: `${c.accent}20`,
                      backgroundColor: `${c.accent}08`,
                    }}
                  >
                    {c.icon}
                  </div>
                  {/* Glow behind icon on hover */}
                  <div
                    className="absolute -inset-3 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 -z-10"
                    style={{
                      background: `radial-gradient(circle, ${c.accent}08 0%, transparent 70%)`,
                    }}
                  />
                </div>

                <h3 className="text-base font-semibold text-text-primary mb-2.5 tracking-[-0.01em]">
                  {c.title}
                </h3>
                <p className="text-[13px] leading-[1.7] text-text-secondary">
                  {c.desc}
                </p>

                {/* Bottom accent on hover */}
                <div
                  className="absolute bottom-0 left-6 right-6 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-600"
                  style={{
                    background: `linear-gradient(90deg, transparent, ${c.accent}30, transparent)`,
                  }}
                />

                {/* Corner glow on hover */}
                <div
                  className="absolute -top-16 -right-16 w-32 h-32 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"
                  style={{
                    background: `radial-gradient(circle, ${c.accent}06 0%, transparent 70%)`,
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
