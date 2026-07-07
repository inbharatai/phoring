'use client'

import { ScrollReveal } from './ScrollReveal'

const TOOLS = [
  {
    name: 'Insight Forge',
    desc: 'Deep analysis across the knowledge graph — entities, relationships and patterns.',
    accent: '#3d6bff',
  },
  {
    name: 'Panorama Search',
    desc: 'Relationship and historical-context search for the full-picture view of a scenario.',
    accent: '#22d3ee',
  },
  {
    name: 'Quick Search',
    desc: 'Targeted retrieval of specific graph facts when a narrow lookup is enough.',
    accent: '#e5a60a',
  },
  {
    name: 'Agent Interviews',
    desc: 'Question selected simulated stakeholders and fold their reasoning into the report.',
    accent: '#10b981',
  },
  {
    name: 'Web & News Retrieval',
    desc: 'Pull fresh live evidence from Serper and Event Registry during the investigation.',
    accent: '#3d6bff',
  },
  {
    name: 'Geopolitical Context',
    desc: 'Load the configured disruption events and geopolitical backdrop shaping the scenario.',
    accent: '#22d3ee',
  },
]

export function ReportAgent() {
  return (
    <section className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient */}
      <div className="absolute top-[35%] left-[-3%] w-[400px] h-[350px] rounded-full bg-accent-blue/[0.015] blur-[120px] pointer-events-none" aria-hidden="true" />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-14 lg:mb-16">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              Report Agent
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              A Report Agent that investigates
              <br />
              <span className="text-text-secondary">before it concludes.</span>
            </h2>
            <p className="mt-6 text-sm sm:text-base leading-[1.7] text-text-secondary max-w-xl">
              Phoring&apos;s Report Agent does not summarise a single prompt. It iteratively
              searches the knowledge graph, inspects relationships, retrieves live evidence,
              interviews selected simulated stakeholders and evaluates competing explanations
              before producing the report.
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal>
          <div className="card p-6 lg:p-8">
            <div className="flex items-center gap-2.5 mb-6">
              <span className="w-1.5 h-1.5 rounded-full animate-signal bg-accent-blue" />
              <span className="font-mono text-[10px] tracking-[0.12em] uppercase text-text-tertiary">
                Six agentic tools · ReACT loop
              </span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border rounded-xl overflow-hidden">
              {TOOLS.map((tool, i) => (
                <div
                  key={tool.name}
                  className="bg-bg-elevated p-6 lg:p-7 group hover:bg-bg-surface transition-colors duration-400 relative"
                >
                  <span
                    className="absolute top-4 right-5 font-mono text-[11px] tabular-nums"
                    style={{ color: `${tool.accent}50` }}
                  >
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <h3
                    className="text-[14px] font-semibold tracking-[-0.01em] mb-2"
                    style={{ color: tool.accent }}
                  >
                    {tool.name}
                  </h3>
                  <p className="text-[12.5px] leading-[1.65] text-text-secondary">
                    {tool.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  )
}