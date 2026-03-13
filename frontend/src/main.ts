import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// PrimeVue imports
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Aura from '@primevue/themes/aura'

// PrimeVue icons & custom styles
import 'primeicons/primeicons.css'

// Custom styles
import './assets/styles/main.scss'

const app = createApp(App)

const pinia = createPinia()
app.use(pinia)

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.dark-mode',
      cssLayer: false,
    },
  },
})
app.use(ConfirmationService)
app.use(ToastService)
app.use(router)

// Initialize auto-login on app start
router.isReady().then(async () => {
  // Import and initialize auto-login after router is ready
  const { useAutoLogin } = await import('./composables/useAutoLogin')
  const autoLogin = useAutoLogin()
  
  // Only initialize auto-login if we're on the login page or being redirected
  const currentRoute = router.currentRoute.value
  if (currentRoute.name === 'login' || currentRoute.query.redirect) {
    await autoLogin.initializeAutoLogin()
  }
})

app.mount('#app')
