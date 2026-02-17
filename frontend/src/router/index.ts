import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiredRole?: UserRole
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/sso-callback',
      name: 'sso-callback',
      component: () => import('@/views/SsoCallbackView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/events',
      name: 'events',
      component: () => import('@/views/EventsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/experiments',
      name: 'experiments',
      component: () => import('@/views/ExperimentsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/datapoints',
      name: 'datapoints',
      component: () => import('@/views/DatapointsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('@/views/UsersView.vue'),
      meta: { requiresAuth: true, requiredRole: 'admin' as UserRole },
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('@/views/LogsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/webhooks',
      name: 'webhooks',
      component: () => import('@/views/WebhooksView.vue'),
      meta: { requiresAuth: true, requiredRole: 'admin' as UserRole },
    },
    {
      path: '/rules',
      name: 'rules',
      component: () => import('@/views/RulesView.vue'),
      meta: { requiresAuth: true, requiredRole: 'operator' as UserRole },
    },
    {
      path: '/ota',
      name: 'ota',
      component: () => import('@/views/OtaView.vue'),
      meta: { requiresAuth: true, requiredRole: 'admin' as UserRole },
    },
    {
      path: '/dashboards',
      name: 'dashboards',
      component: () => import('@/views/DashboardsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboards/:id',
      name: 'dashboard-custom',
      component: () => import('@/views/DashboardCustomView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/plugins',
      name: 'plugins',
      component: () => import('@/views/PluginsView.vue'),
      meta: { requiresAuth: true, requiredRole: 'admin' as UserRole },
    },
    {
      path: '/plugins/packages',
      name: 'plugin-packages',
      component: () => import('@/views/PluginPackagesView.vue'),
      meta: { requiresAuth: true, requiredRole: 'admin' as UserRole },
    },
    {
      path: '/plugins/:id',
      name: 'plugin-detail',
      component: () => import('@/views/PluginDetailView.vue'),
      meta: { requiresAuth: true, requiredRole: 'admin' as UserRole },
    },
    {
      path: '/tokens',
      name: 'tokens',
      component: () => import('@/views/TokensView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiredRole && !auth.hasRole(to.meta.requiredRole)) {
    return { name: 'dashboard' }
  }
})

export default router
