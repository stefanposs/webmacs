import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: attach JWT + prevent browser caching of GET requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Bust browser cache on GET requests so mutations are always visible
  if (config.method === 'get' || !config.method) {
    config.params = { ...config.params, _t: Date.now() }
  }
  return config
})

// Response interceptor: handle 401 + structured error extraction
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      router.push({ name: 'login' })
    }
    // Extract backend detail message for cleaner error propagation
    const detail = error.response?.data?.detail
    if (detail && typeof detail === 'string') {
      error.message = detail
    }
    return Promise.reject(error)
  },
)

export default api
