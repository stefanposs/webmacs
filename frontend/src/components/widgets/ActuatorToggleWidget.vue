<template>
  <WidgetWrapper :title="widget.title" :editable="editable" @edit="$emit('edit')" @delete="$emit('delete')">
    <div class="toggle-container">
      <button
        class="toggle-btn"
        :class="{ 'toggle-btn--active': isOn }"
        @click="toggle"
        :disabled="sending"
      >
        <i :class="isOn ? 'pi pi-check' : 'pi pi-times'" />
        {{ isOn ? 'ON' : 'OFF' }}
      </button>
    </div>
  </WidgetWrapper>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import WidgetWrapper from './WidgetWrapper.vue'
import api from '@/services/api'
import type { DashboardWidget, Datapoint } from '@/types'

const props = defineProps<{ widget: DashboardWidget; editable?: boolean }>()
defineEmits<{ edit: []; delete: [] }>()

const isOn = ref(false)
const sending = ref(false)
let interval: ReturnType<typeof setInterval> | null = null

async function fetchState() {
  if (!props.widget.event_public_id) return
  try {
    const { data } = await api.post<Record<string, Datapoint[]>>('/datapoints/series', {
      event_public_ids: [props.widget.event_public_id],
      minutes: 5,
    })
    const arr = data[props.widget.event_public_id] ?? []
    isOn.value = arr.length > 0 && arr[arr.length - 1].value >= 1
  } catch {
    // ignore
  }
}

async function toggle() {
  if (!props.widget.event_public_id || sending.value) return
  sending.value = true
  try {
    await api.post('/datapoints', {
      value: isOn.value ? 0 : 1,
      event_public_id: props.widget.event_public_id,
    })
    isOn.value = !isOn.value
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  fetchState()
  interval = setInterval(fetchState, 3000)
})
onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.toggle-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.toggle-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 2px solid #475569;
  border-radius: 12px;
  background: transparent;
  color: var(--wm-text-muted, #94a3b8);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.toggle-btn:hover {
  border-color: #3b82f6;
}
.toggle-btn--active {
  background: rgba(34, 197, 94, 0.15);
  border-color: #22c55e;
  color: #22c55e;
}
.toggle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
