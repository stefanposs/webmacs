import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { Datapoint, PaginatedResponse } from '@/types'

export const useDatapointStore = defineStore('datapoints', () => {
  const datapoints = ref<Datapoint[]>([])
  const latestDatapoints = ref<Datapoint[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchDatapoints(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    try {
      const { data } = await api.get<PaginatedResponse<Datapoint>>('/datapoints', {
        params: { page, page_size: pageSize },
      })
      datapoints.value = data.data
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function fetchLatest(): Promise<void> {
    const { data } = await api.get<Datapoint[]>('/datapoints/latest')
    latestDatapoints.value = data
  }

  async function createDatapoint(payload: { value: number; event_public_id: string }): Promise<void> {
    await api.post('/datapoints', payload)
  }

  async function createBatch(items: { value: number; event_public_id: string }[]): Promise<void> {
    await api.post('/datapoints/batch', { datapoints: items })
  }

  return { datapoints, latestDatapoints, total, loading, fetchDatapoints, fetchLatest, createDatapoint, createBatch }
})
