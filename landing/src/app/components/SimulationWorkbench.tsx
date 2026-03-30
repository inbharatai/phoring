'use client'

import { useState, useRef, useCallback, type DragEvent, type ChangeEvent } from 'react'
import { ScrollReveal } from './ScrollReveal'

const ACCEPTED_EXTENSIONS = ['pdf', 'md', 'txt']
const MAX_FILE_SIZE_MB = 50
const MIN_PROMPT_LENGTH = 20
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
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
  const inputRef = useRef<HTMLInputElement>(null)

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
    setError(null)
    setSuccess(null)

    try {
      const formData = new FormData()
      formData.append('simulation_requirement', prompt.trim())
      formData.append('project_name', 'Landing Page Simulation')
      files.forEach((f) => formData.append('files', f.file))

      const res = await fetch(`${API_BASE}/api/graph/ontology/generate`, {
        method: 'POST',
        body: formData,
      })

      const json = await res.json()

      if (!res.ok || !json.success) {
        throw new Error(json.error || `Server error (${res.status})`)
      }

      const projectId = json.data?.project_id
      setSuccess(`Project created — redirecting to workspace…`)
      setFiles([])
      setPrompt('')

      // Redirect to the Vue frontend process page.
      // The MainView loadProject() detects status=ontology_generated
      // and auto-starts graph build — no workflow breakage.
      setTimeout(() => {
        window.location.href = `${APP_BASE}/process/${projectId}`
      }, 1200)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
    } finally {
      setLoading(false)
    }
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

            {/* ── Launch button ── */}
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
                {loading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
                      <path
                        d="M12 2a10 10 0 019.95 9"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                      />
                    </svg>
                    Initializing…
                  </>
                ) : (
                  'Start Simulation'
                )}
              </span>
              {canSubmit && !loading && (
                <span className="absolute inset-0 bg-gradient-to-r from-accent-blue via-[#4a78ff] to-accent-blue bg-[length:200%_100%] opacity-0 group-hover:opacity-100 group-hover:animate-[gradient-shift_2s_ease_infinite] transition-opacity duration-300" />
              )}
            </button>

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
