<template>
  <div class="widget-wrapper">
    <div class="widget-header">
      <span class="widget-title">{{ title }}</span>
      <div class="widget-actions" v-if="editable">
        <button class="widget-btn" @click="$emit('edit')" title="Edit"><i class="pi pi-pencil" /></button>
        <button class="widget-btn widget-btn--danger" @click="$emit('delete')" title="Delete"><i class="pi pi-trash" /></button>
      </div>
    </div>
    <div class="widget-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; editable?: boolean }>()
defineEmits<{ edit: []; delete: [] }>()
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
}
.widget-btn {
  background: none;
  border: none;
  color: var(--wm-text-muted, #94a3b8);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.75rem;
}
.widget-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--wm-text, #e2e8f0);
}
.widget-btn--danger:hover {
  color: #ef4444;
}
.widget-body {
  flex: 1;
  padding: 0.5rem;
  overflow: hidden;
}
</style>
