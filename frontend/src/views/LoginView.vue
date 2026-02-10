<template>
  <div class="login-page">
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
    </div>

    <div class="login-footer">
      WebMACS v2.0 &middot; IoT Control Platform
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    error.value = 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, 0.15) 0%, transparent 60%);
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
  text-align: center;

  h1 {
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--wm-text);
    margin-bottom: 0.2rem;
    letter-spacing: -0.03em;
  }
}

.login-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 1rem;
  background: linear-gradient(135deg, var(--wm-primary) 0%, #6366f1 100%);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);

  i {
    font-size: 1.5rem;
    color: #fff;
  }
}

.login-subtitle {
  color: var(--wm-text-muted);
  margin-bottom: 2rem;
  font-size: 0.9rem;
}

.login-form { text-align: left; }

.input-icon {
  position: relative;

  i {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--wm-text-muted);
    font-size: 0.85rem;
  }

  input {
    padding-left: 2.25rem !important;
  }
}

.form-group {
  margin-bottom: 1.25rem;

  label {
    display: block;
    font-weight: 600;
    font-size: 0.8rem;
    margin-bottom: 0.4rem;
    color: var(--wm-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  input {
    width: 100%;
    padding: 0.65rem 0.8rem;
    border: 1px solid var(--wm-border);
    border-radius: var(--wm-radius);
    font-size: 0.95rem;
    transition: all var(--wm-transition);

    &:focus {
      outline: none;
      border-color: var(--wm-primary);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
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
}

.btn-login {
  width: 100%;
  padding: 0.7rem;
  background: linear-gradient(135deg, var(--wm-primary) 0%, #6366f1 100%);
  color: #fff;
  border: none;
  border-radius: var(--wm-radius);
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--wm-transition);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);

  &:hover {
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.45);
    transform: translateY(-1px);
  }

  &:active { transform: translateY(0); }
  &:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
}

.login-footer {
  position: relative;
  margin-top: 2rem;
  font-size: 0.75rem;
  color: #475569;
}
</style>
