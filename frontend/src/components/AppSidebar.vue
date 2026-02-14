<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-logo">
        <i class="pi pi-microchip" />
        <div>
          <h2>WebMACS</h2>
          <span class="sidebar-version">v2.0</span>
        </div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="sidebar-section-label">Main</div>
      <router-link
        v-for="item in mainItems"
        :key="item.to"
        :to="item.to"
        class="sidebar-link"
        active-class="sidebar-link--active"
        exact-active-class="sidebar-link--exact"
      >
        <i :class="item.icon" />
        <span>{{ item.label }}</span>
      </router-link>

      <div class="sidebar-section-label">Data</div>
      <router-link
        v-for="item in dataItems"
        :key="item.to"
        :to="item.to"
        class="sidebar-link"
        active-class="sidebar-link--active"
      >
        <i :class="item.icon" />
        <span>{{ item.label }}</span>
      </router-link>

      <template v-if="authStore.isAdmin">
        <div class="sidebar-section-label">Automation</div>
        <router-link to="/rules" class="sidebar-link" active-class="sidebar-link--active">
          <i class="pi pi-bolt" />
          <span>Rules</span>
        </router-link>

        <div class="sidebar-section-label">System</div>
        <router-link to="/plugins" class="sidebar-link" active-class="sidebar-link--active">
          <i class="pi pi-microchip" />
          <span>Plugins</span>
        </router-link>
        <router-link to="/webhooks" class="sidebar-link" active-class="sidebar-link--active">
          <i class="pi pi-link" />
          <span>Webhooks</span>
        </router-link>
        <router-link to="/ota" class="sidebar-link" active-class="sidebar-link--active">
          <i class="pi pi-cloud-download" />
          <span>OTA Updates</span>
        </router-link>

        <div class="sidebar-section-label">Admin</div>
        <router-link to="/users" class="sidebar-link" active-class="sidebar-link--active">
          <i class="pi pi-users" />
          <span>Users</span>
        </router-link>
      </template>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-user">
        <div class="sidebar-avatar">{{ initials }}</div>
        <div class="sidebar-user-info">
          <span class="sidebar-username">{{ authStore.user?.username }}</span>
          <span class="sidebar-role">{{ authStore.isAdmin ? 'Admin' : 'User' }}</span>
        </div>
      </div>
      <button class="btn-logout" @click="handleLogout" title="Sign out">
        <i class="pi pi-sign-out" />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const initials = computed(() => {
  const name = authStore.user?.username ?? '?'
  return name.slice(0, 2).toUpperCase()
})

const mainItems = [
  { to: '/', label: 'Dashboard', icon: 'pi pi-objects-column' },
  { to: '/events', label: 'Events', icon: 'pi pi-bolt' },
  { to: '/experiments', label: 'Experiments', icon: 'pi pi-play-circle' },
]

const dataItems = [
  { to: '/datapoints', label: 'Datapoints', icon: 'pi pi-chart-line' },
  { to: '/dashboards', label: 'Dashboards', icon: 'pi pi-th-large' },
  { to: '/logs', label: 'Logs', icon: 'pi pi-file-edit' },
]

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'login' })
}
</script>

<style lang="scss" scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--wm-sidebar-width);
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  color: #cbd5e1;
  display: flex;
  flex-direction: column;
  z-index: 100;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
}

.sidebar-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;

  > i {
    font-size: 1.5rem;
    color: var(--wm-primary);
  }

  h2 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.02em;
  }
}

.sidebar-version {
  font-size: 0.6rem;
  background: var(--wm-primary);
  color: #fff;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.sidebar-nav {
  flex: 1;
  padding: 0.5rem 0;
  overflow-y: auto;
}

.sidebar-section-label {
  padding: 1rem 1.5rem 0.4rem;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #475569;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 1.5rem;
  margin: 0.1rem 0.5rem;
  border-radius: var(--wm-radius);
  transition: all 0.15s ease;
  font-size: 0.9rem;
  font-weight: 500;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #f1f5f9;
  }

  &--active {
    background: rgba(59, 130, 246, 0.15);
    color: var(--wm-primary);

    i { color: var(--wm-primary); }
  }

  i { font-size: 1rem; width: 1.1rem; text-align: center; }
}

.sidebar-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.sidebar-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--wm-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
}

.sidebar-user-info {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.sidebar-username {
  font-size: 0.8rem;
  font-weight: 600;
  color: #e2e8f0;
}

.sidebar-role {
  font-size: 0.65rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.btn-logout {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.4rem;
  border-radius: var(--wm-radius);
  transition: all 0.15s ease;

  &:hover { color: #f1f5f9; background: rgba(239, 68, 68, 0.2); }
}
</style>
