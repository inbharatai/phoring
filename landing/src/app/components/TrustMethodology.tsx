'use client'

import { ScrollReveal } from './ScrollReveal'

const METHODOLOGY = [
  {
    label: 'KNOWLEDGE GRAPH',
    num: '01',
    accent: '#3d6bff',
    detail:
      'LLM-driven ontology generation extracts entities, relationships and domain structure before storing a queryable scenario graph in Zep.',
  },
  {
    label: 'WEB INTELLIGENCE',
    num: '02',
    accent: '#22d3ee',
    detail:
      'Serper and Event Registry provide current web and news context. Public social signals are retrieved through search indexing rather than direct platform APIs.',
  },
  {
    label: 'BEHAVIOURAL AGENTS',
    num: '03',
    accent: '#e5a60a',
    detail:
      'Scenario entities are converted into simulated stakeholders with roles, stances, interests, influence levels and behavioural parameters.',
  },
  {
    label: 'PARALLEL SIMULATION',
    num: '04',
    accent: '#10b981',
    detail:
      'OASIS runs synthetic Twitter and Reddit environments concurrently and records platform-specific agent activity, reactions and narrative movement.',
  },
  {
    label: 'AGENTIC INVESTIGATION',
    num: '05',
    accent: '#3d6bff',
    detail:
      'The Report Agent iteratively searches graph evidence, simulation data and live context rather than relying on one generation call.',
  },
  {
    label: 'AGENT INTERVIEWS',
    num: '06',
    accent: '#22d3ee',
    detail:
      'Selected simulated stakeholders can be questioned to expose likely motivations, concerns and reactions.',
  },
  {
    label: 'CONFIDENCE SCORING',
    num: '07',
    accent: '#e5a60a',
    detail:
      'Report sections receive HIGH, MEDIUM or LOW labels based on evidence density and quality — not certainty.',
  },
  {
    label: 'CONSENSUS VALIDATION',
    num: '08',
    accent: '#10b981',
    detail:
      'Optional independent validators assess coherence, historical precedent, completeness and risk coverage.',
  },
  {
    label: 'REPORT Q&A',
    num: '09',
    accent: '#3d6bff',
    detail:
      'Follow-up questions are answered using report context, graph tools, simulation evidence and fresh intelligence.',
  },
]

const TECH_STACK = [
  { name: 'OASIS', accent: '#e5a60a' },
  { name: 'CAMEL-AI', accent: '#3d6bff' },
  { name: 'Zep Cloud', accent: '#22d3ee' },
  { name: 'Serper', accent: '#10b981' },
  { name: 'Event Registry', accent: '#e5a60a' },
  { name: 'Gemini API', accent: '#3d6bff' },
  { name: 'Google Cloud', accent: '#22d3ee' },
  { name: 'Vue', accent: '#10b981' },
  { name: 'Flask', accent: '#e5a60a' },
]

export function TrustMethodology() {
  return (
    <section id="methodology" className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient */}
      <div className="absolute top-[40%] left-[-3%] w-[350px] h-[350px] rounded-full bg-accent-blue/[0.015] blur-[120px] pointer-events-none" aria-hidden="true" />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-16 lg:mb-20">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              Methodology
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              Transparent by design.
              <br />
              <span className="text-text-secondary">
                Every step is auditable.
              </span>
            </h2>
          </div>
        </ScrollReveal>

        {/* Methodology grid */}
        <ScrollReveal>
          <div className="card overflow-hidden p-0">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border">
              {METHODOLOGY.map((item) => (
                <div
                  key={item.label}
                  className="bg-bg-elevated p-7 lg:p-8 group hover:bg-bg-surface transition-colors duration-400 relative overflow-hidden"
                >
                  {/* Step number watermark */}
                  <span
                    className="absolute top-3 right-4 font-mono text-[40px] font-bold leading-none opacity-[0.03] group-hover:opacity-[0.06] transition-opacity duration-500 select-none"
                    style={{ color: item.accent }}
                  >
                    {item.num}
                  </span>

                  <div className="flex items-center gap-2.5 mb-3.5">
                    <div
                      className="w-1.5 h-1.5 rounded-full animate-signal"
                      style={{ backgroundColor: item.accent }}
                    />
                    <span
                      className="font-mono text-[10px] tracking-[0.12em] transition-colors duration-300"
                      style={{ color: `${item.accent}80` }}
                    >
                      {item.label}
                    </span>
                  </div>

                  <p className="text-[13px] leading-[1.7] text-text-secondary group-hover:text-text-secondary/90 transition-colors duration-300">
                    {item.detail}
                  </p>

                  {/* Bottom accent on hover */}
                  <div
                    className="absolute bottom-0 left-6 right-6 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                    style={{
                      background: `linear-gradient(90deg, transparent, ${item.accent}20, transparent)`,
                    }}
                  />
                </div>
              ))}
            </div>

            {/* Tech stack strip */}
            <div className="bg-bg-elevated border-t border-border px-7 lg:px-8 py-5 flex flex-wrap items-center gap-3">
              <span className="font-mono text-[10px] tracking-[0.1em] uppercase text-text-tertiary mr-1">
                Built on
              </span>
              {TECH_STACK.map((tech) => (
                <span
                  key={tech.name}
                  className="font-mono text-[11px] bg-bg-surface border border-border rounded-md px-3 py-1.5 tracking-wide hover:border-border-hover transition-colors duration-300"
                  style={{ color: `${tech.accent}90` }}
                >
                  {tech.name}
                </span>
              ))}
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  )
}
