<template>
  <div class="login-page">
    <div class="login-glow login-glow--top" />
    <div class="login-glow login-glow--bottom" />

    <div class="login-card">
      <div class="login-logo">
        <i class="pi pi-microchip" />
      </div>
      <h1>WebMACS</h1>
      <p class="login-subtitle">Web-based Monitoring and Control System</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="email">Email</label>
          <div class="input-icon">
            <i class="pi pi-envelope" />
            <input id="email" v-model="email" type="email" placeholder="admin@webmacs.io" required autofocus />
          </div>
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <div class="input-icon">
            <i class="pi pi-lock" />
            <input id="password" v-model="password" type="password" placeholder="••••••••" required />
          </div>
        </div>

        <p v-if="error" class="error-message">
          <i class="pi pi-exclamation-circle" /> {{ error }}
        </p>

        <button type="submit" class="btn-login" :disabled="loading">
          <i v-if="loading" class="pi pi-spin pi-spinner" />
          <i v-else class="pi pi-sign-in" />
          {{ loading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>

      <!-- SSO login -->
      <div v-if="ssoConfig?.enabled" class="sso-divider">
        <span>or</span>
      </div>
      <a v-if="ssoConfig?.enabled" :href="ssoConfig.authorize_url" class="btn-sso">
        <i class="pi pi-shield" />
        Sign in with {{ ssoConfig.provider_name }}
      </a>
    </div>

    <div class="login-footer">
      WebMACS v2.0 &middot; IoT Control Platform
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

interface SsoConfig {
  enabled: boolean
  provider_name: string
  authorize_url: string
}

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const ssoConfig = ref<SsoConfig | null>(null)

onMounted(async () => {
  try {
    const { data } = await api.get<SsoConfig>('/auth/sso/config')
    ssoConfig.value = data
  } catch {
    // SSO config endpoint not available — hide SSO button
  }
})

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    const safeRedirect = redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/'
    router.push(safeRedirect)
  } catch {
    error.value = 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
/* ── Login page: full-bleed dark background ─────────────────────────── */
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  min-height: 100dvh;
  padding: 2rem 1rem;
  /* Solid fallback prevents any light bleed */
  background-color: #0f172a;
  background-image:
    radial-gradient(ellipse at 30% 20%, rgba(59, 130, 246, 0.18) 0%, transparent 55%),
    radial-gradient(ellipse at 70% 80%, rgba(139, 92, 246, 0.12) 0%, transparent 50%),
    linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #0f172a 100%);
  position: relative;
  overflow: hidden;
  isolation: isolate;
}

/* Animated glow orbs */
.login-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  pointer-events: none;
  z-index: 0;
  animation: float 8s ease-in-out infinite;

  &--top {
    width: 500px;
    height: 500px;
    background: rgba(59, 130, 246, 0.25);
    top: -200px;
    left: -100px;
  }

  &--bottom {
    width: 400px;
    height: 400px;
    background: rgba(139, 92, 246, 0.2);
    bottom: -150px;
    right: -100px;
    animation-delay: -4s;
  }
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -20px); }
}

/* ── Card ────────────────────────────────────────────────────────────── */
.login-card {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  padding: 2.5rem 2.5rem 2rem;
  border-radius: 20px;
  box-shadow:
    0 25px 60px -12px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  width: 100%;
  max-width: 400px;
  text-align: center;

  h1 {
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--wm-text);
    margin-bottom: 0.2rem;
    letter-spacing: -0.03em;
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 2rem 1.5rem 1.5rem;
    border-radius: 16px;
  }
}

/* ── Logo ────────────────────────────────────────────────────────────── */
.login-logo {
  width: 60px;
  height: 60px;
  margin: 0 auto 1.25rem;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 6px 20px rgba(59, 130, 246, 0.35),
    0 0 0 4px rgba(59, 130, 246, 0.08);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

  &:hover {
    transform: scale(1.06) rotate(-2deg);
  }

  i {
    font-size: 1.6rem;
    color: #fff;
  }
}

.login-subtitle {
  color: var(--wm-text-muted);
  margin-bottom: 2rem;
  font-size: 0.88rem;
  letter-spacing: 0.01em;
}

/* ── Form ────────────────────────────────────────────────────────────── */
.login-form { text-align: left; }

.input-icon {
  position: relative;

  i {
    position: absolute;
    left: 0.85rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--wm-text-muted);
    font-size: 0.85rem;
    transition: color var(--wm-transition);
  }

  input {
    padding-left: 2.5rem !important;
  }

  &:focus-within i {
    color: var(--wm-primary);
  }
}

.form-group {
  margin-bottom: 1.25rem;

  label {
    display: block;
    font-weight: 600;
    font-size: 0.78rem;
    margin-bottom: 0.4rem;
    color: var(--wm-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  input {
    width: 100%;
    padding: 0.7rem 0.85rem;
    border: 1.5px solid var(--wm-border);
    border-radius: 10px;
    font-size: 0.95rem;
    background: #f8fafc;
    transition: all var(--wm-transition);

    &::placeholder {
      color: #b0bec5;
    }

    &:hover {
      border-color: #cbd5e1;
    }

    &:focus {
      outline: none;
      border-color: var(--wm-primary);
      background: #fff;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
  }
}

.error-message {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--wm-danger);
  font-size: 0.85rem;
  margin-bottom: 1rem;
  padding: 0.5rem 0.75rem;
  background: var(--wm-danger-bg);
  border-radius: var(--wm-radius);
  animation: shake 0.4s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

/* ── Button ──────────────────────────────────────────────────────────── */
.btn-login {
  width: 100%;
  padding: 0.75rem;
  background: linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35);
  margin-top: 0.25rem;

  &:hover:not(:disabled) {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
    transform: translateY(-2px);
  }

  &:active:not(:disabled) { transform: translateY(0); }
  &:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
}

/* ── Footer ──────────────────────────────────────────────────────────── */
.login-footer {
  position: relative;
  z-index: 1;
  margin-top: 2rem;
  font-size: 0.75rem;
  color: rgba(148, 163, 184, 0.7);
  letter-spacing: 0.02em;
}

/* ── SSO ─────────────────────────────────────────────────────────────── */
.sso-divider {
  display: flex;
  align-items: center;
  margin: 1.5rem 0;
  gap: 0.75rem;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--wm-border);
  }

  span {
    color: var(--wm-text-muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
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
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);

  &:hover {
    background: #334155;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    transform: translateY(-1px);
  }

  &:active { transform: translateY(0); }
}
</style>
