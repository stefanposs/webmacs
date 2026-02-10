/**
 * Tests for the auth Pinia store.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

// Mock the router
vi.mock('@/router', () => ({
  default: {
    push: vi.fn(),
  },
}))

import api from '@/services/api'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('initializes with no user and no token', () => {
    const store = useAuthStore()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(store.isAdmin).toBe(false)
  })

  it('login stores token and fetches user', async () => {
    const mockLogin = vi.mocked(api.post)
    const mockGetMe = vi.mocked(api.get)

    mockLogin.mockResolvedValueOnce({
      data: {
        status: 'success',
        access_token: 'test-jwt-token',
        public_id: 'user-001',
        username: 'admin',
      },
    } as never)

    mockGetMe.mockResolvedValueOnce({
      data: {
        public_id: 'user-001',
        email: 'admin@webmacs.io',
        username: 'admin',
        admin: true,
        registered_on: '2025-01-01T00:00:00Z',
      },
    } as never)

    const store = useAuthStore()
    await store.login('admin@webmacs.io', 'admin123')

    expect(mockLogin).toHaveBeenCalledWith('/auth/login', {
      email: 'admin@webmacs.io',
      password: 'admin123',
    })
    expect(store.token).toBe('test-jwt-token')
    expect(store.isAuthenticated).toBe(true)
    expect(store.user?.username).toBe('admin')
    expect(store.isAdmin).toBe(true)
    expect(localStorage.getItem('access_token')).toBe('test-jwt-token')
  })

  it('logout clears state and localStorage', async () => {
    const mockPost = vi.mocked(api.post)
    mockPost.mockResolvedValueOnce({ data: {} } as never)

    const store = useAuthStore()
    store.token = 'some-token'
    store.user = {
      public_id: 'u1',
      email: 'test@test.com',
      username: 'test',
      admin: false,
      registered_on: '2025-01-01T00:00:00Z',
    }

    await store.logout()

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('fetchMe sets user on success', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValueOnce({
      data: {
        public_id: 'user-001',
        email: 'test@webmacs.io',
        username: 'test',
        admin: false,
        registered_on: '2025-06-01T00:00:00Z',
      },
    } as never)

    const store = useAuthStore()
    store.token = 'valid-token'
    await store.fetchMe()

    expect(store.user?.email).toBe('test@webmacs.io')
    expect(store.isAdmin).toBe(false)
  })

  it('fetchMe calls logout on failure', async () => {
    const mockGet = vi.mocked(api.get)
    mockGet.mockRejectedValueOnce(new Error('Unauthorized'))

    const store = useAuthStore()
    store.token = 'expired-token'
    await store.fetchMe()

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
  })

  it('fetchMe does nothing without token', async () => {
    const mockGet = vi.mocked(api.get)

    const store = useAuthStore()
    store.token = null
    await store.fetchMe()

    expect(mockGet).not.toHaveBeenCalled()
  })
})
