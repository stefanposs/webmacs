/**
 * Composable for real-time datapoint streaming.
 *
 * Strategy: WebSocket-first with automatic HTTP polling fallback.
 *
 * 1. Tries to connect to /ws/datapoints/stream
 * 2. If WebSocket fails to connect after 3 attempts, falls back to HTTP polling
 * 3. If WebSocket reconnects later, stops polling and switches back
 *
 * Features:
 * - Configurable UI throttle interval (default 1000ms) prevents visual flicker
 * - Pause/resume capability for inspecting current values
 * - While paused, only the latest value per event is kept in the buffer — resume shows the most recent state
 *
 * Usage:
 *   const { latestDatapoints, connectionMode, isConnected, isPaused, togglePause, throttleMs, setThrottleMs } = useRealtimeDatapoints()
 */

import { onMounted, onUnmounted, ref, type Ref } from 'vue'
import { WebSocketClient } from '@/services/websocket'
import api from '@/services/api'
import type { Datapoint } from '@/types'

export type ConnectionMode = 'websocket' | 'polling' | 'connecting'

export interface RealtimeDatapointsReturn {
  latestDatapoints: Ref<Datapoint[]>
  connectionMode: Ref<ConnectionMode>
  isConnected: Ref<boolean>
  /** Whether UI updates are paused (data is still collected in the background) */
  isPaused: Ref<boolean>
  /** Toggle pause on/off */
  togglePause: () => void
  /** Current throttle interval in ms */
  throttleMs: Ref<number>
  /** Change the throttle interval at runtime */
  setThrottleMs: (ms: number) => void
}

export function useRealtimeDatapoints(
  pollIntervalMs = 1500,
  defaultThrottleMs = 1000,
): RealtimeDatapointsReturn {
  const latestDatapoints = ref<Datapoint[]>([])
  const connectionMode = ref<ConnectionMode>('connecting')
  const isConnected = ref(false)
  const isPaused = ref(false)
  const throttleMs = ref(defaultThrottleMs)

  let wsClient: WebSocketClient | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let wsFailCount = 0
  const WS_MAX_FAILS = 3

  // ─── Throttle buffer ─────────────────────────────────────────────
  // Incoming data is merged into this buffer immediately.
  // The buffer is flushed to `latestDatapoints` at most once per `throttleMs`.
  let buffer = new Map<string, Datapoint>()
  let flushTimer: ReturnType<typeof setTimeout> | null = null
  let lastFlushTime = 0

  function flushBuffer() {
    flushTimer = null
    if (isPaused.value) return
    if (buffer.size === 0) return
    // Merge buffer into current visible data
    const map = new Map<string, Datapoint>()
    for (const dp of latestDatapoints.value) {
      map.set(dp.event_public_id, dp)
    }
    for (const [key, dp] of buffer) {
      map.set(key, dp)
    }
    latestDatapoints.value = [...map.values()]
    buffer = new Map()
    lastFlushTime = Date.now()
  }

  function scheduleFlush() {
    if (flushTimer) return // Already scheduled
    const elapsed = Date.now() - lastFlushTime
    const delay = Math.max(0, throttleMs.value - elapsed)
    if (delay === 0) {
      flushBuffer()
    } else {
      flushTimer = setTimeout(flushBuffer, delay)
    }
  }

  function bufferDatapoints(incoming: Datapoint[]) {
    for (const dp of incoming) {
      buffer.set(dp.event_public_id, dp)
    }
    scheduleFlush()
  }

  function togglePause() {
    isPaused.value = !isPaused.value
    // When un-pausing, flush any buffered data immediately
    if (!isPaused.value) {
      flushBuffer()
    }
  }

  function setThrottleMs(ms: number) {
    throttleMs.value = Math.max(100, ms)
  }

  // ─── HTTP Polling Fallback ───────────────────────────────────────

  async function fetchLatestHttp() {
    try {
      const { data } = await api.get<Datapoint[]>('/datapoints/latest')
      bufferDatapoints(data)
    } catch {
      // Silently retry on next interval
    }
  }

  function startPolling() {
    if (pollTimer) return
    connectionMode.value = 'polling'
    pollTimer = setInterval(fetchLatestHttp, pollIntervalMs)
    fetchLatestHttp() // Immediately fetch
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  // ─── WebSocket Handler ───────────────────────────────────────────

  function handleWsMessage(data: unknown) {
    const msg = data as { type?: string; datapoints?: Datapoint[] }
    if (msg.type === 'datapoints_batch' && msg.datapoints) {
      bufferDatapoints(msg.datapoints)
    }
  }

  function handleWsStateChange(connected: boolean) {
    isConnected.value = connected
    if (connected) {
      wsFailCount = 0
      connectionMode.value = 'websocket'
      stopPolling()
    } else {
      wsFailCount++
      if (wsFailCount >= WS_MAX_FAILS) {
        // WebSocket appears blocked — fall back to polling
        startPolling()
      }
    }
  }

  // ─── Lifecycle ───────────────────────────────────────────────────

  onMounted(() => {
    // Start with an HTTP fetch so we always have data
    fetchLatestHttp()

    // Try WebSocket (requires JWT token for authentication)
    const token = localStorage.getItem('access_token')
    const wsUrl = token
      ? `/ws/datapoints/stream?token=${encodeURIComponent(token)}`
      : '/ws/datapoints/stream'

    wsClient = new WebSocketClient({
      url: wsUrl,
      onMessage: handleWsMessage,
      onStateChange: handleWsStateChange,
    })
    wsClient.connect()
  })

  onUnmounted(() => {
    wsClient?.dispose()
    stopPolling()
    if (flushTimer) {
      clearTimeout(flushTimer)
      flushTimer = null
    }
  })

  return { latestDatapoints, connectionMode, isConnected, isPaused, togglePause, throttleMs, setThrottleMs }
}
