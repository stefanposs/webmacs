/**
 * Pinia OTA Store – unit tests.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useOtaStore } from '@/stores/ota'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

const SAMPLE_UPDATES = [
  {
    public_id: 'fw-1',
    version: '2.0.0',
    changelog: 'Initial release',
    status: 'pending',
    has_firmware_file: false,
    created_on: '2024-01-01T00:00:00Z',
    user_public_id: 'u1',
  },
]

describe('OTA Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchUpdates() populates state', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_UPDATES },
    })

    const store = useOtaStore()
    await store.fetchUpdates()

    expect(store.updates).toHaveLength(1)
    expect(store.updates[0].version).toBe('2.0.0')
    expect(store.loading).toBe(false)
  })

  it('fetchUpdates() sets error on failure', async () => {
    ;(api.get as Mock).mockRejectedValueOnce(new Error('Offline'))

    const store = useOtaStore()
    await store.fetchUpdates()

    expect(store.error).toBe('Offline')
  })

  it('createUpdate() posts and refreshes', async () => {
    ;(api.post as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_UPDATES },
    })

    const store = useOtaStore()
    await store.createUpdate({ version: '2.1.0', changelog: 'Bug fixes' })

    expect(api.post).toHaveBeenCalledWith('/ota', { version: '2.1.0', changelog: 'Bug fixes' })
  })

  it('checkForUpdates() sets checkResult', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { current_version: '2.0.0', latest_version: '2.1.0', update_available: true },
    })

    const store = useOtaStore()
    await store.checkForUpdates()

    expect(store.checkResult).toEqual({
      current_version: '2.0.0',
      latest_version: '2.1.0',
      update_available: true,
    })
  })

  it('applyUpdate() posts apply and refreshes', async () => {
    ;(api.post as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_UPDATES },
    })

    const store = useOtaStore()
    await store.applyUpdate('fw-1')

    expect(api.post).toHaveBeenCalledWith('/ota/fw-1/apply')
  })

  it('rollbackUpdate() posts rollback and refreshes', async () => {
    ;(api.post as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_UPDATES },
    })

    const store = useOtaStore()
    await store.rollbackUpdate('fw-1')

    expect(api.post).toHaveBeenCalledWith('/ota/fw-1/rollback')
  })

  it('deleteUpdate() optimistically removes', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_UPDATES },
    })

    const store = useOtaStore()
    await store.fetchUpdates()

    ;(api.delete as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    await store.deleteUpdate('fw-1')

    expect(store.updates).toHaveLength(0)
  })

  it('deleteUpdate() rolls back on failure', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: SAMPLE_UPDATES },
    })

    const store = useOtaStore()
    await store.fetchUpdates()

    ;(api.delete as Mock).mockRejectedValueOnce(new Error('Nope'))

    await expect(store.deleteUpdate('fw-1')).rejects.toThrow('Failed to delete update')
    expect(store.updates).toHaveLength(1)
  })
})
