/**
 * Tests for the system Pinia store (versions + update progress).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSystemStore } from '@/stores/system'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('@/router', () => ({
  default: { push: vi.fn() },
}))

import api from '@/services/api'

const mockVersions = {
  services: [
    {
      name: 'backend',
      installed: '2.4.2',
      available: '2.5.0',
      image: 'stefanposs/webmacs-backend:2.4.2',
      status: 'running' as const,
    },
    {
      name: 'frontend',
      installed: '2.4.2',
      available: '2.5.0',
      image: 'stefanposs/webmacs-frontend:2.4.2',
      status: 'running' as const,
    },
    {
      name: 'controller',
      installed: '2.4.2',
      available: '2.5.0',
      image: 'stefanposs/webmacs-controller:2.4.2',
      status: 'running' as const,
    },
  ],
}

const mockProgressIdle = {
  overall_status: 'idle' as const,
  services: {},
  current_step: null,
  started_at: null,
  error: null,
}

const mockProgressPulling = {
  overall_status: 'pulling' as const,
  services: { backend: 'updating', frontend: 'updating', controller: 'updating' },
  current_step: 'Pulling images…',
  started_at: '2026-03-01T12:00:00Z',
  error: null,
}

describe('useSystemStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('fetchVersions populates versions list', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockVersions } as never)

    const store = useSystemStore()
    await store.fetchVersions()

    expect(api.get).toHaveBeenCalledWith('/system/versions')
    expect(store.versions).toHaveLength(3)
    expect(store.versions[0].name).toBe('backend')
    expect(store.versions[0].installed).toBe('2.4.2')
  })

  it('fetchVersions sets error on failure', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('Network error'))

    const store = useSystemStore()
    await store.fetchVersions()

    expect(store.error).toBe('Network error')
    expect(store.versions).toHaveLength(0)
  })

  it('fetchUpdateProgress stores progress', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockProgressPulling } as never)

    const store = useSystemStore()
    await store.fetchUpdateProgress()

    expect(api.get).toHaveBeenCalledWith('/system/update-progress')
    expect(store.updateProgress?.overall_status).toBe('pulling')
  })

  it('isUpdating is true when pulling', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockProgressPulling } as never)

    const store = useSystemStore()
    await store.fetchUpdateProgress()

    expect(store.isUpdating).toBe(true)
    expect(store.isCompleted).toBe(false)
  })

  it('isUpdating is false when idle', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockProgressIdle } as never)

    const store = useSystemStore()
    await store.fetchUpdateProgress()

    expect(store.isUpdating).toBe(false)
  })

  it('isCompleted is true when completed', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { ...mockProgressIdle, overall_status: 'completed' },
    } as never)

    const store = useSystemStore()
    await store.fetchUpdateProgress()

    expect(store.isCompleted).toBe(true)
    expect(store.isUpdating).toBe(false)
  })

  it('triggerUpdate posts to /system/trigger and starts polling', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { status: 'accepted' } } as never)

    const store = useSystemStore()
    await store.triggerUpdate('2.5.0')

    expect(api.post).toHaveBeenCalledWith('/system/trigger', {
      version: '2.5.0',
      backend_image: 'stefanposs/webmacs-backend:2.5.0',
      frontend_image: 'stefanposs/webmacs-frontend:2.5.0',
      controller_image: 'stefanposs/webmacs-controller:2.5.0',
    })
    // Optimistic update
    expect(store.updateProgress?.overall_status).toBe('pulling')
  })

  it('initialize fetches versions and progress in parallel', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: mockVersions } as never) // /system/versions
      .mockResolvedValueOnce({ data: mockProgressIdle } as never) // /system/update-progress

    const store = useSystemStore()
    await store.initialize()

    expect(api.get).toHaveBeenCalledTimes(2)
    expect(store.versions).toHaveLength(3)
    expect(store.isUpdating).toBe(false)
  })

  it('initialize starts polling when update is active', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: mockVersions } as never)
      .mockResolvedValueOnce({ data: mockProgressPulling } as never)

    const store = useSystemStore()
    await store.initialize()

    expect(store.isUpdating).toBe(true)
    // Polling was started — advance timer and verify extra API calls
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: { ...mockProgressIdle, overall_status: 'completed' } } as never)
      .mockResolvedValueOnce({ data: mockVersions } as never)

    await vi.advanceTimersByTimeAsync(2000)

    // The polling interval (2000ms) should have triggered another round
    expect(api.get).toHaveBeenCalledTimes(4) // 2 initial + 2 from poll
  })

  it('loading state is managed during fetchVersions', async () => {
    let resolve: (v: unknown) => void
    const promise = new Promise((r) => {
      resolve = r
    })
    vi.mocked(api.get).mockReturnValueOnce(promise as never)

    const store = useSystemStore()
    const fetchPromise = store.fetchVersions()

    expect(store.loading).toBe(true)

    resolve!({ data: mockVersions })
    await fetchPromise

    expect(store.loading).toBe(false)
  })
})
