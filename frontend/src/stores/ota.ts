import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { FirmwareUpdate, PaginatedResponse, UpdateCheckResponse } from '@/types'

export const useOtaStore = defineStore('ota', () => {
  const updates = ref<FirmwareUpdate[]>([])
  const total = ref(0)
  const loading = ref(false)
  const checkResult = ref<UpdateCheckResponse | null>(null)
  const error = ref<string | null>(null)

  async function fetchUpdates(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<FirmwareUpdate>>('/ota', {
        params: { page, page_size: pageSize },
      })
      updates.value = data.data
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch updates'
    } finally {
      loading.value = false
    }
  }

  async function createUpdate(payload: { version: string; changelog?: string }): Promise<void> {
    await api.post('/ota', payload)
    await fetchUpdates()
  }

  async function checkForUpdates(): Promise<void> {
    const { data } = await api.get<UpdateCheckResponse>('/ota/check')
    checkResult.value = data
  }

  async function applyUpdate(publicId: string): Promise<void> {
    await api.post(`/ota/${publicId}/apply`)
    await fetchUpdates()
  }

  async function rollbackUpdate(publicId: string): Promise<void> {
    await api.post(`/ota/${publicId}/rollback`)
    await fetchUpdates()
  }

  async function deleteUpdate(publicId: string): Promise<void> {
    const backup = [...updates.value]
    updates.value = updates.value.filter((u) => u.public_id !== publicId)
    try {
      await api.delete(`/ota/${publicId}`)
    } catch {
      updates.value = backup
      throw new Error('Failed to delete update')
    }
  }

  return {
    updates,
    total,
    loading,
    error,
    checkResult,
    fetchUpdates,
    createUpdate,
    checkForUpdates,
    applyUpdate,
    rollbackUpdate,
    deleteUpdate,
  }
})
