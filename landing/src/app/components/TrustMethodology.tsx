'use client'

import { ScrollReveal } from './ScrollReveal'

const METHODOLOGY = [
  {
    label: 'KNOWLEDGE GRAPH',
    num: '01',
    accent: '#3d6bff',
    detail:
      'LLM-driven ontology extraction → entity and relationship mapping → Zep Cloud storage → downstream querying for agent profiles, simulation context, and report generation.',
  },
  {
    label: 'WEB ENRICHMENT',
    num: '02',
    accent: '#22d3ee',
    detail:
      'Entity-scoped queries via Serper and NewsAPI. Articles scraped and processed up to 4,000 characters each. Social content sourced via Google Search indexing.',
  },
  {
    label: 'SIMULATION ENGINE',
    num: '03',
    accent: '#e5a60a',
    detail:
      'OASIS framework spawns synthetic environments where LLM-generated agents interact based on assigned personas, stances, and behavioral parameters. Results stream in real time.',
  },
  {
    label: 'REPORT GENERATION',
    num: '04',
    accent: '#10b981',
    detail:
      'ReACT loop pulls from knowledge graph, web intelligence, and simulation data. Claims are backed by inline numbered references with a full sources section.',
  },
  {
    label: 'CONFIDENCE SCORING',
    num: '05',
    accent: '#3d6bff',
    detail:
      'Each report section tagged [HIGH], [MEDIUM], or [LOW] based on independent tool-sourced data points. Reflects evidence density — not a guarantee of accuracy.',
  },
  {
    label: 'CONSENSUS VALIDATION',
    num: '06',
    accent: '#22d3ee',
    detail:
      'Optional. Up to 3 independent LLM validators score predictions on coherence, precedent, and risk. A consensus summary is appended to the final report.',
  },
]

const TECH_STACK = [
  { name: 'OASIS', accent: '#e5a60a' },
  { name: 'CAMEL AI', accent: '#3d6bff' },
  { name: 'Zep Cloud', accent: '#22d3ee' },
  { name: 'Serper', accent: '#10b981' },
  { name: 'NewsAPI', accent: '#e5a60a' },
  { name: 'OpenAI', accent: '#3d6bff' },
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
