import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { Experiment, PaginatedResponse } from '@/types'

export const useExperimentStore = defineStore('experiments', () => {
  const experiments = ref<Experiment[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchExperiments(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<Experiment>>('/experiments', {
        params: { page, page_size: pageSize },
      })
      experiments.value = data.data
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch experiments'
    } finally {
      loading.value = false
    }
  }

  async function createExperiment(payload: Partial<Experiment>): Promise<void> {
    await api.post('/experiments', payload)
    await fetchExperiments()
  }

  async function stopExperiment(publicId: string): Promise<void> {
    await api.put(`/experiments/${publicId}/stop`)
    await fetchExperiments()
  }

  async function deleteExperiment(publicId: string): Promise<void> {
    const backup = [...experiments.value]
    experiments.value = experiments.value.filter((e) => e.public_id !== publicId)
    try {
      await api.delete(`/experiments/${publicId}`)
    } catch {
      experiments.value = backup
      throw new Error('Failed to delete experiment')
    }
  }

  return { experiments, total, loading, error, fetchExperiments, createExperiment, stopExperiment, deleteExperiment }
})
