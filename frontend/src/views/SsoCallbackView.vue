<template>
  <div class="sso-callback-page">
    <div class="sso-callback-card">
      <div class="spinner-wrap" v-if="!error">
        <i class="pi pi-spin pi-spinner" />
        <p>Completing sign-in...</p>
      </div>
      <div class="error-wrap" v-else>
        <i class="pi pi-exclamation-triangle" />
        <p>{{ error }}</p>
        <button class="btn-back" @click="goToLogin">Back to Login</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const error = ref('')

const SSO_TIMEOUT_MS = 15_000

onMounted(async () => {
  const code = route.query.code as string | undefined

  // Immediately strip the code from the URL (prevent leakage)
  window.history.replaceState({}, '', '/sso-callback')

  if (!code) {
    error.value = 'No authorization code received. Please try again.'
    return
  }

  // Race against a timeout
  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error('SSO sign-in timed out. Please try again.')), SSO_TIMEOUT_MS),
  )

  try {
    // Exchange the one-time code for a JWT via POST (code never stays in URL)
    const { data } = await Promise.race([
      api.post<{ access_token: string }>('/auth/sso/exchange', { code }),
      timeout,
    ])

    authStore.token = data.access_token
    localStorage.setItem('access_token', data.access_token)

    await Promise.race([authStore.fetchMe(), timeout])
    router.replace('/')
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to complete SSO sign-in.'
    error.value = message
    localStorage.removeItem('access_token')
    authStore.token = null
  }
})

function goToLogin() {
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.sso-callback-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
}

.sso-callback-card {
  background: #fff;
  padding: 3rem;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
  text-align: center;
  min-width: 300px;
}

.spinner-wrap {
  i {
    font-size: 2rem;
    color: var(--wm-primary, #3b82f6);
  }
  p {
    margin-top: 1rem;
    color: var(--wm-text-muted, #64748b);
    font-size: 0.95rem;
  }
}

.error-wrap {
  i {
    font-size: 2rem;
    color: var(--wm-danger, #ef4444);
  }
  p {
    margin-top: 1rem;
    color: var(--wm-text, #1e293b);
    font-size: 0.95rem;
  }
}

.btn-back {
  margin-top: 1.5rem;
  padding: 0.5rem 1.5rem;
  background: var(--wm-primary, #3b82f6);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover { opacity: 0.85; }
}
</style>
