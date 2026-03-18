import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Global error handler — catches unhandled promise rejections and Vue errors
app.config.errorHandler = (err, instance, info) => {
  console.error('[Global Error]', err, info)
  // Dispatch custom event picked up by ErrorToast in App.vue
  window.dispatchEvent(new CustomEvent('phoring:error', {
    detail: { message: err?.message || String(err), info }
  }))
}

window.addEventListener('unhandledrejection', (event) => {
  const msg = event.reason?.message || String(event.reason)
  window.dispatchEvent(new CustomEvent('phoring:error', { detail: { message: msg } }))
})

app.mount('#app')
