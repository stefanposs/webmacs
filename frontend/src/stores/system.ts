import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import type { ServiceVersion, UpdateProgress, UpdateOverallStatus } from '@/types'

const POLL_INTERVAL_MS = 2000

export const useSystemStore = defineStore('system', () => {
  const versions = ref<ServiceVersion[]>([])
  const updateProgress = ref<UpdateProgress | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  let _pollTimer: ReturnType<typeof setInterval> | null = null

  const isUpdating = computed(() => {
    const s = updateProgress.value?.overall_status
    return s === 'pulling' || s === 'restarting'
  })

  const isCompleted = computed(() => updateProgress.value?.overall_status === 'completed')

  /**
   * Fetch installed + available versions for all 3 services.
   * While an update is running the backend marks services as "updating".
   */
  async function fetchVersions(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<{ services: ServiceVersion[] }>('/system/versions')
      versions.value = data.services
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch versions'
    } finally {
      loading.value = false
    }
  }

  /** Poll the background update progress once. */
  async function fetchUpdateProgress(): Promise<void> {
    try {
      const { data } = await api.get<UpdateProgress>('/system/update-progress')
      updateProgress.value = data
    } catch {
      // silently ignore — progress endpoint is best-effort
    }
  }

  /**
   * Trigger a Docker pull + restart for the given version.
   * Starts polling /update-progress until finished.
   */
  async function triggerUpdate(version: string): Promise<void> {
    await api.post('/system/trigger', { version })
    // Optimistically set status to pulling
    updateProgress.value = {
      overall_status: 'pulling',
      services: { backend: 'updating', frontend: 'updating', controller: 'updating' },
      current_step: 'Starting update…',
      started_at: new Date().toISOString(),
      error: null,
    }
    _startPolling()
  }

  function _startPolling(): void {
    _stopPolling()
    _pollTimer = setInterval(async () => {
      await fetchUpdateProgress()
      await fetchVersions()
      const s: UpdateOverallStatus | undefined = updateProgress.value?.overall_status
      if (s === 'completed' || s === 'failed' || s === 'idle') {
        _stopPolling()
      }
    }, POLL_INTERVAL_MS)
  }

  function _stopPolling(): void {
    if (_pollTimer !== null) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  /** Call on component mount to resume polling if an update was already running. */
  async function initialize(): Promise<void> {
    await Promise.all([fetchVersions(), fetchUpdateProgress()])
    if (isUpdating.value) {
      _startPolling()
    }
  }

  return {
    versions,
    updateProgress,
    loading,
    error,
    isUpdating,
    isCompleted,
    fetchVersions,
    fetchUpdateProgress,
    triggerUpdate,
    initialize,
  }
})
