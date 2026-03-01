<template>
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div v-if="visible" class="confirm-overlay" @click.self="handleCancel">
        <Transition name="confirm-slide">
          <div v-if="visible" class="confirm-dialog" :class="`confirm-dialog--${options.variant ?? 'info'}`">
            <div class="confirm-icon">
              <i :class="iconClass" />
            </div>
            <h3 class="confirm-title">{{ options.title }}</h3>
            <p class="confirm-message">{{ options.message }}</p>
            <div class="confirm-actions">
              <button class="confirm-btn confirm-btn--cancel" @click="handleCancel">
                {{ options.cancelLabel ?? 'Cancel' }}
              </button>
              <button class="confirm-btn" :class="confirmBtnClass" @click="handleConfirm">
                {{ options.confirmLabel ?? 'Confirm' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const { visible, options, handleConfirm, handleCancel } = useConfirmDialog()

const iconClass = computed(() => {
  if (options.value.icon) return options.value.icon
  switch (options.value.variant) {
    case 'danger': return 'pi pi-exclamation-triangle'
    case 'warning': return 'pi pi-exclamation-circle'
    default: return 'pi pi-question-circle'
  }
})

const confirmBtnClass = computed(() => {
  switch (options.value.variant) {
    case 'danger': return 'confirm-btn--danger'
    case 'warning': return 'confirm-btn--warning'
    default: return 'confirm-btn--primary'
  }
})
</script>

<style lang="scss" scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
  padding: 1rem;
}

.confirm-dialog {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  padding: 2rem;
  width: 100%;
  max-width: 400px;
  box-shadow: var(--wm-shadow-lg);
  text-align: center;
}

.confirm-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  font-size: 1.5rem;

  .confirm-dialog--danger & {
    background: var(--wm-danger-bg);
    color: var(--wm-danger);
  }

  .confirm-dialog--warning & {
    background: var(--wm-warning-bg);
    color: var(--wm-warning);
  }

  .confirm-dialog--info & {
    background: var(--wm-info-bg);
    color: var(--wm-info);
  }
}

.confirm-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--wm-text);
  margin-bottom: 0.5rem;
}

.confirm-message {
  font-size: 0.9rem;
  color: var(--wm-text-secondary);
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.confirm-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.confirm-btn {
  padding: 0.55rem 1.25rem;
  border-radius: var(--wm-radius);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all var(--wm-transition);
  min-width: 100px;

  &--cancel {
    background: var(--wm-bg);
    color: var(--wm-text-secondary);
    border: 1px solid var(--wm-border);

    &:hover { background: var(--wm-border-light); }
  }

  &--danger {
    background: var(--wm-danger);
    color: #fff;
    box-shadow: 0 1px 3px rgba(239, 68, 68, 0.3);

    &:hover { background: #dc2626; transform: translateY(-1px); }
  }

  &--warning {
    background: var(--wm-accent);
    color: #fff;
    box-shadow: 0 1px 3px rgba(245, 158, 11, 0.3);

    &:hover { background: var(--wm-accent-hover); transform: translateY(-1px); }
  }

  &--primary {
    background: var(--wm-primary);
    color: #fff;
    box-shadow: 0 1px 3px rgba(59, 130, 246, 0.3);

    &:hover { background: var(--wm-primary-dark); transform: translateY(-1px); }
  }

  &:active { transform: translateY(0); }
}

/* Mobile: bottom-sheet */
@media (max-width: 768px) {
  .confirm-overlay {
    align-items: flex-end;
    padding: 0;
  }

  .confirm-dialog {
    max-width: 100%;
    border-radius: var(--wm-radius-lg) var(--wm-radius-lg) 0 0;
    padding: 1.5rem;
  }

  .confirm-actions {
    flex-direction: column-reverse;

    .confirm-btn {
      width: 100%;
      min-height: 44px;
    }
  }
}

/* Transitions */
.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 0.2s ease;
}
.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}

.confirm-slide-enter-active {
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.confirm-slide-leave-active {
  transition: all 0.15s ease-in;
}
.confirm-slide-enter-from {
  opacity: 0;
  transform: scale(0.92) translateY(8px);
}
.confirm-slide-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
