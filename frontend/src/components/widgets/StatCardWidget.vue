<template>
  <WidgetWrapper :title="widget.title" :editable="editable" @edit="$emit('edit')" @delete="$emit('delete')">
    <div class="stat-container">
      <div class="stat-value">{{ displayValue }}</div>
      <div class="stat-unit" v-if="unit">{{ unit }}</div>
    </div>
  </WidgetWrapper>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import WidgetWrapper from './WidgetWrapper.vue'
import api from '@/services/api'
import type { DashboardWidget, Datapoint } from '@/types'

const props = defineProps<{ widget: DashboardWidget; editable?: boolean; unit?: string }>()
defineEmits<{ edit: []; delete: [] }>()

const latestValue = ref<number | null>(null)
let interval: ReturnType<typeof setInterval> | null = null

async function fetchLatest() {
  if (!props.widget.event_public_id) return
  try {
    const { data } = await api.post<Record<string, Datapoint[]>>('/datapoints/series', {
      event_public_ids: [props.widget.event_public_id],
      minutes: 5,
    })
    const arr = data[props.widget.event_public_id] ?? []
    latestValue.value = arr.length ? arr[arr.length - 1].value : null
  } catch {
    // ignore
  }
}

const displayValue = computed(() => (latestValue.value !== null ? latestValue.value.toFixed(2) : '--'))

onMounted(() => {
  fetchLatest()
  interval = setInterval(fetchLatest, 3000)
})
onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.stat-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--wm-text, #e2e8f0);
}
.stat-unit {
  font-size: 0.85rem;
  color: var(--wm-text-muted, #94a3b8);
  margin-top: 0.25rem;
}
</style>
