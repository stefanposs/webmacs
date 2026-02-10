/**
 * Tests for the events Pinia store.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEventStore } from '@/stores/events'

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

const mockEvents = [
  { public_id: 'ev-001', name: 'Temperature', type: 'sensor', unit: '°C', min_value: 0, max_value: 200, user_public_id: null },
  { public_id: 'ev-002', name: 'Pressure', type: 'sensor', unit: 'bar', min_value: 0, max_value: 10, user_public_id: null },
]

describe('useEventStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches events with pagination', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 2, data: mockEvents },
    } as never)

    const store = useEventStore()
    await store.fetchEvents()

    expect(api.get).toHaveBeenCalledWith('/events/', { params: { page: 1, page_size: 50 } })
    expect(store.events).toHaveLength(2)
    expect(store.total).toBe(2)
    expect(store.loading).toBe(false)
  })

  it('sets loading during fetch', async () => {
    let resolvePromise: (v: unknown) => void
    vi.mocked(api.get).mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePromise = resolve
      }) as never,
    )

    const store = useEventStore()
    const promise = store.fetchEvents()
    expect(store.loading).toBe(true)

    resolvePromise!({ data: { page: 1, page_size: 50, total: 0, data: [] } })
    await promise
    expect(store.loading).toBe(false)
  })

  it('creates event and re-fetches', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: [mockEvents[0]] },
    } as never)

    const store = useEventStore()
    await store.createEvent({ name: 'Temperature', type: 'sensor' as never, unit: '°C' })

    expect(api.post).toHaveBeenCalledWith('/events/', expect.objectContaining({ name: 'Temperature' }))
    expect(api.get).toHaveBeenCalled()
  })

  it('updates event and re-fetches', async () => {
    vi.mocked(api.put).mockResolvedValueOnce({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: [mockEvents[0]] },
    } as never)

    const store = useEventStore()
    await store.updateEvent('ev-001', { name: 'Updated' })

    expect(api.put).toHaveBeenCalledWith('/events/ev-001', { name: 'Updated' })
  })

  it('deletes event and removes from local state', async () => {
    vi.mocked(api.delete).mockResolvedValueOnce({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 2, data: mockEvents },
    } as never)

    const store = useEventStore()
    await store.fetchEvents()
    await store.deleteEvent('ev-001')

    expect(api.delete).toHaveBeenCalledWith('/events/ev-001')
    expect(store.events).toHaveLength(1)
    expect(store.events[0].public_id).toBe('ev-002')
  })
})
