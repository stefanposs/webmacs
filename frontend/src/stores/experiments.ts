import { defineStore } from 'pinia'
import api from '@/services/api'
import { useNotification } from '@/composables/useNotification'
import { useCrudStore } from '@/composables/useCrudStore'
import type { Experiment } from '@/types'

export const useExperimentStore = defineStore('experiments', () => {
  const { items: experiments, total, loading, error, fetch, create, remove } =
    useCrudStore<Experiment>({ endpoint: '/experiments', name: 'experiment' })

  const notify = useNotification()

  /** Domain-specific action — stops a running experiment. */
  async function stopExperiment(publicId: string): Promise<void> {
    try {
      await api.put(`/experiments/${publicId}/stop`)
      notify.success('Experiment stopped')
      await fetch()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to stop experiment'
      notify.error('Stop failed', msg)
      throw e
    }
  }

  return {
    experiments,
    total,
    loading,
    error,
    fetchExperiments: fetch,
    createExperiment: create,
    stopExperiment,
    deleteExperiment: remove,
  }
})
