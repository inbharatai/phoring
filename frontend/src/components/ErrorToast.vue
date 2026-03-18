<template>
  <!-- Toast stack — bottom-right, stacks vertically -->
  <Teleport to="body">
    <div class="toast-container" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast-slide">
        <div
          v-for="t in store.toasts"
          :key="t.id"
          class="toast"
          :class="`toast--${t.type}`"
          role="alert"
        >
          <div class="toast-icon">
            <svg v-if="t.type === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <svg v-else-if="t.type === 'warn'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <svg v-else-if="t.type === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div class="toast-body">
            <span class="toast-msg">{{ t.message }}</span>
            <span v-if="t.detail" class="toast-detail">{{ t.detail }}</span>
          </div>
          <button v-if="t.dismissible" class="toast-close" @click="store.dismissToast(t.id)" aria-label="Dismiss">×</button>
        </div>
      </TransitionGroup>
    </div>

    <!-- Offline banner -->
    <Transition name="banner-slide">
      <div v-if="!store.isOnline" class="offline-banner" role="status">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="1" y1="1" x2="23" y2="23"/><path d="M16.72 11.06A10.94 10.94 0 0119 12.55"/><path d="M5 12.55a10.94 10.94 0 015.17-2.39"/><path d="M10.71 5.05A16 16 0 0122.56 9"/><path d="M1.42 9a15.91 15.91 0 014.7-2.88"/><path d="M8.53 16.11a6 6 0 016.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>
        You are offline — backend unreachable
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()

// Listen for API errors emitted by the axios interceptor
function onApiError(e) {
  store.toast.error(e.detail?.message || 'An error occurred')
}
// Listen for vue global errors
function onPhoringError(e) {
  store.toast.error(e.detail?.message || 'Unexpected error', e.detail?.info || '')
}

onMounted(() => {
  window.addEventListener('phoring:api-error', onApiError)
  window.addEventListener('phoring:error', onPhoringError)
})
onUnmounted(() => {
  window.removeEventListener('phoring:api-error', onApiError)
  window.removeEventListener('phoring:error', onPhoringError)
})
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column-reverse;
  gap: 10px;
  max-width: 420px;
  width: calc(100vw - 48px);
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #1a1a2e;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 8px 32px rgba(0,0,0,0.35);
  pointer-events: all;
  font-size: 13px;
  line-height: 1.4;
}

.toast--error   { border-left: 3px solid #ef4444; }
.toast--warn    { border-left: 3px solid #f59e0b; }
.toast--success { border-left: 3px solid #22c55e; }
.toast--info    { border-left: 3px solid #3b82f6; }

.toast-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  margin-top: 1px;
}

.toast--error   .toast-icon { color: #ef4444; }
.toast--warn    .toast-icon { color: #f59e0b; }
.toast--success .toast-icon { color: #22c55e; }
.toast--info    .toast-icon { color: #3b82f6; }

.toast-icon svg { width: 18px; height: 18px; }

.toast-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toast-msg {
  color: #f1f5f9;
  font-weight: 500;
  word-break: break-word;
}

.toast-detail {
  color: #94a3b8;
  font-size: 12px;
  word-break: break-word;
}

.toast-close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: #64748b;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.15s;
}
.toast-close:hover { color: #f1f5f9; }

/* Offline banner */
.offline-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10000;
  background: #b91c1c;
  color: #fff;
  text-align: center;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

/* Animations */
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.toast-slide-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.banner-slide-enter-active,
.banner-slide-leave-active {
  transition: transform 0.3s ease;
}
.banner-slide-enter-from,
.banner-slide-leave-to {
  transform: translateY(-100%);
}
</style>
