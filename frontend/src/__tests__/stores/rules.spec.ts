/**
 * Pinia Rules Store – unit tests.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useRuleStore } from '@/stores/rules'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const SAMPLE_RULES = [
  {
    public_id: 'rule-1',
    name: 'High Temp Alert',
    event_public_id: 'evt-1',
    operator: 'gt',
    threshold: 80.0,
    threshold_high: null,
    action_type: 'webhook',
    webhook_event_type: 'sensor.threshold_exceeded',
    enabled: true,
    cooldown_seconds: 60,
    last_triggered_at: null,
    created_on: '2024-01-01T00:00:00Z',
    user_public_id: 'u1',
  },
]

describe('Rules Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchRules() populates state', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_RULES },
    })

    const store = useRuleStore()
    await store.fetchRules()

    expect(store.rules).toHaveLength(1)
    expect(store.rules[0].name).toBe('High Temp Alert')
    expect(store.total).toBe(1)
    expect(store.loading).toBe(false)
  })

  it('fetchRules() sets error on failure', async () => {
    ;(api.get as Mock).mockRejectedValueOnce(new Error('Boom'))

    const store = useRuleStore()
    await store.fetchRules()

    expect(store.error).toBe('Boom')
    expect(store.rules).toHaveLength(0)
  })

  it('createRule() posts and refreshes', async () => {
    ;(api.post as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_RULES },
    })

    const store = useRuleStore()
    await store.createRule({
      name: 'New Rule',
      event_public_id: 'evt-1',
      operator: 'lt',
      threshold: 10.0,
      action_type: 'log',
    })

    expect(api.post).toHaveBeenCalledWith('/rules', expect.objectContaining({ name: 'New Rule' }))
  })

  it('updateRule() puts and refreshes', async () => {
    ;(api.put as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_RULES },
    })

    const store = useRuleStore()
    await store.updateRule('rule-1', { enabled: false })

    expect(api.put).toHaveBeenCalledWith('/rules/rule-1', { enabled: false })
  })

  it('deleteRule() optimistically removes', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_RULES },
    })

    const store = useRuleStore()
    await store.fetchRules()

    ;(api.delete as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    await store.deleteRule('rule-1')

    expect(store.rules).toHaveLength(0)
  })

  it('deleteRule() rolls back on failure', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_RULES },
    })

    const store = useRuleStore()
    await store.fetchRules()

    ;(api.delete as Mock).mockRejectedValueOnce(new Error('Nope'))

    await expect(store.deleteRule('rule-1')).rejects.toThrow('Failed to delete rule')
    expect(store.rules).toHaveLength(1) // rolled back
  })
})
