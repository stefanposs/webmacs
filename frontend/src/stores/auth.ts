import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import type { User, LoginResponse } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.admin ?? false)

  async function login(email: string, password: string): Promise<void> {
    const { data } = await api.post<LoginResponse>('/auth/login', { email, password })
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    await fetchMe()
  }

  async function fetchMe(): Promise<void> {
    if (!token.value) return
    try {
      const { data } = await api.get<User>('/auth/me')
      user.value = data
    } catch {
      logout()
    }
  }

  async function logout(): Promise<void> {
    try {
      await api.post('/auth/logout')
    } catch {
      // ignore
    }
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  // Hydrate user on store creation
  if (token.value && !user.value) {
    fetchMe()
  }

  return { user, token, isAuthenticated, isAdmin, login, logout, fetchMe }
})
