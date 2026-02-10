/**
 * Tests for the experiments Pinia store.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useExperimentStore } from '@/stores/experiments'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/router', () => ({
  default: { push: vi.fn() },
}))

import api from '@/services/api'

const mockExperiments = [
  { public_id: 'exp-001', name: 'Run 1', started_on: '2025-06-15T10:00:00Z', stopped_on: null, user_public_id: 'u1' },
  { public_id: 'exp-002', name: 'Run 2', started_on: '2025-06-14T08:00:00Z', stopped_on: '2025-06-14T12:00:00Z', user_public_id: 'u1' },
]

describe('useExperimentStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches experiments', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 2, data: mockExperiments },
    } as never)

    const store = useExperimentStore()
    await store.fetchExperiments()

    expect(store.experiments).toHaveLength(2)
    expect(store.total).toBe(2)
  })

  it('creates experiment and re-fetches', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: [mockExperiments[0]] },
    } as never)

    const store = useExperimentStore()
    await store.createExperiment({ name: 'New Run' })

    expect(api.post).toHaveBeenCalledWith('/experiments', { name: 'New Run' })
  })

  it('stops experiment and re-fetches', async () => {
    vi.mocked(api.put).mockResolvedValueOnce({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 2, data: mockExperiments },
    } as never)

    const store = useExperimentStore()
    await store.stopExperiment('exp-001')

    expect(api.put).toHaveBeenCalledWith('/experiments/exp-001/stop')
  })

  it('deletes experiment and removes from local state', async () => {
    vi.mocked(api.delete).mockResolvedValueOnce({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 2, data: mockExperiments },
    } as never)

    const store = useExperimentStore()
    await store.fetchExperiments()
    await store.deleteExperiment('exp-001')

    expect(store.experiments).toHaveLength(1)
  })
})
