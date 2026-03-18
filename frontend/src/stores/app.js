/**
 * Central Pinia store — replaces scattered reactive() state across components.
 * Provides: project/simulation/report data, global error/toast handling,
 * network status, and persistent session recovery via sessionStorage.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // ── Project ──────────────────────────────────────────────────────────────
  const projectId = ref(sessionStorage.getItem('phoring_project_id') || null)
  const graphId = ref(sessionStorage.getItem('phoring_graph_id') || null)
  const projectData = ref(null)

  function setProject(data) {
    projectData.value = data
    projectId.value = data?.project_id || null
    graphId.value = data?.graph_id || null
    if (projectId.value) sessionStorage.setItem('phoring_project_id', projectId.value)
    if (graphId.value)    sessionStorage.setItem('phoring_graph_id',   graphId.value)
  }

  // ── Simulation ───────────────────────────────────────────────────────────
  const simulationId = ref(sessionStorage.getItem('phoring_simulation_id') || null)

  function setSimulationId(id) {
    simulationId.value = id
    if (id) sessionStorage.setItem('phoring_simulation_id', id)
    else    sessionStorage.removeItem('phoring_simulation_id')
  }

  // ── Report ───────────────────────────────────────────────────────────────
  const reportId = ref(sessionStorage.getItem('phoring_report_id') || null)

  function setReportId(id) {
    reportId.value = id
    if (id) sessionStorage.setItem('phoring_report_id', id)
    else    sessionStorage.removeItem('phoring_report_id')
  }

  // ── Toasts / Errors ──────────────────────────────────────────────────────
  const toasts = ref([])  // [{ id, type, message, detail, dismissible }]
  let toastSeq = 0

  function addToast(type, message, detail = '', durationMs = 6000) {
    const id = ++toastSeq
    toasts.value.push({ id, type, message, detail, dismissible: true })
    if (durationMs > 0) {
      setTimeout(() => dismissToast(id), durationMs)
    }
    return id
  }

  function dismissToast(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  function clearToasts() { toasts.value = [] }

  const toast = {
    error:   (msg, detail = '') => addToast('error',   msg, detail, 8000),
    warn:    (msg, detail = '') => addToast('warn',    msg, detail, 5000),
    success: (msg, detail = '') => addToast('success', msg, detail, 4000),
    info:    (msg, detail = '') => addToast('info',    msg, detail, 4000),
  }

  // ── Network ──────────────────────────────────────────────────────────────
  const isOnline = ref(navigator.onLine)
  window.addEventListener('online',  () => { isOnline.value = true;  toast.success('Connection restored') })
  window.addEventListener('offline', () => { isOnline.value = false; toast.error('Connection lost — check your network', '', 0) })

  // ── Upload state (replaces pendingUpload.js) ─────────────────────────────
  const pendingFiles = ref([])
  const pendingRequirement = ref(sessionStorage.getItem('phoring_requirement') || '')

  function setPending(files, requirement) {
    pendingFiles.value = files
    pendingRequirement.value = requirement
    sessionStorage.setItem('phoring_requirement', requirement)
  }

  function clearPending() {
    pendingFiles.value = []
    pendingRequirement.value = ''
    sessionStorage.removeItem('phoring_requirement')
  }

  const hasPending = computed(() => pendingFiles.value.length > 0)

  // ── Reset (new simulation) ────────────────────────────────────────────────
  function resetSession() {
    projectId.value = null
    graphId.value = null
    projectData.value = null
    simulationId.value = null
    reportId.value = null
    clearPending()
    clearToasts()
    ;['phoring_project_id','phoring_graph_id','phoring_simulation_id','phoring_report_id','phoring_requirement']
      .forEach(k => sessionStorage.removeItem(k))
  }

  return {
    // project
    projectId, graphId, projectData, setProject,
    // simulation
    simulationId, setSimulationId,
    // report
    reportId, setReportId,
    // toasts
    toasts, toast, dismissToast, clearToasts,
    // network
    isOnline,
    // pending upload
    pendingFiles, pendingRequirement, hasPending, setPending, clearPending,
    // reset
    resetSession,
  }
})
