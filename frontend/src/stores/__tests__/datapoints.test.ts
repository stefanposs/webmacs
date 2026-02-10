/**
 * Tests for the datapoints Pinia store.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDatapointStore } from '@/stores/datapoints'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/router', () => ({
  default: { push: vi.fn() },
}))

import api from '@/services/api'

const mockDatapoints = [
  { public_id: 'dp-001', value: 42.5, timestamp: '2025-06-15T12:00:00Z', event_public_id: 'ev-001', experiment_public_id: 'exp-001' },
  { public_id: 'dp-002', value: 3.14, timestamp: '2025-06-15T12:00:01Z', event_public_id: 'ev-002', experiment_public_id: 'exp-001' },
]

describe('useDatapointStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches datapoints with pagination', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 2, data: mockDatapoints },
    } as never)

    const store = useDatapointStore()
    await store.fetchDatapoints()

    expect(store.datapoints).toHaveLength(2)
    expect(store.total).toBe(2)
  })

  it('fetches latest datapoints', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: mockDatapoints,
    } as never)

    const store = useDatapointStore()
    await store.fetchLatest()

    expect(api.get).toHaveBeenCalledWith('/datapoints/latest')
    expect(store.latestDatapoints).toHaveLength(2)
  })

  it('creates a single datapoint', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: mockDatapoints[0],
    } as never)

    const store = useDatapointStore()
    const result = await store.createDatapoint({ value: 42.5, event_public_id: 'ev-001' })

    expect(api.post).toHaveBeenCalledWith('/datapoints', { value: 42.5, event_public_id: 'ev-001' })
    expect(result.value).toBe(42.5)
  })

  it('creates a batch of datapoints', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: {} } as never)

    const store = useDatapointStore()
    const items = [
      { value: 42.5, event_public_id: 'ev-001' },
      { value: 3.14, event_public_id: 'ev-002' },
    ]
    await store.createBatch(items)

    expect(api.post).toHaveBeenCalledWith('/datapoints/batch', { datapoints: items })
  })

  it('sets loading state during fetch', async () => {
    let resolvePromise: (v: unknown) => void
    vi.mocked(api.get).mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePromise = resolve
      }) as never,
    )

    const store = useDatapointStore()
    const promise = store.fetchDatapoints()
    expect(store.loading).toBe(true)

    resolvePromise!({ data: { page: 1, page_size: 50, total: 0, data: [] } })
    await promise
    expect(store.loading).toBe(false)
  })
})
