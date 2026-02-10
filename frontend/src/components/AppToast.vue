<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="n in notifications"
          :key="n.id"
          class="toast-item"
          :class="`toast-item--${n.severity}`"
          @click="remove(n.id)"
        >
          <i :class="iconFor(n.severity)" class="toast-icon" />
          <div class="toast-body">
            <div class="toast-summary">{{ n.summary }}</div>
            <div v-if="n.detail" class="toast-detail">{{ n.detail }}</div>
          </div>
          <button class="toast-close" @click.stop="remove(n.id)" aria-label="Close">
            <i class="pi pi-times" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useNotifications } from '@/composables/useNotification'

const { notifications, remove } = useNotifications()

function iconFor(severity: string): string {
  switch (severity) {
    case 'success': return 'pi pi-check-circle'
    case 'info': return 'pi pi-info-circle'
    case 'warn': return 'pi pi-exclamation-triangle'
    case 'error': return 'pi pi-times-circle'
    default: return 'pi pi-bell'
  }
}
</script>

<style lang="scss" scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 380px;
  width: 100%;
  pointer-events: none;
}

.toast-item {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-radius: var(--wm-radius);
  box-shadow: var(--wm-shadow-lg);
  cursor: pointer;
  backdrop-filter: blur(12px);
  border: 1px solid;
  transition: opacity 0.2s ease, transform 0.15s ease;

  &:hover { transform: translateX(-2px); }

  &--success {
    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
    border-color: #a7f3d0;
    .toast-icon { color: #059669; }
    .toast-summary { color: #065f46; }
    .toast-detail { color: #047857; }
  }

  &--info {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border-color: #93c5fd;
    .toast-icon { color: #2563eb; }
    .toast-summary { color: #1e40af; }
    .toast-detail { color: #1d4ed8; }
  }

  &--warn {
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border-color: #fcd34d;
    .toast-icon { color: #d97706; }
    .toast-summary { color: #92400e; }
    .toast-detail { color: #b45309; }
  }

  &--error {
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    border-color: #fca5a5;
    .toast-icon { color: #dc2626; }
    .toast-summary { color: #991b1b; }
    .toast-detail { color: #b91c1c; }
  }
}

.toast-icon {
  font-size: 1.15rem;
  margin-top: 0.1rem;
  flex-shrink: 0;
}

.toast-body {
  flex: 1;
  min-width: 0;
}

.toast-summary {
  font-weight: 600;
  font-size: 0.875rem;
  line-height: 1.3;
}

.toast-detail {
  font-size: 0.8rem;
  margin-top: 0.15rem;
  opacity: 0.85;
  line-height: 1.4;
}

.toast-close {
  background: none;
  border: none;
  color: inherit;
  opacity: 0.4;
  cursor: pointer;
  padding: 0.15rem;
  font-size: 0.75rem;
  flex-shrink: 0;
  transition: opacity 0.15s;

  &:hover { opacity: 0.8; }
}

/* Transition */
.toast-enter-active {
  animation: toastIn 0.25s ease;
}

.toast-leave-active {
  animation: toastOut 0.2s ease forwards;
}

@keyframes toastIn {
  from {
    opacity: 0;
    transform: translateX(40px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes toastOut {
  from {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateX(40px) scale(0.95);
  }
}
</style>
