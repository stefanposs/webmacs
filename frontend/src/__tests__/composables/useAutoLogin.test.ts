import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useAutoLogin } from '@/composables/useAutoLogin'
import { useAuthStore } from '@/stores/auth'
import { createPinia, setActivePinia } from 'pinia'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock
})

// Mock router
const routerMock = {
  push: vi.fn(),
  currentRoute: {
    value: {
      query: {}
    }
  }
}

vi.mock('vue-router', () => ({
  useRouter: () => routerMock
}))

// Mock notification composable
vi.mock('@/composables/useNotification', () => ({
  useNotification: () => ({
    showError: vi.fn(),
    showSuccess: vi.fn()
  })
}))

describe('useAutoLogin', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should load default config when localStorage is empty', () => {
    localStorageMock.getItem.mockReturnValue(null)
    
    const { loadAutoLoginConfig } = useAutoLogin()
    const config = loadAutoLoginConfig()
    
    expect(config.enabled).toBe(false)
    expect(config.rememberMe).toBe(true)
    expect(config.retryAttempts).toBe(3)
    expect(config.retryDelay).toBe(2000)
  })

  it('should load saved config from localStorage', () => {
    const savedConfig = {
      enabled: true,
      email: 'test@example.com',
      rememberMe: false,
      retryAttempts: 5,
      retryDelay: 3000
    }
    
    localStorageMock.getItem.mockReturnValue(JSON.stringify(savedConfig))
    
    const { loadAutoLoginConfig } = useAutoLogin()
    const config = loadAutoLoginConfig()
    
    expect(config.enabled).toBe(true)
    expect(config.email).toBe('test@example.com')
    expect(config.rememberMe).toBe(false)
    expect(config.retryAttempts).toBe(5)
    expect(config.retryDelay).toBe(3000)
  })

  it('should save config to localStorage without password', () => {
    const { saveAutoLoginConfig } = useAutoLogin()
    const config = {
      enabled: true,
      email: 'test@example.com',
      password: 'secret123',
      rememberMe: true,
      retryAttempts: 3,
      retryDelay: 2000
    }
    
    saveAutoLoginConfig(config)
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'webmacs_auto_login_config',
      expect.not.stringContaining('secret123')
    )
  })

  it('should enable auto-login with credentials', () => {
    const { enableAutoLogin, getStoredCredentials } = useAutoLogin()
    
    sessionStorageMock.getItem.mockReturnValue(
      btoa(JSON.stringify({ email: 'test@example.com', password: 'secret123' }))
    )
    
    enableAutoLogin('test@example.com', 'secret123', false)
    
    expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
      'webmacs_temp_credentials',
      expect.any(String)
    )
    
    const credentials = getStoredCredentials()
    expect(credentials?.email).toBe('test@example.com')
    expect(credentials?.password).toBe('secret123')
  })

  it('should disable auto-login and clear credentials', () => {
    localStorageMock.getItem.mockReturnValue(JSON.stringify({ enabled: true }))
    
    const { disableAutoLogin } = useAutoLogin()
    
    disableAutoLogin()
    
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('webmacs_temp_credentials')
    
    // Verify config is updated to disabled
    const calls = localStorageMock.setItem.mock.calls
    const lastCall = calls[calls.length - 1]
    if (lastCall) {
      const savedConfig = JSON.parse(lastCall[1])
      expect(savedConfig.enabled).toBe(false)
    }
  })

  it('should perform auto-login with valid credentials', async () => {
    const authStore = useAuthStore()
    authStore.login = vi.fn().mockResolvedValue(undefined)
    authStore.isAuthenticated = true
    
    const { performAutoLogin } = useAutoLogin()
    
    const result = await performAutoLogin({
      email: 'test@example.com',
      password: 'secret123'
    })
    
    expect(authStore.login).toHaveBeenCalledWith('test@example.com', 'secret123')
    expect(result).toBe(true)
  })

  it('should handle failed auto-login attempts with retry', async () => {
    const authStore = useAuthStore()
    authStore.login = vi.fn().mockRejectedValue(new Error('Login failed'))
    authStore.isAuthenticated = false
    
    const { performAutoLogin } = useAutoLogin()
    
    const result = await performAutoLogin({
      email: 'test@example.com',
      password: 'wrong'
    })
    
    expect(authStore.login).toHaveBeenCalledWith('test@example.com', 'wrong')
    expect(result).toBe(false)
  })
})
