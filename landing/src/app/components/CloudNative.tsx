'use client'

import { ScrollReveal } from './ScrollReveal'

const CLOUD_BADGES = [
  'Google Kubernetes Engine',
  'Gemini API',
  'Cloud Build',
  'Artifact Registry',
  'Cloud Storage',
  'BigQuery',
  'Workload Identity',
  'Docker',
]

const CORE_BADGES = [
  'OASIS',
  'CAMEL-AI',
  'Zep Cloud',
  'Serper',
  'Event Registry',
  'Vue',
  'Flask',
]

const LINKS = [
  { name: 'Repository', href: 'https://github.com/inbharatai/phoring' },
  { name: 'README', href: 'https://github.com/inbharatai/phoring#readme' },
  { name: 'License', href: 'https://github.com/inbharatai/phoring/blob/main/LICENSE' },
  { name: 'Cloud Architecture', href: 'https://github.com/inbharatai/phoring/blob/main/docs/google-cloud-architecture.md' },
]

function BadgeRow({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      {items.map((name) => (
        <span
          key={name}
          className="font-mono text-[11px] bg-bg-surface border border-border rounded-md px-3 py-1.5 tracking-wide hover:border-border-hover transition-colors duration-300 text-text-secondary"
        >
          {name}
        </span>
      ))}
    </div>
  )
}

export function CloudNative() {
  return (
    <section className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient */}
      <div className="absolute top-[30%] right-[-4%] w-[400px] h-[300px] rounded-full bg-accent-cyan/[0.015] blur-[120px] pointer-events-none" aria-hidden="true" />

      <div className="container-lg">
        <ScrollReveal>
          <div className="max-w-2xl mb-14 lg:mb-16">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              Cloud &amp; Open Source
            </span>
            <h2 className="text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem] font-semibold tracking-[-0.025em] leading-[1.15] text-text-primary">
              Cloud-native, observable
              <br />
              <span className="text-text-secondary">and portable.</span>
            </h2>
            <p className="mt-6 text-sm sm:text-base leading-[1.7] text-text-secondary max-w-xl">
              Phoring runs as a containerised frontend and backend on Google Kubernetes
              Engine Autopilot. Cloud Build and Artifact Registry support deployment, Cloud
              Storage can mirror uploaded documents and generated artefacts, and BigQuery can
              capture simulation, agent-event, evaluation and feedback telemetry. Workload
              Identity allows Google Cloud access without embedded service-account key files.
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal>
          <div className="card p-6 lg:p-8 mb-6">
            <div className="mb-6">
              <span className="font-mono text-[10px] tracking-[0.12em] uppercase text-text-tertiary block mb-3">
                Google Cloud
              </span>
              <BadgeRow items={CLOUD_BADGES} />
            </div>
            <div className="mb-6">
              <span className="font-mono text-[10px] tracking-[0.12em] uppercase text-text-tertiary block mb-3">
                Core stack
              </span>
              <BadgeRow items={CORE_BADGES} />
            </div>

            {/* Honest qualifications + model statement */}
            <div className="grid sm:grid-cols-2 gap-4 pt-6 border-t border-border/60">
              <div>
                <p className="font-mono text-[10px] tracking-[0.1em] uppercase text-accent-cyan/70 mb-1.5">
                  Configuration-gated
                </p>
                <p className="text-[12.5px] leading-[1.65] text-text-secondary">
                  Cloud Storage and BigQuery are optional and default off — local deployment
                  needs neither. BigQuery is append-only telemetry, not a relational database or
                  BI layer. Local storage remains the primary working store.
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] tracking-[0.1em] uppercase text-accent-cyan/70 mb-1.5">
                  Models
                </p>
                <p className="text-[12.5px] leading-[1.65] text-text-secondary">
                  OpenAI SDK-compatible model endpoints, with Gemini used as the primary live
                  reasoning model and optional independent validators. Gemini is accessed
                  through the Gemini API — not Vertex AI, Looker or Managed Spark.
                </p>
              </div>
            </div>
          </div>
        </ScrollReveal>

        {/* Open-source deployment positioning */}
        <ScrollReveal>
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div className="max-w-md">
              <p className="text-[15px] font-medium text-text-primary mb-2">
                Open-source, Docker-ready and deployable locally or on Google Cloud.
              </p>
              <p className="text-[13px] leading-[1.65] text-text-secondary">
                Run Phoring in a trusted local environment or deploy the containerised
                application through the documented cloud architecture.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              {LINKS.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[11px] tracking-wider uppercase px-4 py-2.5 border border-border rounded-lg text-text-secondary hover:text-text-primary hover:border-border-hover hover:bg-bg-elevated/50 transition-all duration-300"
                >
                  {link.name}
                </a>
              ))}
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  )
}