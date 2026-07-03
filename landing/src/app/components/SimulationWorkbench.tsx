'use client'

import { useState, useRef, useCallback, useEffect, type DragEvent, type ChangeEvent } from 'react'
import { ScrollReveal } from './ScrollReveal'

const ACCEPTED_EXTENSIONS = ['pdf', 'md', 'txt']
const MAX_FILE_SIZE_MB = 50
const MIN_PROMPT_LENGTH = 20
const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''
const APP_BASE = process.env.NEXT_PUBLIC_APP_URL || '/app'

interface FileEntry {
  file: File
  name: string
  sizeMB: number
}

export function SimulationWorkbench() {
  const [files, setFiles] = useState<FileEntry[]>([])
  const [prompt, setPrompt] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  /* ── Validation ── */
  const promptTooShort = prompt.trim().length > 0 && prompt.trim().length < MIN_PROMPT_LENGTH
  const oversizedFiles = files.filter((f) => f.sizeMB > MAX_FILE_SIZE_MB)
  const canSubmit =
    files.length > 0 &&
    prompt.trim().length >= MIN_PROMPT_LENGTH &&
    oversizedFiles.length === 0 &&
    !loading

  /* ── File helpers ── */
  const addFiles = useCallback((incoming: File[]) => {
    const accepted = incoming.filter((f) => {
      const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
      return ACCEPTED_EXTENSIONS.includes(ext)
    })

    setFiles((prev) => {
      const existingNames = new Set(prev.map((e) => e.name))
      const fresh = accepted
        .filter((f) => !existingNames.has(f.name))
        .map((f) => ({
          file: f,
          name: f.name,
          sizeMB: f.size / (1024 * 1024),
        }))
      return [...prev, ...fresh]
    })
  }, [])

  const removeFile = (name: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== name))
  }

  /* ── Drag / Drop ── */
  const onDragOver = (e: DragEvent) => {
    e.preventDefault()
    if (!loading) setDragOver(true)
  }
  const onDragLeave = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }
  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (loading) return
    addFiles(Array.from(e.dataTransfer.files))
  }
  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(Array.from(e.target.files))
    e.target.value = ''
  }

  /* ── Submit ── */
  const handleLaunch = async () => {
    if (!canSubmit) return
    setLoading(true)
    setDone(false)
    setError(null)
    setSuccess(null)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const formData = new FormData()
      formData.append('simulation_requirement', prompt.trim())
      formData.append('project_name', 'Landing Page Simulation')
      files.forEach((f) => formData.append('files', f.file))

      const res = await fetch(`${API_BASE}/api/graph/ontology/generate`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })

      const json = await res.json()

      if (!res.ok || !json.success) {
        throw new Error(json.error || `Server error (${res.status})`)
      }

      const projectId = json.data?.project_id
      setFiles([])
      setPrompt('')
      setDone(true) // ring snaps to 100% + "Opening workspace…"

      // Redirect to the Vue frontend process page.
      // The MainView loadProject() detects status=ontology_generated
      // and auto-starts graph build — no workflow breakage.
      setTimeout(() => {
        window.location.href = `${APP_BASE}/process/${projectId}`
      }, 1200)
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  /* ── Cancel an in-flight submit (abort fetch, reset to the form) ── */
  const handleCancel = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setLoading(false)
    setDone(false)
    setSuccess(null)
    setError(null)
  }

  return (
    <section id="start" className="relative py-28 lg:py-40">
      <div className="absolute top-0 inset-x-0 section-divider" />

      {/* Ambient glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-accent-blue/[0.03] blur-[140px] rounded-full pointer-events-none"
        aria-hidden="true"
      />

      <div className="container-lg relative z-10 max-w-2xl mx-auto">
        <ScrollReveal>
          <div className="text-center mb-12">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-blue/70 block mb-4">
              New Simulation
            </span>
            <h2 className="text-[1.75rem] sm:text-[2.25rem] lg:text-[2.75rem] font-bold tracking-[-0.03em] leading-[1.08] text-text-primary mb-4">
              Upload documents,
              <br />
              <span className="text-gradient">define your scenario.</span>
            </h2>
            <p className="text-base text-text-secondary leading-relaxed max-w-md mx-auto">
              Drop your source files and describe the scenario you want to simulate.
              Phoring handles the rest.
            </p>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={0.1}>
          <div className="card p-6 sm:p-8 lg:p-10">
            {/* ── Dropzone ── */}
            <div
              role="button"
              tabIndex={0}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              onClick={() => !loading && inputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  if (!loading) inputRef.current?.click()
                }
              }}
              className={`
                relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed
                transition-all duration-300 cursor-pointer min-h-[160px] mb-8
                ${
                  dragOver
                    ? 'border-accent-blue/60 bg-accent-blue/[0.06] shadow-[0_0_40px_rgba(61,107,255,0.08)]'
                    : files.length > 0
                      ? 'border-accent-emerald/30 bg-accent-emerald/[0.02]'
                      : 'border-border hover:border-border-hover hover:bg-bg-surface/40'
                }
                ${loading ? 'opacity-50 pointer-events-none' : ''}
              `}
            >
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".pdf,.md,.txt"
                onChange={onFileChange}
                className="hidden"
                disabled={loading}
              />

              {files.length === 0 ? (
                <div className="text-center py-10 px-6">
                  {/* Upload icon */}
                  <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-bg-surface border border-border flex items-center justify-center">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-text-tertiary">
                      <path
                        d="M12 15V3m0 0L8 7m4-4l4 4"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-text-secondary mb-1">
                    Drop files here or click to browse
                  </p>
                  <p className="text-[11px] font-mono text-text-tertiary tracking-wider">
                    PDF · MD · TXT — up to {MAX_FILE_SIZE_MB} MB
                  </p>
                </div>
              ) : (
                <div className="w-full p-4 space-y-2">
                  {files.map((f) => (
                    <div
                      key={f.name}
                      className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-lg bg-bg-surface/60 border border-border/50 group"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-7 h-7 rounded-md bg-accent-blue/10 border border-accent-blue/15 flex items-center justify-center flex-shrink-0">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-accent-blue/70">
                            <path
                              d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
                              stroke="currentColor"
                              strokeWidth="1.5"
                              strokeLinejoin="round"
                            />
                            <path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                          </svg>
                        </div>
                        <span className="text-[13px] text-text-primary truncate">{f.name}</span>
                        <span className="text-[10px] font-mono text-text-tertiary flex-shrink-0">
                          {f.sizeMB < 1
                            ? `${(f.sizeMB * 1024).toFixed(0)} KB`
                            : `${f.sizeMB.toFixed(1)} MB`}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          removeFile(f.name)
                        }}
                        className="text-[10px] font-mono uppercase tracking-wider text-text-tertiary hover:text-red-400 transition-colors duration-200 flex-shrink-0"
                        aria-label={`Remove ${f.name}`}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <p className="text-center text-[10px] font-mono text-text-tertiary mt-2 tracking-wider">
                    Click to add more files
                  </p>
                </div>
              )}
            </div>

            {/* ── Scenario Prompt ── */}
            <label
              htmlFor="scenario-prompt"
              className="block font-mono text-[11px] uppercase tracking-[0.12em] text-text-tertiary mb-3"
            >
              Scenario Prompt
            </label>
            <textarea
              id="scenario-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Example: Simulate the public reaction to a university policy announcement over 72 hours."
              rows={5}
              disabled={loading}
              className={`
                w-full bg-bg-surface border rounded-xl px-5 py-4
                text-sm text-text-primary placeholder:text-text-tertiary/50
                resize-none transition-all duration-300
                focus:outline-none focus:border-accent-blue/40 focus:shadow-[0_0_30px_rgba(61,107,255,0.06)]
                ${promptTooShort ? 'border-amber-500/40' : 'border-border hover:border-border-hover'}
                ${loading ? 'opacity-50' : ''}
              `}
            />
            {promptTooShort && (
              <p className="mt-2 text-[11px] font-mono text-amber-500/80">
                Please describe your scenario in at least {MIN_PROMPT_LENGTH} characters.
              </p>
            )}

            {/* ── Validation / status messages ── */}
            {oversizedFiles.length > 0 && (
              <div className="mt-3">
                {oversizedFiles.map((f) => (
                  <p key={f.name} className="text-[11px] font-mono text-red-400/80">
                    &ldquo;{f.name}&rdquo; exceeds the {MAX_FILE_SIZE_MB} MB limit.
                  </p>
                ))}
              </div>
            )}

            {error && (
              <div className="mt-4 px-4 py-3 rounded-lg bg-red-500/[0.06] border border-red-500/20">
                <p className="text-[12px] text-red-400">{error}</p>
              </div>
            )}

            {success && (
              <div className="mt-4 px-4 py-3 rounded-lg bg-accent-emerald/[0.06] border border-accent-emerald/20">
                <p className="text-[12px] text-accent-emerald">{success}</p>
              </div>
            )}

            {/* ── Launch / progress ── */}
            {loading || done ? (
              <div className="mt-8">
                <ScenarioProgress done={done} onCancel={handleCancel} />
              </div>
            ) : (
              <button
                type="button"
                onClick={handleLaunch}
                disabled={!canSubmit}
                className={`
                  group relative w-full mt-8 px-8 py-4 text-[15px] font-semibold rounded-xl
                  overflow-hidden transition-all duration-300
                  ${
                    canSubmit
                      ? 'bg-accent-blue text-white hover:shadow-[0_0_60px_rgba(61,107,255,0.3)] hover:scale-[1.01] active:scale-[0.99] cursor-pointer'
                      : 'bg-bg-surface text-text-tertiary border border-border cursor-not-allowed'
                  }
                `}
              >
                <span className="relative z-10 flex items-center justify-center gap-2">
                  Start Simulation
                </span>
                {canSubmit && (
                  <span className="absolute inset-0 bg-gradient-to-r from-accent-blue via-[#4a78ff] to-accent-blue bg-[length:200%_100%] opacity-0 group-hover:opacity-100 group-hover:animate-[gradient-shift_2s_ease_infinite] transition-opacity duration-300" />
                )}
              </button>
            )}

            {/* ── Subtle help text ── */}
            <div className="mt-6 flex items-center justify-center gap-4 flex-wrap">
              {['Source-Cited Reports', 'Knowledge Graph', 'OASIS Simulation'].map((badge) => (
                <span
                  key={badge}
                  className="font-mono text-[9px] tracking-[0.1em] uppercase text-text-tertiary/50 px-3 py-1 border border-border/40 rounded-full"
                >
                  {badge}
                </span>
              ))}
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  )
}

/* ───────────────────────────────────────────────────────────────────────────
   ScenarioProgress — on-brand "building your scenario" panel.
   Estimated-progress ring (caps at 90% while pending, snaps to 100% on `done`)
   + a live knowledge-graph motif that lights up as the ring fills + rotating
   stage labels + an elapsed mm:ss timer + an honest "2–3 min" estimate + a
   Cancel affordance. Pure frontend — consumes no backend progress signal, so
   it can never lie about completion (never hits 100% before the server returns).
   ─────────────────────────────────────────────────────────────────────────── */
const ESTIMATE_SECONDS = 150

function ScenarioProgress({ done, onCancel }: { done: boolean; onCancel: () => void }) {
  const [progress, setProgress] = useState(0)
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (done) return
    const start = performance.now()
    const id = window.setInterval(() => {
      const el = (performance.now() - start) / 1000
      setElapsed(el)
      setProgress(Math.min(el / ESTIMATE_SECONDS, 1) * 90) // cap at 90% while pending
    }, 200)
    return () => window.clearInterval(id)
  }, [done])

  useEffect(() => {
    if (done) setProgress(100) // snap to 100% on success — "Opening workspace…"
  }, [done])

  const shownPct = done ? 100 : Math.min(progress, 90)
  const mm = Math.floor(elapsed / 60).toString().padStart(2, '0')
  const ss = Math.floor(elapsed % 60).toString().padStart(2, '0')

  const stage = done
    ? 'Opening workspace…'
    : shownPct >= 90
      ? 'Finalizing — almost there'
      : shownPct >= 70
        ? 'Generating scenario ontology'
        : shownPct >= 45
          ? 'Mapping relationships'
          : shownPct >= 20
            ? 'Extracting entities'
            : 'Parsing document'

  // Knowledge-graph motif: 6 nodes around a circle; more activate as pct grows.
  const RADIUS = 46
  const NODES = Array.from({ length: 6 }, (_, i) => {
    const ang = (-90 + i * 60) * (Math.PI / 180)
    return { x: 100 + RADIUS * Math.cos(ang), y: 100 + RADIUS * Math.sin(ang) }
  })
  const EDGES: [number, number][] = [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], // hexagon perimeter
    [0, 3], [1, 4], // cross-links
  ]
  const activeCount = Math.ceil((shownPct / 90) * NODES.length)
  const nodeActive = (i: number) => i < activeCount
  const edgeActive = (a: number, b: number) => nodeActive(a) && nodeActive(b)
  const CIRC = 2 * Math.PI * 88
  const dashOffset = CIRC * (1 - shownPct / 100)

  return (
    <div className="flex flex-col items-center text-center">
      <div className="relative w-[180px] h-[180px]">
        <svg viewBox="0 0 200 200" className="w-full h-full">
          {/* slowly-rotating dashed accent ring */}
          <circle
            cx="100"
            cy="100"
            r="94"
            fill="none"
            stroke="rgba(61,107,255,0.18)"
            strokeWidth="1"
            strokeDasharray="2 6"
            style={{ animation: 'ring-rotate 12s linear infinite', transformOrigin: '100px 100px' }}
          />
          {/* track */}
          <circle cx="100" cy="100" r="88" fill="none" stroke="#1a1a28" strokeWidth="6" />
          {/* progress arc */}
          <circle
            cx="100"
            cy="100"
            r="88"
            fill="none"
            stroke="#3d6bff"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={dashOffset}
            style={{
              transform: 'rotate(-90deg)',
              transformOrigin: '100px 100px',
              transition: 'stroke-dashoffset 0.4s ease-out',
              filter: 'drop-shadow(0 0 6px rgba(61,107,255,0.45))',
            }}
          />
          {/* knowledge-graph edges */}
          {EDGES.map(([a, b], i) => (
            <line
              key={`e${i}`}
              x1={NODES[a].x}
              y1={NODES[a].y}
              x2={NODES[b].x}
              y2={NODES[b].y}
              stroke="rgba(34,211,238,0.5)"
              strokeWidth="1"
              strokeLinecap="round"
              style={{ opacity: edgeActive(a, b) ? 1 : 0, transition: 'opacity 0.5s ease' }}
            />
          ))}
          {/* knowledge-graph nodes */}
          {NODES.map((n, i) => (
            <circle
              key={`n${i}`}
              cx={n.x}
              cy={n.y}
              r="4"
              fill={nodeActive(i) ? '#22d3ee' : 'rgba(74,74,96,0.5)'}
              style={{
                opacity: nodeActive(i) ? 1 : 0.25,
                transition: 'opacity 0.5s ease, fill 0.5s ease',
                filter: nodeActive(i) ? 'drop-shadow(0 0 4px rgba(34,211,238,0.6))' : 'none',
              }}
            />
          ))}
        </svg>
        {/* center readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold tabular-nums text-text-primary">
            {Math.round(shownPct)}%
          </span>
          <span className="font-mono text-[10px] text-text-tertiary tabular-nums mt-0.5">
            {mm}:{ss}
          </span>
        </div>
      </div>

      <p className="mt-5 text-sm font-medium text-text-primary">{stage}</p>
      <p className="mt-1.5 font-mono text-[10px] tracking-wider uppercase text-text-tertiary">
        {done ? 'Redirecting to workspace' : 'This usually takes 2–3 minutes'}
      </p>

      {!done && (
        <button
          type="button"
          onClick={onCancel}
          className="mt-5 font-mono text-[10px] uppercase tracking-wider text-text-tertiary hover:text-text-secondary transition-colors duration-200"
        >
          Cancel
        </button>
      )}
    </div>
  )
}
