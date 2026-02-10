/**
 * Composable for polling data at a fixed interval with automatic cleanup.
 */
import { onMounted, onUnmounted, ref } from 'vue'

export function usePolling(callback: () => Promise<void>, intervalMs = 1500) {
  let timer: ReturnType<typeof setInterval> | null = null
  const active = ref(false)

  function start() {
    if (timer) return
    active.value = true
    timer = setInterval(callback, intervalMs)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    active.value = false
  }

  onMounted(async () => {
    await callback()
    start()
  })

  onUnmounted(stop)

  return { active, start, stop }
}
