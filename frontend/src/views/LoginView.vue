<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <div class="w-full max-w-md p-6">
      <Card class="shadow-lg">
        <template #title>
          <div class="text-center mb-4">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
              WebMACS
            </h1>
            <p class="text-gray-600 dark:text-gray-400">
              Web-based Monitoring and Control System
            </p>
          </div>
        </template>

        <template #content>
          <!-- Auto-Login Status -->
          <div v-if="autoLogin.isAutoLoggingIn.value" class="mb-4">
            <div class="flex items-center justify-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
              <ProgressSpinner style="width: 20px; height: 20px" stroke-width="4" />
              <span class="text-sm text-blue-800 dark:text-blue-200">
                Automatically logging in...
              </span>
            </div>
          </div>

          <!-- Account Locked Warning -->
          <div v-if="isAccountLocked" class="mb-4">
            <Message 
              severity="warn" 
              :closable="false"
            >
              <template #icon>
                <i class="pi pi-exclamation-triangle"></i>
              </template>
              Account temporarily locked due to too many failed attempts.
              <br>
              Try again after {{ formatTime(unlockTime) }}.
            </Message>
          </div>

          <!-- Login Form -->
          <form @submit.prevent="handleLogin" class="space-y-4">
            <!-- Email Field -->
            <div class="flex flex-col gap-2">
              <label for="email" class="font-medium text-gray-700 dark:text-gray-300">
                Email
              </label>
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
              <small v-if="errors.email" class="text-red-500">
                {{ errors.email }}
              </small>
            </div>

            <!-- Password Field -->
            <div class="flex flex-col gap-2">
              <label for="password" class="font-medium text-gray-700 dark:text-gray-300">
                Password
              </label>
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
              <small v-if="errors.password" class="text-red-500">
                {{ errors.password }}
              </small>
            </div>

            <!-- Remember Me & Auto-Login -->
            <div class="space-y-2">
              <div class="flex items-center gap-2">
                <Checkbox
                  id="remember-me"
                  v-model="form.rememberMe"
                  :disabled="isLoading || isAccountLocked"
                  binary
                />
                <label for="remember-me" class="text-sm text-gray-700 dark:text-gray-300">
                  Remember me
                </label>
              </div>

              <div class="flex items-center gap-2">
                <Checkbox
                  id="enable-auto-login"
                  v-model="form.enableAutoLogin"
                  :disabled="isLoading || isAccountLocked"
                  binary
                />
                <label for="enable-auto-login" class="text-sm text-gray-700 dark:text-gray-300">
                  Enable auto-login for this session
                </label>
              </div>
            </div>

            <!-- Submit Button -->
            <Button
              type="submit"
              label="Sign In"
              icon="pi pi-sign-in"
              :loading="isLoading"
              :disabled="isAccountLocked || !isFormValid"
              class="w-full"
              size="large"
            />
          </form>

          <!-- SSO Login (if enabled) -->
          <div v-if="ssoConfig?.enabled" class="mt-6">
            <div class="relative">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-gray-300 dark:border-gray-600" />
              </div>
              <div class="relative flex justify-center text-sm">
                <span class="px-2 bg-white dark:bg-gray-800 text-gray-500">Or</span>
              </div>
            </div>

            <Button
              :label="`Sign in with ${ssoConfig.provider_name}`"
              icon="pi pi-external-link"
              outlined
              class="w-full mt-4"
              @click="handleSSOLogin"
            />
          </div>

          <!-- Auto-Login Settings Link -->
          <div class="mt-6 text-center">
            <Button
              label="Auto-Login Settings"
              link
              size="small"
              @click="showAutoLoginSettings = true"
            />
          </div>
        </template>
      </Card>
    </div>

    <!-- Auto-Login Settings Dialog -->
    <Dialog
      v-model:visible="showAutoLoginSettings"
      modal
      header="Auto-Login Settings"
      :style="{ width: '600px' }"
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

import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
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
