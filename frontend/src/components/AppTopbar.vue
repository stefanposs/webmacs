<template>
  <header class="topbar">
    <div class="topbar-left">
        <button class="topbar-hamburger" @click="toggleSidebar" aria-label="Toggle sidebar">
          <i class="pi pi-bars" />
        </button>
        <h1 class="topbar-title">{{ currentRoute }}</h1>
    </div>
    <div class="topbar-right">
      <span class="topbar-env" :class="`topbar-env--${env}`">{{ env }}</span>
      <span class="topbar-clock">{{ clock }}</span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const currentRoute = computed(() => {
  const name = route.name?.toString() ?? ''
  return name.charAt(0).toUpperCase() + name.slice(1)
})
const env = import.meta.env.MODE

const clock = ref('')
let clockTimer: ReturnType<typeof setInterval> | null = null
const uiStore = useUiStore()

function toggleSidebar() {
  uiStore.toggleSidebar()
}

function updateClock() {
  clock.value = new Date().toLocaleTimeString()
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
})
onUnmounted(() => { if (clockTimer) clearInterval(clockTimer) })
</script>

<style lang="scss" scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 2rem;
  background: var(--wm-surface);
  border-bottom: 1px solid var(--wm-border);
  position: sticky;
  top: 0;
  z-index: 50;
}

.topbar-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--wm-text);
  letter-spacing: -0.02em;
}

.topbar-hamburger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 0.75rem;
  background: none;
  border: none;
  color: var(--wm-text);
  font-size: 1.1rem;
}

@media (min-width: 900px) {
  .topbar-hamburger { display: none; }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.topbar-env {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.6rem;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.06em;

  &--development { background: var(--wm-warning-bg); color: #92400e; }
  &--production { background: var(--wm-success-bg); color: #065f46; }
}

.topbar-clock {
  font-size: 0.8rem;
  color: var(--wm-text-muted);
  font-variant-numeric: tabular-nums;
}
</style>
