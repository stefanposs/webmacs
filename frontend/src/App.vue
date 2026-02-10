<template>
  <AppToast />
  <div class="layout-wrapper">
    <AppSidebar v-if="authStore.isAuthenticated" />
    <div :class="['layout-main', { 'layout-main--full': !authStore.isAuthenticated }]">
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
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import AppToast from '@/components/AppToast.vue'

const authStore = useAuthStore()
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
