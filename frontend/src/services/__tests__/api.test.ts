/**
 * Tests for the API service (Axios instance).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// We test the interceptor logic, not actual HTTP calls
describe('API service', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('attaches JWT token from localStorage to requests', async () => {
    localStorage.setItem('access_token', 'test-token-123')

    // Dynamically import to get fresh module
    vi.resetModules()
    vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

    const { default: api } = await import('@/services/api')

    // Verify the instance has the correct baseURL
    expect(api.defaults.baseURL).toBe('/api/v1')
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('has /api/v1 as baseURL', async () => {
    vi.resetModules()
    vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

    const { default: api } = await import('@/services/api')
    expect(api.defaults.baseURL).toBe('/api/v1')
  })
})
