import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotification } from '@/composables/useNotification'

export interface AutoLoginConfig {
  enabled: boolean
  email?: string
  password?: string
  rememberMe: boolean
  retryAttempts: number
  retryDelay: number
}

export function useAutoLogin() {
  const router = useRouter()
  const authStore = useAuthStore()
  const { error: showError, success: showSuccess } = useNotification()
  
  const isAutoLoggingIn = ref(false)
  const autoLoginAttempts = ref(0)
  const maxRetries = ref(3)
  
  const defaultConfig: AutoLoginConfig = {
    enabled: false,
    rememberMe: true,
    retryAttempts: 3,
    retryDelay: 2000
  }

  // Load config from localStorage
  const loadAutoLoginConfig = (): AutoLoginConfig => {
    try {
      const saved = localStorage.getItem('webmacs_auto_login_config')
      if (saved) {
        const parsed = JSON.parse(saved)
        return { ...defaultConfig, ...parsed }
      }
    } catch (error) {
      console.warn('Failed to load auto-login config:', error)
    }
    return defaultConfig
  }

  // Save config to localStorage
  const saveAutoLoginConfig = (config: AutoLoginConfig) => {
    try {
      // Don't persist password for security
      const configToSave = { ...config }
      delete configToSave.password
      localStorage.setItem('webmacs_auto_login_config', JSON.stringify(configToSave))
    } catch (error) {
      console.warn('Failed to save auto-login config:', error)
    }
  }

  // Check if auto-login should be attempted
  const shouldAutoLogin = computed(() => {
    const config = loadAutoLoginConfig()
    return config.enabled && 
           !authStore.isAuthenticated && 
           !isAutoLoggingIn.value &&
           autoLoginAttempts.value < maxRetries.value
  })

  // Perform automated login
  const performAutoLogin = async (credentials?: { email: string; password: string }) => {
    if (isAutoLoggingIn.value) return false

    const config = loadAutoLoginConfig()
    
    const email = credentials?.email || config.email
    const password = credentials?.password || config.password

    if (!email || !password) {
      console.warn('Auto-login: Missing credentials')
      return false
    }

    isAutoLoggingIn.value = true
    autoLoginAttempts.value++

    try {
      await authStore.login(email, password)
      
      if (authStore.isAuthenticated) {
        showSuccess('Automatically logged in successfully')
        
        // Navigate to intended destination or dashboard
        const redirect = router.currentRoute.value.query.redirect as string
        await router.push(redirect || '/dashboard')
        
        // Reset attempts on success
        autoLoginAttempts.value = 0
        return true
      }
    } catch (error: any) {
      console.error('Auto-login failed:', error)
      
      if (autoLoginAttempts.value >= maxRetries.value) {
        showError('Auto-login failed after maximum attempts')
        // Disable auto-login after max retries
        const updatedConfig = { ...config, enabled: false }
        saveAutoLoginConfig(updatedConfig)
      } else {
        // Schedule retry
        setTimeout(() => {
          if (shouldAutoLogin.value) {
            performAutoLogin(credentials)
          }
        }, config.retryDelay)
      }
    } finally {
      isAutoLoggingIn.value = false
    }
    
    return false
  }

  // Enable auto-login with credentials
  const enableAutoLogin = (email: string, password: string, rememberMe = true) => {
    const config: AutoLoginConfig = {
      enabled: true,
      email,
      password, // Will be excluded from localStorage
      rememberMe,
      retryAttempts: 3,
      retryDelay: 2000
    }
    
    saveAutoLoginConfig(config)
    
    // Store encrypted credentials in sessionStorage if rememberMe is false
    if (!rememberMe && password) {
      try {
        sessionStorage.setItem('webmacs_temp_credentials', btoa(JSON.stringify({ email, password })))
      } catch (error) {
        console.warn('Failed to store temporary credentials:', error)
      }
    }
  }

  // Disable auto-login
  const disableAutoLogin = () => {
    const config = loadAutoLoginConfig()
    const updatedConfig = { ...config, enabled: false }
    saveAutoLoginConfig(updatedConfig)
    
    // Clear temporary credentials
    sessionStorage.removeItem('webmacs_temp_credentials')
    autoLoginAttempts.value = 0
  }

  // Get stored credentials for auto-login
  const getStoredCredentials = (): { email: string; password: string } | null => {
    const config = loadAutoLoginConfig()
    
    // Try sessionStorage first (temporary credentials)
    try {
      const tempCreds = sessionStorage.getItem('webmacs_temp_credentials')
      if (tempCreds) {
        const decoded = JSON.parse(atob(tempCreds))
        return decoded
      }
    } catch (error) {
      console.warn('Failed to retrieve temporary credentials:', error)
    }

    // Fallback to config (email only, password would need to be re-entered)
    if (config.email) {
      return { email: config.email, password: '' }
    }

    return null
  }

  // Initialize auto-login on app start
  const initializeAutoLogin = async () => {
    if (authStore.isAuthenticated) return

    const credentials = getStoredCredentials()
    if (credentials?.email && credentials?.password && shouldAutoLogin.value) {
      await performAutoLogin(credentials)
    }
  }

  return {
    isAutoLoggingIn: computed(() => isAutoLoggingIn.value),
    autoLoginAttempts: computed(() => autoLoginAttempts.value),
    maxRetries: computed(() => maxRetries.value),
    shouldAutoLogin,
    performAutoLogin,
    enableAutoLogin,
    disableAutoLogin,
    getStoredCredentials,
    initializeAutoLogin,
    loadAutoLoginConfig,
    saveAutoLoginConfig
  }
}
