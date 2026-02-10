/**
 * Lightweight notification system — custom toasts matching the WebMACS design system.
 * No dependency on PrimeVue Toast (which requires theme presets to render correctly).
 */

import { ref, type Ref } from 'vue'

export type Severity = 'success' | 'info' | 'warn' | 'error'

export interface Notification {
  id: number
  severity: Severity
  summary: string
  detail?: string
  life: number
}

let nextId = 0
const notifications: Ref<Notification[]> = ref([])

function addNotification(severity: Severity, summary: string, detail?: string, life = 3500) {
  const id = nextId++
  notifications.value.push({ id, severity, summary, detail, life })
  setTimeout(() => removeNotification(id), life)
}

function removeNotification(id: number) {
  notifications.value = notifications.value.filter((n) => n.id !== id)
}

export function useNotifications(): { notifications: Ref<Notification[]>; remove: (id: number) => void } {
  return { notifications, remove: removeNotification }
}

export function useNotification() {
  const success = (msg: string, detail?: string) => addNotification('success', msg, detail)
  const info = (msg: string, detail?: string) => addNotification('info', msg, detail)
  const warn = (msg: string, detail?: string) => addNotification('warn', msg, detail)
  const error = (msg: string, detail?: string) => addNotification('error', msg, detail, 5000)

  return { success, info, warn, error }
}
