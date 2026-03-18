/**
 * Compatibility shim — delegates to the Pinia app store.
 * Existing imports (getPendingUpload, clearPendingUpload) continue to work.
 */
import { useAppStore } from '../stores/app'

export function setPendingUpload(files, requirement) {
  useAppStore().setPending(files, requirement)
}

export function getPendingUpload() {
  const store = useAppStore()
  return {
    files: store.pendingFiles,
    simulationRequirement: store.pendingRequirement,
    isPending: store.hasPending
  }
}

export function clearPendingUpload() {
  useAppStore().clearPending()
}

export default {
  get files() { return useAppStore().pendingFiles },
  get simulationRequirement() { return useAppStore().pendingRequirement },
  get isPending() { return useAppStore().hasPending }
}
