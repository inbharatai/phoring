'use client'

import { ScrollReveal } from './ScrollReveal'

const POINTS = [
  {
    title: 'Not a chatbot.',
    subtitle: 'A simulation engine.',
    desc: "Phoring doesn't generate answers from a single model prompt. It runs structured multi-agent simulations where synthetic personas interact, debate, and surface emergent patterns across configurable rounds.",
    accent: '#3d6bff',
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <rect x="4" y="4" width="24" height="24" rx="4" stroke="currentColor" strokeWidth="1.2" />
        <circle cx="11" cy="16" r="3" stroke="currentColor" strokeWidth="1" />
        <circle cx="21" cy="16" r="3" stroke="currentColor" strokeWidth="1" />
        <path d="M14 16h4" stroke="currentColor" strokeWidth="0.8" strokeDasharray="2 2" />
        <path d="M11 13v-4M21 13v-4M11 19v4M21 19v4" stroke="currentColor" strokeWidth="0.6" opacity="0.3" />
      </svg>
    ),
  },
  {
    title: 'Not prediction from thin air.',
    subtitle: 'Grounded in evidence.',
    desc: 'Every forecast traces back to document-sourced entities, web-retrieved intelligence, and simulation-observed dynamics. The quality of the input directly shapes the output.',
    accent: '#22d3ee',
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <path d="M16 4v24" stroke="currentColor" strokeWidth="1" opacity="0.2" />
        <path d="M4 16h24" stroke="currentColor" strokeWidth="1" opacity="0.2" />
        <circle cx="16" cy="16" r="3" stroke="currentColor" strokeWidth="1.2" />
        <circle cx="8" cy="10" r="2" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
        <circle cx="24" cy="12" r="2" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
        <circle cx="10" cy="24" r="2" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
        <line x1="14" y1="14" x2="9.5" y2="11" stroke="currentColor" strokeWidth="0.7" opacity="0.3" />
        <line x1="18" y1="15" x2="22.5" y2="12.5" stroke="currentColor" strokeWidth="0.7" opacity="0.3" />
        <line x1="14.5" y1="18" x2="11" y2="22.5" stroke="currentColor" strokeWidth="0.7" opacity="0.3" />
      </svg>
    ),
  },
  {
    title: 'Not a black box.',
    subtitle: 'Source-cited and scored.',
    desc: 'Reports include inline references [1][2][3] to specific sources. Each section carries a confidence tag — HIGH, MEDIUM, or LOW — based on how many independent data points support it.',
    accent: '#10b981',
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <rect x="6" y="3" width="20" height="26" rx="2" stroke="currentColor" strokeWidth="1.2" />
        <line x1="10" y1="9" x2="22" y2="9" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="10" y1="13" x2="22" y2="13" stroke="currentColor" strokeWidth="1" opacity="0.4" />
        <line x1="10" y1="17" x2="18" y2="17" stroke="currentColor" strokeWidth="1" opacity="0.3" />
        <rect x="10" y="21" width="8" height="3" rx="1" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
        <path d="M12 22.5l1.5 1 2.5-2" stroke="currentColor" strokeWidth="0.7" opacity="0.6" />
      </svg>
    ),
  },
  {
    title: 'Not a single perspective.',
    subtitle: 'Multi-agent, multi-model.',
    desc: 'Optional multi-model consensus validation runs independent LLMs as validators — scoring on coherence, precedent, and risk before producing a consensus summary appended to the report.',
    accent: '#e5a60a',
    icon: (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <circle cx="16" cy="8" r="3" stroke="currentColor" strokeWidth="1.1" />
        <circle cx="8" cy="22" r="3" stroke="currentColor" strokeWidth="1.1" />
        <circle cx="24" cy="22" r="3" stroke="currentColor" strokeWidth="1.1" />
        <path d="M14 10.5L10 19.5" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
        <path d="M18 10.5L22 19.5" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
        <path d="M11 22H21" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
        <path d="M16 14v2M8 17v2M24 17v2" stroke="currentColor" strokeWidth="0.6" opacity="0.25" strokeDasharray="1 2" />
      </svg>
    ),
  },
]

export function Differentiator() {
  return (
    <section className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient glows */}
      <div className="absolute top-[30%] right-[-5%] w-[400px] h-[300px] rounded-full bg-accent-amber/[0.015] blur-[100px] pointer-events-none" aria-hidden="true" />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-16 lg:mb-20">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              Why Phoring
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              Different by architecture,
              <br />
              <span className="text-text-secondary">not by marketing.</span>
            </h2>
          </div>
        </ScrollReveal>

        <div className="grid sm:grid-cols-2 gap-5">
          {POINTS.map((pt, i) => (
            <ScrollReveal key={pt.title} delay={i * 0.1}>
              <div className="card card-shine group p-8 lg:p-10 h-full relative overflow-hidden">
                {/* Left accent bar on hover */}
                <div
                  className="absolute left-0 top-8 bottom-8 w-px opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{
                    background: `linear-gradient(to bottom, ${pt.accent}50, ${pt.accent}10, transparent)`,
                  }}
                />

                {/* Icon */}
                <div className="mb-6 relative">
                  <div
                    className="w-14 h-14 rounded-xl flex items-center justify-center border transition-all duration-400 group-hover:scale-105"
                    style={{
                      color: pt.accent,
                      borderColor: `${pt.accent}18`,
                      backgroundColor: `${pt.accent}06`,
                    }}
                  >
                    {pt.icon}
                  </div>
                  <div
                    className="absolute -inset-4 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 -z-10"
                    style={{
                      background: `radial-gradient(circle, ${pt.accent}06 0%, transparent 70%)`,
                    }}
                  />
                </div>

                <h3 className="text-lg font-semibold text-text-primary tracking-[-0.01em]">
                  {pt.title}
                </h3>
                <p
                  className="text-sm font-medium mt-1 mb-4"
                  style={{ color: `${pt.accent}90` }}
                >
                  {pt.subtitle}
                </p>
                <p className="text-[13px] leading-[1.7] text-text-secondary">
                  {pt.desc}
                </p>

                {/* Bottom accent */}
                <div
                  className="absolute bottom-0 left-8 right-8 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-600"
                  style={{
                    background: `linear-gradient(90deg, transparent, ${pt.accent}25, transparent)`,
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
