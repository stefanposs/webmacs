<template>
  <div class="widget-wrapper" :class="{ 'widget-wrapper--editing': editable }">
    <div class="widget-header">
      <span class="widget-title">{{ title }}</span>
      <div class="widget-actions" v-if="editable">
        <button class="widget-btn" @click="$emit('edit')" title="Edit">
          <i class="pi pi-pencil" />
        </button>
        <button
          v-if="!confirmingDelete"
          class="widget-btn widget-btn--danger"
          @click="startDelete"
          title="Delete"
        >
          <i class="pi pi-trash" />
        </button>
        <button
          v-else
          class="widget-btn widget-btn--confirm"
          @click="$emit('delete')"
          title="Confirm delete"
        >
          <i class="pi pi-exclamation-triangle" /> Confirm?
        </button>
      </div>
    </div>
    <div class="widget-body">
      <Transition name="fade">
        <div v-if="loading" class="widget-loading">
          <i class="pi pi-spin pi-spinner" />
        </div>
      </Transition>
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

defineProps<{ title: string; editable?: boolean; loading?: boolean }>()
defineEmits<{ edit: []; delete: [] }>()

const confirmingDelete = ref(false)
let resetTimeout: ReturnType<typeof setTimeout> | null = null

function startDelete() {
  confirmingDelete.value = true
  if (resetTimeout) clearTimeout(resetTimeout)
  resetTimeout = setTimeout(() => {
    confirmingDelete.value = false
  }, 3000)
}

onUnmounted(() => {
  if (resetTimeout) clearTimeout(resetTimeout)
})
</script>

<style scoped>
.widget-wrapper {
  background: var(--wm-surface, #1e293b);
  border: 1px solid var(--wm-border, #334155);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.widget-wrapper--editing:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.1);
}
.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--wm-border, #334155);
  min-height: 36px;
}
.widget-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--wm-text, #e2e8f0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.widget-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.widget-btn {
  background: none;
  border: none;
  color: var(--wm-text-muted, #94a3b8);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.75rem;
  transition: background 0.15s, color 0.15s;
}
.widget-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--wm-text, #e2e8f0);
}
.widget-btn--danger:hover {
  color: #ef4444;
}
.widget-btn--confirm {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  font-size: 0.7rem;
  padding: 2px 6px;
  display: flex;
  align-items: center;
  gap: 3px;
  animation: pulse-red 1s ease-in-out infinite;
}
@keyframes pulse-red {
  0%, 100% { background: rgba(239, 68, 68, 0.1); }
  50% { background: rgba(239, 68, 68, 0.2); }
}
.widget-body {
  flex: 1;
  padding: 0.5rem;
  overflow: hidden;
  position: relative;
}
.widget-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0.5rem;
  align-items: flex-start;
  z-index: 5;
  font-size: 0.9rem;
  color: #60a5fa;
  pointer-events: none;
}
.widget-loading + * {
  opacity: 0.4;
  transition: opacity 0.2s ease;
}
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>
