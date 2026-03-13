<template>
  <div class="login-container">
    <div class="login-background">
      <div class="animated-grid"></div>
      <div class="floating-particles"></div>
    </div>
    
    <div class="login-card" :class="{ 'card-animate': isLoaded }">
      <div class="login-header">
        <div class="logo-container" :class="{ 'logo-animate': isLoaded }">
          <i class="pi pi-desktop text-6xl text-primary"></i>
          <h1 class="text-3xl font-bold mt-3 mb-2">WebMACS</h1>
          <p class="text-surface-500 text-sm mb-6">Monitoring and Control System</p>
        </div>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="field" :class="{ 'field-animate': isLoaded }">
          <label for="email" class="block text-sm font-medium mb-2">Email</label>
          <InputText
            id="email"
            v-model="email"
            type="email"
            placeholder="Enter your email"
            class="w-full p-inputtext-lg"
            :class="{ 'p-invalid': emailError }"
            @input="clearEmailError"
            autofocus
          />
          <small v-if="emailError" class="p-error">{{ emailError }}</small>
        </div>

        <div class="field" :class="{ 'field-animate': isLoaded }" style="animation-delay: 0.1s">
          <label for="password" class="block text-sm font-medium mb-2">Password</label>
          <Password
            id="password"
            v-model="password"
            placeholder="Enter your password"
            class="w-full"
            input-class="p-inputtext-lg w-full"
            :class="{ 'p-invalid': passwordError }"
            @input="clearPasswordError"
            :feedback="false"
            toggle-mask
          />
          <small v-if="passwordError" class="p-error">{{ passwordError }}</small>
        </div>

        <div class="login-actions" :class="{ 'actions-animate': isLoaded }">
          <Button
            type="submit"
            label="Sign In"
            class="w-full p-button-lg login-button"
            :loading="isLoading"
            :disabled="!isFormValid"
            icon="pi pi-sign-in"
          />
        </div>

        <div v-if="ssoConfig?.enabled" class="sso-section" :class="{ 'sso-animate': isLoaded }">
          <div class="divider">
            <span>or</span>
          </div>
          <Button
            type="button"
            :label="`Continue with ${ssoConfig.provider_name}`"
            class="w-full p-button-outlined sso-button"
            icon="pi pi-id-card"
            @click="handleSSOLogin"
            :disabled="isLoading"
          />
        </div>

        <div v-if="error" class="error-message" :class="{ 'error-animate': error }">
          <i class="pi pi-exclamation-triangle"></i>
          {{ error }}
        </div>
      </form>
    </div>

    <div class="version-info" :class="{ 'version-animate': isLoaded }">
      <span>WebMACS v{{ version }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import { useAuthStore } from '@/stores/auth'
import { useNotification } from '@/composables/useNotification'

const router = useRouter()
const authStore = useAuthStore()
const { showError } = useNotification()

// Form state
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref('')
const emailError = ref('')
const passwordError = ref('')
const isLoaded = ref(false)
const ssoConfig = ref(null)

// Version info
const version = ref('2.2.0')

// Animation state
onMounted(async () => {
  // Trigger animations after component mount
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
  
  // Load SSO config
  try {
    const response = await fetch('/api/v1/auth/sso/config')
    if (response.ok) {
      ssoConfig.value = await response.json()
    }
  } catch (err) {
    console.warn('Failed to load SSO config:', err)
  }
  
  // Create floating particles animation
  createParticles()
})

// Form validation
const isFormValid = computed(() => {
  return email.value && password.value && !emailError.value && !passwordError.value
})

// Clear errors
const clearEmailError = () => {
  emailError.value = ''
  error.value = ''
}

const clearPasswordError = () => {
  passwordError.value = ''
  error.value = ''
}

// Validate email format
const validateEmail = (email: string) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// Login handler
const handleLogin = async () => {
  // Reset errors
  error.value = ''
  emailError.value = ''
  passwordError.value = ''

  // Client-side validation
  if (!email.value) {
    emailError.value = 'Email is required'
    return
  }

  if (!validateEmail(email.value)) {
    emailError.value = 'Please enter a valid email address'
    return
  }

  if (!password.value) {
    passwordError.value = 'Password is required'
    return
  }

  isLoading.value = true

  try {
    await authStore.login(email.value, password.value)
    router.push('/')
  } catch (err: any) {
    console.error('Login failed:', err)
    if (err.response?.status === 422) {
      error.value = 'Invalid email or password format'
    } else if (err.response?.status === 401) {
      error.value = 'Invalid email or password'
    } else {
      error.value = 'Login failed. Please try again.'
    }
  } finally {
    isLoading.value = false
  }
}

// SSO login handler
const handleSSOLogin = () => {
  window.location.href = '/api/v1/auth/sso/authorize'
}

// Create floating particles animation
const createParticles = () => {
  const container = document.querySelector('.floating-particles')
  if (!container) return

  for (let i = 0; i < 6; i++) {
    const particle = document.createElement('div')
    particle.className = 'particle'
    particle.style.left = `${Math.random() * 100}%`
    particle.style.animationDelay = `${Math.random() * 4}s`
    particle.style.animationDuration = `${4 + Math.random() * 2}s`
    container.appendChild(particle)
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: linear-gradient(135deg, 
    var(--surface-900) 0%, 
    var(--surface-800) 50%, 
    var(--surface-900) 100%
  );
  overflow: hidden;
}

.login-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
}

.animated-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(var(--primary-400), 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(var(--primary-400), 0.1) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: gridFloat 20s ease-in-out infinite;
}

@keyframes gridFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(-10px, -5px) scale(1.02); }
  50% { transform: translate(5px, -10px) scale(0.98); }
  75% { transform: translate(-5px, 5px) scale(1.01); }
}

.floating-particles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: var(--primary-400);
  border-radius: 50%;
  opacity: 0.6;
  animation: particleFloat 6s ease-in-out infinite;
}

@keyframes particleFloat {
  0%, 100% {
    transform: translateY(0) translateX(0) scale(1);
    opacity: 0.6;
  }
  25% {
    transform: translateY(-20px) translateX(10px) scale(1.2);
    opacity: 0.8;
  }
  50% {
    transform: translateY(-40px) translateX(-5px) scale(0.8);
    opacity: 0.4;
  }
  75% {
    transform: translateY(-20px) translateX(-10px) scale(1.1);
    opacity: 0.7;
  }
}

.login-card {
  background: var(--surface-card);
  padding: 3rem;
  border-radius: 1rem;
  box-shadow: 
    0 25px 50px -12px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.05);
  width: 100%;
  max-width: 420px;
  position: relative;
  z-index: 2;
  backdrop-filter: blur(10px);
  transform: translateY(20px);
  opacity: 0;
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.login-card.card-animate {
  transform: translateY(0);
  opacity: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.logo-container {
  transform: scale(0.8);
  opacity: 0;
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.logo-container.logo-animate {
  transform: scale(1);
  opacity: 1;
}

.logo-container i {
  background: linear-gradient(135deg, var(--primary-400), var(--primary-600));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: logoGlow 3s ease-in-out infinite alternate;
}

@keyframes logoGlow {
  0% {
    filter: drop-shadow(0 0 5px rgba(var(--primary-400), 0.3));
  }
  100% {
    filter: drop-shadow(0 0 15px rgba(var(--primary-400), 0.6));
  }
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.field {
  transform: translateX(-20px);
  opacity: 0;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.field.field-animate {
  transform: translateX(0);
  opacity: 1;
}

.field label {
  color: var(--text-color);
  font-weight: 500;
}

.login-actions {
  margin-top: 1rem;
  transform: translateY(20px);
  opacity: 0;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1) 0.3s;
}

.login-actions.actions-animate {
  transform: translateY(0);
  opacity: 1;
}

.login-button {
  background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
  border: none;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.login-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(var(--primary-500), 0.3);
}

.login-button:active {
  transform: translateY(0);
}

.login-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.6s;
}

.login-button:hover::before {
  left: 100%;
}

.sso-section {
  margin-top: 1.5rem;
  transform: translateY(20px);
  opacity: 0;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1) 0.4s;
}

.sso-section.sso-animate {
  transform: translateY(0);
  opacity: 1;
}

.divider {
  display: flex;
  align-items: center;
  margin: 1.5rem 0 1rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--surface-border);
}

.divider span {
  padding: 0 1rem;
}

.sso-button {
  border: 1px solid var(--surface-border);
  transition: all 0.3s ease;
}

.sso-button:hover {
  border-color: var(--primary-400);
  background: rgba(var(--primary-400), 0.05);
  transform: translateY(-1px);
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(var(--red-500), 0.1);
  border: 1px solid rgba(var(--red-500), 0.3);
  border-radius: 0.5rem;
  color: var(--red-400);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transform: translateY(10px);
  opacity: 0;
  transition: all 0.3s ease;
}

.error-message.error-animate {
  transform: translateY(0);
  opacity: 1;
}

.error-message i {
  font-size: 1rem;
}

.version-info {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  opacity: 0;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  z-index: 2;
  transition: all 0.6s ease 0.8s;
}

.version-info.version-animate {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}

/* Input focus animations */
:deep(.p-inputtext:focus),
:deep(.p-password .p-inputtext:focus) {
  box-shadow: 0 0 0 2px rgba(var(--primary-500), 0.2);
  border-color: var(--primary-400);
  transform: scale(1.02);
  transition: all 0.3s ease;
}

:deep(.p-password .p-inputtext:focus) {
  transform: scale(1.02);
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .login-card {
    margin: 1rem;
    padding: 2rem;
  }
  
  .login-container {
    padding: 1rem;
  }
  
  .animated-grid {
    background-size: 30px 30px;
  }
}

/* Dark mode enhancements */
@media (prefers-color-scheme: dark) {
  .login-card {
    background: rgba(var(--surface-card), 0.8);
  }
  
  .particle {
    background: var(--primary-300);
  }
}

/* Reduce motion for accessibility */
@media (prefers-reduced-motion: reduce) {
  .login-card,
  .logo-container,
  .field,
  .login-actions,
  .sso-section,
  .version-info {
    transition: opacity 0.3s ease;
    transform: none !important;
  }
  
  .animated-grid,
  .particle,
  .logo-container i {
    animation: none;
  }
}
</style>
