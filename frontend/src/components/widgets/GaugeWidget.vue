<template>
  <WidgetWrapper :title="widget.title" :editable="editable" @edit="$emit('edit')" @delete="$emit('delete')">
    <div class="gauge-container">
      <svg viewBox="0 0 120 80" class="gauge-svg">
        <!-- Background arc -->
        <path :d="bgArc" fill="none" stroke="#334155" stroke-width="10" stroke-linecap="round" />
        <!-- Value arc -->
        <path :d="valueArc" fill="none" :stroke="color" stroke-width="10" stroke-linecap="round" />
      </svg>
      <div class="gauge-value">{{ displayValue }}<small v-if="unit"> {{ unit }}</small></div>
    </div>
  </WidgetWrapper>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import WidgetWrapper from './WidgetWrapper.vue'
import api from '@/services/api'
import type { DashboardWidget, Datapoint } from '@/types'

const props = defineProps<{ widget: DashboardWidget; editable?: boolean; min?: number; max?: number; unit?: string }>()
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

const minVal = computed(() => props.min ?? 0)
const maxVal = computed(() => props.max ?? 100)

const pct = computed(() => {
  if (latestValue.value === null) return 0
  return Math.max(0, Math.min(1, (latestValue.value - minVal.value) / (maxVal.value - minVal.value || 1)))
})

const displayValue = computed(() => (latestValue.value !== null ? latestValue.value.toFixed(1) : '--'))

const color = computed(() => {
  const p = pct.value
  if (p < 0.5) return '#22c55e'
  if (p < 0.8) return '#eab308'
  return '#ef4444'
})

function polarToCartesian(cx: number, cy: number, r: number, angle: number) {
  const rad = ((angle - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function arc(startAngle: number, endAngle: number) {
  const cx = 60,
    cy = 60,
    r = 45
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArc = endAngle - startAngle > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`
}

const bgArc = computed(() => arc(-120, 120))
const valueArc = computed(() => {
  const sweep = pct.value * 240
  return sweep > 0 ? arc(-120, -120 + sweep) : ''
})

onMounted(() => {
  fetchLatest()
  interval = setInterval(fetchLatest, 3000)
})
onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.gauge-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.gauge-svg {
  width: 100%;
  max-width: 160px;
}
.gauge-value {
  margin-top: -0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--wm-text, #e2e8f0);
}
.gauge-value small {
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--wm-text-muted, #94a3b8);
}
</style>
