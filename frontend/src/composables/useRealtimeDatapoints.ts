/**
 * Composable for real-time datapoint streaming.
 *
 * Strategy: WebSocket-first with automatic HTTP polling fallback.
 *
 * 1. Tries to connect to /ws/datapoints/stream
 * 2. If WebSocket fails to connect after 3 attempts, falls back to HTTP polling
 * 3. If WebSocket reconnects later, stops polling and switches back
 *
 * Usage:
 *   const { latestDatapoints, connectionMode, isConnected } = useRealtimeDatapoints()
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
}

export function useRealtimeDatapoints(pollIntervalMs = 1500): RealtimeDatapointsReturn {
  const latestDatapoints = ref<Datapoint[]>([])
  const connectionMode = ref<ConnectionMode>('connecting')
  const isConnected = ref(false)

  let wsClient: WebSocketClient | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let wsFailCount = 0
  const WS_MAX_FAILS = 3

  // ─── HTTP Polling Fallback ───────────────────────────────────────

  async function fetchLatestHttp() {
    try {
      const { data } = await api.get<Datapoint[]>('/datapoints/latest')
      latestDatapoints.value = data
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
      // Merge incoming datapoints with latest (update by event_public_id)
      const map = new Map<string, Datapoint>()
      for (const dp of latestDatapoints.value) {
        map.set(dp.event_public_id, dp)
      }
      for (const dp of msg.datapoints) {
        map.set(dp.event_public_id, dp)
      }
      latestDatapoints.value = [...map.values()]
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
  })

  return { latestDatapoints, connectionMode, isConnected }
}
