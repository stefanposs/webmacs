<template>
  <AppToast />
  <div class="layout-wrapper">
    <AppSidebar v-if="authStore.isAuthenticated && uiStore.sidebarOpen" />
    <div :class="['layout-main', { 'layout-main--full': !authStore.isAuthenticated || !uiStore.sidebarOpen }]">
      <AppTopbar v-if="authStore.isAuthenticated" />
      <main class="layout-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import AppToast from '@/components/AppToast.vue'

const authStore = useAuthStore()
const uiStore = useUiStore()
</script>

<style lang="scss">
.layout-wrapper {
  display: flex;
  min-height: 100vh;
}

.layout-main {
  flex: 1;
  margin-left: var(--wm-sidebar-width);
  transition: margin-left 0.3s ease;

  &--full {
    margin-left: 0;
  }
}

.layout-content {
  padding: 1.75rem 2rem;
  max-width: 1400px;
}

/* Mobile layout overrides */
@media (max-width: 768px) {
  .layout-main {
    margin-left: 0 !important;
  }

  .layout-content {
    padding: 1rem 0.75rem;
  }
}

@media (min-width: 769px) and (max-width: 899px) {
  .layout-content {
    padding: 1.25rem 1.25rem;
  }
}

/* Page transition */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-leave-to {
  opacity: 0;
}
</style>
