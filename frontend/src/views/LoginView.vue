<template>
  <div class="login-page">
    <div class="login-card">
      <!-- Logo -->
      <div class="login-logo">
        <i class="pi pi-microchip" />
      </div>
      <h1>WebMACS</h1>
      <p class="login-subtitle">Web-based Monitoring and Control System</p>

      <!-- Auto-Login Status -->
      <div v-if="autoLogin.isAutoLoggingIn.value" class="auto-login-status">
        <ProgressSpinner style="width: 20px; height: 20px" stroke-width="4" />
        <span>Automatically logging in...</span>
      </div>

      <!-- Account Locked Warning -->
      <div v-if="isAccountLocked" class="lockout-warning">
        <i class="pi pi-exclamation-triangle" />
        <span>
          Account temporarily locked. Try again after {{ formatTime(unlockTime) }}.
        </span>
      </div>

      <!-- Login Form -->
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="email">Email</label>
          <div class="input-icon">
            <i class="pi pi-envelope" />
            <InputText
              id="email"
              v-model="form.email"
              type="email"
              placeholder="admin@webmacs.local"
              :invalid="!!errors.email"
              :disabled="isLoading || isAccountLocked"
              required
              autofocus
              @blur="validateEmail"
              @input="clearError('email')"
            />
          </div>
          <small v-if="errors.email" class="field-error">{{ errors.email }}</small>
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <div class="input-icon">
            <i class="pi pi-lock" />
            <Password
              id="password"
              v-model="form.password"
              placeholder="Enter your password"
              :invalid="!!errors.password"
              :disabled="isLoading || isAccountLocked"
              :feedback="false"
              toggle-mask
              required
              @blur="validatePassword"
              @input="clearError('password')"
            />
          </div>
          <small v-if="errors.password" class="field-error">{{ errors.password }}</small>
        </div>

        <!-- Remember Me & Auto-Login -->
        <div class="checkbox-group">
          <div class="checkbox-item">
            <Checkbox
              id="remember-me"
              v-model="form.rememberMe"
              :disabled="isLoading || isAccountLocked"
              binary
            />
            <label for="remember-me">Remember me</label>
          </div>
          <div class="checkbox-item">
            <Checkbox
              id="enable-auto-login"
              v-model="form.enableAutoLogin"
              :disabled="isLoading || isAccountLocked"
              binary
            />
            <label for="enable-auto-login">Enable auto-login for this session</label>
          </div>
        </div>

        <button type="submit" class="btn-login" :disabled="isLoading || isAccountLocked || !isFormValid">
          <i v-if="isLoading" class="pi pi-spin pi-spinner" />
          <i v-else class="pi pi-sign-in" />
          {{ isLoading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>

      <!-- SSO Login -->
      <template v-if="ssoConfig?.enabled">
        <div class="sso-divider"><span>or</span></div>
        <button class="btn-sso" @click="handleSSOLogin">
          <i class="pi pi-shield" />
          Sign in with {{ ssoConfig.provider_name }}
        </button>
      </template>

      <!-- Auto-Login Settings -->
      <div class="auto-login-link">
        <button class="btn-link" @click="showAutoLoginSettings = true">
          <i class="pi pi-cog" /> Auto-Login Settings
        </button>
      </div>
    </div>

    <div class="login-footer">
      WebMACS v2.0 &middot; IoT Control Platform
    </div>

    <!-- Auto-Login Settings Dialog -->
    <Dialog
      v-model:visible="showAutoLoginSettings"
      modal
      header="Auto-Login Settings"
      :style="{ width: '90vw', maxWidth: '600px' }"
    >
      <AutoLoginSettings />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAutoLogin } from '@/composables/useAutoLogin'
import { useNotification } from '@/composables/useNotification'
import { AutoLoginService } from '@/services/autoLoginService'
import AutoLoginSettings from '@/components/AutoLoginSettings.vue'

import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const autoLogin = useAutoLogin()
const { error: showError } = useNotification()

const isLoading = ref(false)
const showAutoLoginSettings = ref(false)
const ssoConfig = ref<any>(null)

const form = reactive({
  email: '',
  password: '',
  rememberMe: false,
  enableAutoLogin: false
})

const errors = reactive({
  email: '',
  password: '',
  general: ''
})

// Account lockout state
const isAccountLocked = computed(() => {
  return AutoLoginService.isAccountLocked(form.email)
})

const unlockTime = computed(() => {
  return AutoLoginService.getUnlockTime(form.email)
})

// Form validation
const isFormValid = computed(() => {
  return form.email && form.password && !errors.email && !errors.password
})

// Initialize component
onMounted(async () => {
  // Check if already authenticated
  if (authStore.isAuthenticated) {
    const redirect = route.query.redirect as string
    await router.push(redirect || '/dashboard')
    return
  }

  // Load SSO configuration
  try {
    const response = await fetch('/api/v1/auth/sso/config')
    if (response.ok) {
      ssoConfig.value = await response.json()
    }
  } catch (error) {
    console.warn('Failed to load SSO config:', error)
  }

  // Load saved email if available
  const storedCreds = autoLogin.getStoredCredentials()
  if (storedCreds?.email) {
    form.email = storedCreds.email
    if (storedCreds.password) {
      form.password = storedCreds.password
      form.enableAutoLogin = true
    }
  }

  // Initialize auto-login
  await autoLogin.initializeAutoLogin()
})

// Watch for auto-login attempts
watch(() => autoLogin.autoLoginAttempts.value, (attempts) => {
  if (attempts > 0) {
    AutoLoginService.logAttempt({
      email: form.email,
      success: authStore.isAuthenticated,
      error: authStore.isAuthenticated ? undefined : 'Auto-login failed'
    })
  }
})

// Validation functions
const validateEmail = () => {
  if (!form.email) {
    errors.email = 'Email is required'
  } else if (!form.email.includes('@')) {
    errors.email = 'Please enter a valid email address'
  } else {
    errors.email = ''
  }
}

const validatePassword = () => {
  if (!form.password) {
    errors.password = 'Password is required'
  } else {
    errors.password = ''
  }
}

const clearError = (field: keyof typeof errors) => {
  errors[field] = ''
}

// Handle login form submission
const handleLogin = async () => {
  if (isAccountLocked.value) {
    showError('Account is temporarily locked. Please wait before trying again.')
    return
  }

  validateEmail()
  validatePassword()

  if (!isFormValid.value) {
    return
  }

  isLoading.value = true
  errors.general = ''

  try {
    await authStore.login(form.email, form.password)

    // Log successful attempt
    AutoLoginService.logAttempt({
      email: form.email,
      success: true
    })

    // Enable auto-login if requested
    if (form.enableAutoLogin) {
      autoLogin.enableAutoLogin(form.email, form.password, form.rememberMe)
    }

    // Navigate to intended destination
    const redirect = route.query.redirect as string
    await router.push(redirect || '/dashboard')

  } catch (error: any) {
    console.error('Login failed:', error)

    // Log failed attempt
    AutoLoginService.logAttempt({
      email: form.email,
      success: false,
      error: error.message || 'Login failed'
    })

    errors.general = error.message || 'Invalid email or password'
    showError(errors.general)

  } finally {
    isLoading.value = false
  }
}

// Handle SSO login
const handleSSOLogin = () => {
  window.location.href = '/api/v1/auth/sso/authorize'
}

// Format time for account lockout display
const formatTime = (time: Date | null): string => {
  if (!time) return ''
  
  const now = new Date()
  const diff = time.getTime() - now.getTime()
  
  if (diff <= 0) return 'now'
  
  const minutes = Math.ceil(diff / (1000 * 60))
  return `${minutes} minute${minutes !== 1 ? 's' : ''}`
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background:
    linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  background-size: 100%, 100%, 24px 24px;
}

@media (prefers-color-scheme: light) {
  .login-page {
    background:
      radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, 0.15) 0%, transparent 60%),
      radial-gradient(ellipse at 80% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
      radial-gradient(circle at 2px 2px, rgba(255, 255, 255, 0.04) 1px, transparent 0);
    background-size: 100%, 100%, 24px 24px;
  }
}

.login-card {
  position: relative;
  background: #fff;
  padding: 2.5rem 2.5rem 2rem;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
  width: 100%;
  max-width: 400px;
  margin: 0 1rem;
  text-align: center;
}

@media (prefers-color-scheme: dark) {
  .login-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }
}

.login-card h1 {
  font-size: 1.75rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.2rem;
  letter-spacing: -0.03em;
}

@media (prefers-color-scheme: dark) {
  .login-card h1 { color: #f1f5f9; }
}

@media (max-width: 480px) {
  .login-card {
    padding: 1.5rem 1.25rem 1.5rem;
    margin: 0 0.5rem;
    border-radius: 12px;
  }
}

.login-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 1rem;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
}

.login-logo i {
  font-size: 1.5rem;
  color: #fff;
}

.login-subtitle {
  color: #64748b;
  margin-bottom: 2rem;
  font-size: 0.9rem;
}

.login-form {
  text-align: left;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  font-size: 0.8rem;
  margin-bottom: 0.4rem;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

@media (prefers-color-scheme: dark) {
  .form-group label { color: #94a3b8; }
}

.input-icon {
  position: relative;
}

.input-icon > i {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 0.85rem;
  z-index: 1;
  pointer-events: none;
}

.input-icon :deep(input) {
  padding-left: 2.25rem !important;
  width: 100%;
}

.input-icon :deep(.p-inputtext) {
  width: 100%;
}

.input-icon :deep(.p-password) {
  width: 100%;
}

.input-icon :deep(.p-password input) {
  width: 100%;
  padding-left: 2.25rem !important;
}

.field-error {
  display: block;
  color: #ef4444;
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.auto-login-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-bottom: 1.25rem;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 8px;
  font-size: 0.85rem;
  color: #3b82f6;
}

.lockout-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-bottom: 1.25rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 8px;
  font-size: 0.85rem;
  color: #b45309;
}

@media (prefers-color-scheme: dark) {
  .lockout-warning { color: #fbbf24; }
}

.checkbox-group {
  margin-bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-item label {
  font-size: 0.85rem;
  color: #475569;
  cursor: pointer;
}

@media (prefers-color-scheme: dark) {
  .checkbox-item label { color: #94a3b8; }
}

.btn-login {
  width: 100%;
  padding: 0.7rem;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.btn-login:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.45);
  transform: translateY(-1px);
}

.btn-login:active:not(:disabled) { transform: translateY(0); }
.btn-login:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.sso-divider {
  display: flex;
  align-items: center;
  margin: 1.5rem 0;
  gap: 0.75rem;
}

.sso-divider::before,
.sso-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e2e8f0;
}

@media (prefers-color-scheme: dark) {
  .sso-divider::before,
  .sso-divider::after { background: #334155; }
}

.sso-divider span {
  color: #64748b;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.btn-sso {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.7rem;
  background: #1e293b;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.btn-sso:hover {
  background: #334155;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  transform: translateY(-1px);
}

.btn-sso:active { transform: translateY(0); }

.auto-login-link {
  margin-top: 1.25rem;
  text-align: center;
}

.btn-link {
  background: none;
  border: none;
  color: #3b82f6;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.btn-link:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #2563eb;
}

.login-footer {
  margin-top: 2rem;
  font-size: 0.75rem;
  color: #64748b;
}
</style>
