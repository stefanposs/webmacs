/**
 * Pinia Webhook Store – unit tests.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWebhookStore } from '@/stores/webhooks'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const SAMPLE_WEBHOOKS = [
  {
    public_id: 'wh-1',
    url: 'https://example.com/hook',
    events: ['sensor.threshold_exceeded'],
    enabled: true,
    created_on: '2024-01-01T00:00:00Z',
    user_public_id: 'u1',
  },
]

describe('Webhook Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchWebhooks() populates state', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_WEBHOOKS },
    })

    const store = useWebhookStore()
    await store.fetchWebhooks()

    expect(store.webhooks).toHaveLength(1)
    expect(store.webhooks[0].url).toBe('https://example.com/hook')
    expect(store.total).toBe(1)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchWebhooks() sets error on failure', async () => {
    ;(api.get as Mock).mockRejectedValueOnce(new Error('Network error'))

    const store = useWebhookStore()
    await store.fetchWebhooks()

    expect(store.error).toBe('Network error')
    expect(store.webhooks).toHaveLength(0)
    expect(store.loading).toBe(false)
  })

  it('createWebhook() posts and refreshes list', async () => {
    ;(api.post as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_WEBHOOKS },
    })

    const store = useWebhookStore()
    await store.createWebhook({
      url: 'https://new.example.com/hook',
      events: ['sensor.reading'],
      enabled: true,
    })

    expect(api.post).toHaveBeenCalledWith('/webhooks', {
      url: 'https://new.example.com/hook',
      events: ['sensor.reading'],
      enabled: true,
    })
    expect(store.webhooks).toHaveLength(1) // refreshed
  })

  it('updateWebhook() puts and refreshes list', async () => {
    ;(api.put as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_WEBHOOKS },
    })

    const store = useWebhookStore()
    await store.updateWebhook('wh-1', { enabled: false })

    expect(api.put).toHaveBeenCalledWith('/webhooks/wh-1', { enabled: false })
  })

  it('deleteWebhook() optimistically removes and confirms via API', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_WEBHOOKS },
    })

    const store = useWebhookStore()
    await store.fetchWebhooks()

    ;(api.delete as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    await store.deleteWebhook('wh-1')

    expect(store.webhooks).toHaveLength(0)
  })

  it('deleteWebhook() rolls back on API failure', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_WEBHOOKS },
    })

    const store = useWebhookStore()
    await store.fetchWebhooks()

    ;(api.delete as Mock).mockRejectedValueOnce(new Error('Server error'))

    await expect(store.deleteWebhook('wh-1')).rejects.toThrow('Failed to delete webhook')
    expect(store.webhooks).toHaveLength(1) // rolled back
  })
})
