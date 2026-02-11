/**
 * Pinia Auth Store – unit tests.
 *
 * Strategy: mock the `api` axios instance so tests run without a real backend.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

// Mock the api module
vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should start unauthenticated', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('login() should store token and fetch user', async () => {
    const mockLogin = api.post as Mock
    mockLogin.mockResolvedValueOnce({
      data: { access_token: 'test-jwt-token', public_id: 'u1', username: 'admin' },
    })

    const mockMe = api.get as Mock
    mockMe.mockResolvedValueOnce({
      data: { public_id: 'u1', email: 'admin@test.io', username: 'admin', admin: true, registered_on: '2024-01-01' },
    })

    const store = useAuthStore()
    await store.login('admin@test.io', 'password123')

    expect(mockLogin).toHaveBeenCalledWith('/auth/login', { email: 'admin@test.io', password: 'password123' })
    expect(store.token).toBe('test-jwt-token')
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.getItem('access_token')).toBe('test-jwt-token')
    expect(store.user?.username).toBe('admin')
    expect(store.isAdmin).toBe(true)
  })

  it('logout() should clear token and user', async () => {
    const mockPost = api.post as Mock
    mockPost.mockResolvedValueOnce({
      data: { access_token: 'tok', public_id: 'u1', username: 'admin' },
    })
    const mockGet = api.get as Mock
    mockGet.mockResolvedValueOnce({
      data: { public_id: 'u1', email: 'a@t.io', username: 'admin', admin: true, registered_on: '2024-01-01' },
    })

    const store = useAuthStore()
    await store.login('a@t.io', 'pw')

    mockPost.mockResolvedValueOnce({ data: {} }) // logout call
    await store.logout()

    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('fetchMe() does nothing without token', async () => {
    const store = useAuthStore()
    await store.fetchMe()
    expect(api.get).not.toHaveBeenCalled()
  })
})
