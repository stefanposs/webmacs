<template>
  <WidgetWrapper :title="widget.title" :editable="editable" :loading="loading" @edit="$emit('edit')" @delete="$emit('delete')">
    <Line v-if="chartData" :data="chartData" :options="chartOptions" class="chart-canvas" />
    <div v-else-if="!loading" class="widget-empty">No data</div>
  </WidgetWrapper>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
} from 'chart.js'
import WidgetWrapper from './WidgetWrapper.vue'
import api from '@/services/api'
import type { DashboardWidget, Datapoint } from '@/types'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler)

const props = defineProps<{ widget: DashboardWidget; editable?: boolean; timeRangeMinutes?: number }>()
defineEmits<{ edit: []; delete: [] }>()

const series = ref<Datapoint[]>([])
const loading = ref(true)
let interval: ReturnType<typeof setInterval> | null = null

async function fetchSeries() {
  if (!props.widget.event_public_id) {
    loading.value = false
    return
  }
  try {
    const minutes = props.timeRangeMinutes ?? 60
    const { data } = await api.post<Record<string, Datapoint[]>>('/datapoints/series', {
      event_public_ids: [props.widget.event_public_id],
      minutes,
      max_points: minutes > 360 ? 300 : 500,
    })
    series.value = data[props.widget.event_public_id] ?? []
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

watch(() => props.timeRangeMinutes, () => {
  loading.value = true
  fetchSeries()
})

const chartData = computed(() => {
  if (!series.value.length) return null
  return {
    labels: series.value.map((d) =>
      d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : '',
    ),
    datasets: [
      {
        label: props.widget.title,
        data: series.value.map((d) => d.value),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      },
    ],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: { display: false },
    y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: 'rgba(148,163,184,0.1)' } },
  },
  plugins: { tooltip: { enabled: true }, legend: { display: false } },
  animation: { duration: 300 },
}

onMounted(() => {
  fetchSeries()
  interval = setInterval(fetchSeries, 5000)
})
onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped>
.widget-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--wm-text-muted, #94a3b8);
  font-size: 0.85rem;
}
</style>
