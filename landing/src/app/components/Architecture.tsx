'use client'

import { ScrollReveal } from './ScrollReveal'

const STAGES = [
  { n: '01', label: 'Documents & Objective', accent: '#3d6bff' },
  { n: '02', label: 'Text Processing & Ontology', accent: '#3d6bff' },
  { n: '03', label: 'Web & News Intelligence', accent: '#22d3ee' },
  { n: '04', label: 'Zep Knowledge Graph', accent: '#22d3ee' },
  { n: '05', label: 'Behavioural Agent Generation', accent: '#e5a60a' },
  { n: '06', label: 'Simulation Config & Disruptions', accent: '#e5a60a' },
  { n: '07', label: 'Parallel Twitter & Reddit', accent: '#e5a60a' },
  { n: '08', label: 'Agentic Report & Interviews', accent: '#10b981' },
  { n: '09', label: 'Validation, Confidence & Q&A', accent: '#10b981' },
]

const RELATIONSHIPS = [
  'Documents feed text processing and ontology generation.',
  'Live intelligence enriches the graph and the scenario context.',
  'The graph feeds both agent generation and the Report Agent.',
  'Synthetic Twitter and Reddit environments run in parallel.',
  'The Report Agent combines graph, simulation and live evidence.',
  'Independent validators review the generated output.',
  'Final output is a cited report plus interactive follow-up Q&A.',
]

export function Architecture() {
  return (
    <section id="architecture" className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient */}
      <div className="absolute top-[30%] left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-accent-blue/[0.015] blur-[140px] rounded-full pointer-events-none" aria-hidden="true" />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-14 lg:mb-16">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              Architecture
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              A deeper decision-intelligence
              <br />
              <span className="text-text-secondary">architecture.</span>
            </h2>
            <p className="mt-6 text-sm sm:text-base leading-[1.7] text-text-secondary max-w-xl">
              Phoring connects evidence ingestion, graph memory, live intelligence, social
              simulation and agentic reporting in one auditable workflow.
            </p>
          </div>
        </ScrollReveal>

        {/* Nine-stage strip — horizontal scroll on small screens, full row on lg */}
        <ScrollReveal>
          <div className="card p-5 lg:p-7 mb-10">
            <div className="flex items-center gap-2.5 mb-6">
              <span className="w-1.5 h-1.5 rounded-full animate-signal bg-accent-blue" />
              <span className="font-mono text-[10px] tracking-[0.12em] uppercase text-text-tertiary">
                Nine-stage pipeline
              </span>
            </div>

            <div
              className="flex gap-3 overflow-x-auto pb-3 -mx-1 px-1 snap-x"
              role="list"
              aria-label="Phoring nine-stage architecture"
              style={{ scrollbarWidth: 'thin' }}
            >
              {STAGES.map((s, i) => (
                <div
                  key={s.n}
                  role="listitem"
                  className="snap-start flex-shrink-0 w-[150px] sm:w-[160px] relative"
                >
                  <div
                    className="rounded-xl border p-4 h-full"
                    style={{ borderColor: `${s.accent}22`, backgroundColor: `${s.accent}06` }}
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <span
                        className="font-mono text-[11px] font-bold tabular-nums"
                        style={{ color: s.accent }}
                      >
                        {s.n}
                      </span>
                      <span
                        className="h-px flex-1"
                        style={{ background: `linear-gradient(90deg, ${s.accent}40, transparent)` }}
                      />
                    </div>
                    <p className="text-[12.5px] font-medium leading-[1.4] text-text-primary">
                      {s.label}
                    </p>
                  </div>
                  {i < STAGES.length - 1 && (
                    <span
                      className="hidden lg:block absolute top-1/2 -right-2 translate-y-[-50%] text-text-tertiary"
                      aria-hidden="true"
                    >
                      →
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </ScrollReveal>

        {/* Parallel Twitter / Reddit lanes — static explanatory visual */}
        <ScrollReveal>
          <div className="card p-6 lg:p-8 mb-10 overflow-hidden">
            <div className="flex flex-col lg:flex-row gap-6 lg:gap-10 items-center">
              <div className="flex-1 w-full">
                <div className="flex items-center gap-2.5 mb-4">
                  <span className="w-1.5 h-1.5 rounded-full animate-signal" style={{ backgroundColor: '#e5a60a' }} />
                  <span className="font-mono text-[10px] tracking-[0.12em] uppercase text-text-tertiary">
                    Parallel environments · OASIS
                  </span>
                </div>
                <p className="text-[13px] leading-[1.7] text-text-secondary max-w-md">
                  Synthetic Twitter and Reddit environments powered by OASIS run
                  concurrently. Platform activity, agent actions and round progress are
                  surfaced to the interface during execution.
                </p>
              </div>

              {/* Two-lane visual */}
              <div className="w-full lg:w-[340px] flex-shrink-0">
                <div className="grid grid-cols-2 gap-3" aria-hidden="true">
                  {[
                    { name: 'Twitter', accent: '#3d6bff', rounds: 4 },
                    { name: 'Reddit', accent: '#e5a60a', rounds: 4 },
                  ].map((lane) => (
                    <div
                      key={lane.name}
                      className="rounded-xl border p-4"
                      style={{ borderColor: `${lane.accent}22`, backgroundColor: `${lane.accent}05` }}
                    >
                      <span
                        className="font-mono text-[10px] tracking-[0.1em] uppercase block mb-3"
                        style={{ color: `${lane.accent}cc` }}
                      >
                        {lane.name}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {Array.from({ length: lane.rounds }).map((_, r) => (
                          <span
                            key={r}
                            className="h-1.5 flex-1 rounded-full"
                            style={{ backgroundColor: `${lane.accent}30` }}
                          />
                        ))}
                      </div>
                      <span className="mt-2 block font-mono text-[9px] tracking-wider uppercase text-text-tertiary">
                        Round progress
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </ScrollReveal>

        {/* Data relationships */}
        <ScrollReveal>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-3">
            {RELATIONSHIPS.map((r, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="font-mono text-[10px] tabular-nums text-accent-blue/60 mt-0.5">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <p className="text-[12.5px] leading-[1.6] text-text-secondary">{r}</p>
              </div>
            ))}
          </div>
        </ScrollReveal>
      </div>
    </section>
  )
}