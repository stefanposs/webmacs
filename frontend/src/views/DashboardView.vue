<template>
  <div class="dashboard">
    <!-- Stats bar -->
    <div class="stats-bar">
      <div class="stat-card">
        <i class="pi pi-bolt stat-icon stat-icon--sensor" />
        <div>
          <div class="stat-value">{{ sensorEvents.length }}</div>
          <div class="stat-label">Sensors</div>
        </div>
      </div>
      <div class="stat-card">
        <i class="pi pi-cog stat-icon stat-icon--actuator" />
        <div>
          <div class="stat-value">{{ actuatorEvents.length }}</div>
          <div class="stat-label">Actuators</div>
        </div>
      </div>
      <div class="stat-card">
        <i class="pi pi-sliders-h stat-icon stat-icon--range" />
        <div>
          <div class="stat-value">{{ rangeEvents.length }}</div>
          <div class="stat-label">Range Controls</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-pulse" :class="{ 'stat-pulse--active': isConnected || connectionMode === 'polling' }" />
        <div>
          <div class="stat-value">{{ connectionMode === 'websocket' ? 'Live' : connectionMode === 'polling' ? 'Poll' : '...' }}</div>
          <div class="stat-label">{{ connectionMode === 'websocket' ? 'WebSocket' : connectionMode === 'polling' ? `${(1.5)}s HTTP` : 'Connecting' }}</div>
        </div>
      </div>
    </div>

    <!-- Sensor Cards -->
    <section class="dashboard-section">
      <h2 class="section-title"><i class="pi pi-bolt" /> Sensors</h2>
      <div class="card-grid">
        <div v-for="sensor in sensorEvents" :key="sensor.public_id" class="sensor-card">
          <div class="sensor-header">
            <span class="sensor-name">{{ sensor.name }}</span>
            <span class="sensor-unit">{{ sensor.unit }}</span>
          </div>
          <div class="sensor-value">{{ formatNumber(getLatestRaw(sensor.public_id), 2) }}</div>
          <div class="sensor-range">
            <span>{{ sensor.min_value }}</span>
            <div class="sensor-bar">
              <div
                class="sensor-bar-fill"
                :style="{ width: getBarPercent(sensor) + '%' }"
              />
            </div>
            <span>{{ sensor.max_value }}</span>
          </div>
        </div>
        <div v-if="sensorEvents.length === 0" class="empty-state">
          <i class="pi pi-bolt" />
          No sensor events configured.
        </div>
      </div>
    </section>

    <!-- Actuator Controls -->
    <section class="dashboard-section">
      <h2 class="section-title"><i class="pi pi-cog" /> Actuators</h2>
      <div class="card-grid">
        <div v-for="actuator in actuatorEvents" :key="actuator.public_id" class="actuator-card">
          <div class="actuator-header">{{ actuator.name }}</div>
          <button class="btn-toggle" :class="{ 'btn-toggle--active': isActive(actuator.public_id) }" @click="toggleActuator(actuator)">
            <i :class="isActive(actuator.public_id) ? 'pi pi-check' : 'pi pi-times'" />
            {{ isActive(actuator.public_id) ? 'ON' : 'OFF' }}
          </button>
        </div>
        <div v-if="actuatorEvents.length === 0" class="empty-state">
          <i class="pi pi-cog" />
          No actuator events configured.
        </div>
      </div>
    </section>

    <!-- Range Controls -->
    <section class="dashboard-section">
      <h2 class="section-title"><i class="pi pi-sliders-h" /> Range Controls</h2>
      <div class="card-grid">
        <div v-for="range in rangeEvents" :key="range.public_id" class="range-card">
          <div class="range-header">{{ range.name }}</div>
          <input type="range" :min="range.min_value" :max="range.max_value" :value="getLatestRaw(range.public_id)" @change="onRangeChange($event, range)" />
          <div class="range-value-label">{{ formatNumber(getLatestRaw(range.public_id), 1) }} <small>{{ range.unit }}</small></div>
        </div>
        <div v-if="rangeEvents.length === 0" class="empty-state">
          <i class="pi pi-sliders-h" />
          No range events configured.
        </div>
      </div>
    </section>

    <!-- Live Chart -->
    <section class="dashboard-section" v-if="sensorEvents.length > 0">
      <h2 class="section-title"><i class="pi pi-chart-line" /> Live Data</h2>
      <div class="chart-container">
        <Line :data="chartData" :options="chartOptions" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { useEventStore } from '@/stores/events'
import { useDatapointStore } from '@/stores/datapoints'
import { useRealtimeDatapoints } from '@/composables/useRealtimeDatapoints'
import { useFormatters } from '@/composables/useFormatters'
import type { Event } from '@/types'
import { EventType } from '@/types'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const eventStore = useEventStore()
const datapointStore = useDatapointStore()
const { formatNumber } = useFormatters()
const { latestDatapoints: realtimeDatapoints, connectionMode, isConnected } = useRealtimeDatapoints(1500)

const chartHistory = ref<Record<string, { time: string; value: number }[]>>({})

const sensorEvents = computed(() => eventStore.events.filter((e) => e.type === EventType.sensor))
const actuatorEvents = computed(() => eventStore.events.filter((e) => e.type === EventType.actuator))
const rangeEvents = computed(() => eventStore.events.filter((e) => e.type === EventType.range))

function getLatestRaw(publicId: string): number | null {
  // Prefer real-time data, fall back to store
  const dp = realtimeDatapoints.value.find((d) => d.event_public_id === publicId)
    ?? datapointStore.latestDatapoints.find((d) => d.event_public_id === publicId)
  return dp?.value ?? null
}

function getBarPercent(sensor: Event): number {
  const val = getLatestRaw(sensor.public_id)
  if (val == null) return 0
  const range = sensor.max_value - sensor.min_value
  if (range === 0) return 0
  return Math.max(0, Math.min(100, ((val - sensor.min_value) / range) * 100))
}

function isActive(publicId: string): boolean {
  const val = getLatestRaw(publicId)
  return val === 1 || val === 1.0
}

async function toggleActuator(event: Event) {
  const current = isActive(event.public_id)
  try {
    await datapointStore.createDatapoint({ event_public_id: event.public_id, value: current ? 0 : 1 })
    await datapointStore.fetchLatest()
  } catch {
    // best-effort, real-time update will catch up
  }
}

async function onRangeChange(ev: globalThis.Event, event: Event) {
  const target = ev.target as HTMLInputElement
  try {
    await datapointStore.createDatapoint({ event_public_id: event.public_id, value: parseFloat(target.value) })
    await datapointStore.fetchLatest()
  } catch {
    // best-effort
  }
}

const CHART_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']

const chartData = computed(() => {
  const labels = chartHistory.value[sensorEvents.value[0]?.public_id]?.map((h) => h.time) ?? []
  return {
    labels,
    datasets: sensorEvents.value.map((sensor, idx) => ({
      label: sensor.name,
      data: chartHistory.value[sensor.public_id]?.map((h) => h.value) ?? [],
      borderColor: CHART_COLORS[idx % CHART_COLORS.length],
      backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] + '15',
      tension: 0.4,
      fill: true,
      pointRadius: 0,
      borderWidth: 2,
    })),
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  interaction: { mode: 'index' as const, intersect: false },
  plugins: {
    legend: { position: 'bottom' as const, labels: { usePointStyle: true, padding: 20 } },
  },
  scales: {
    x: { display: true, grid: { display: false } },
    y: { beginAtZero: false, grid: { color: '#f1f5f9' } },
  },
}

function recordHistory() {
  const now = new Date().toLocaleTimeString()
  for (const sensor of sensorEvents.value) {
    const val = getLatestRaw(sensor.public_id)
    if (val != null) {
      if (!chartHistory.value[sensor.public_id]) {
        chartHistory.value[sensor.public_id] = []
      }
      const arr = chartHistory.value[sensor.public_id]
      arr.push({ time: now, value: val })
      if (arr.length > 60) arr.shift()
    }
  }
}

// Record chart history whenever real-time data updates
watch(realtimeDatapoints, recordHistory, { deep: true })

onMounted(async () => {
  await eventStore.fetchEvents()
  await datapointStore.fetchLatest()
})
</script>

<style lang="scss" scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

/* Stats bar */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--wm-surface);
  padding: 1rem 1.25rem;
  border-radius: var(--wm-radius-lg);
  box-shadow: var(--wm-shadow-sm);
}

.stat-icon {
  font-size: 1.5rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--wm-radius);

  &--sensor { background: var(--wm-info-bg); color: #3b82f6; }
  &--actuator { background: var(--wm-success-bg); color: #10b981; }
  &--range { background: var(--wm-warning-bg); color: #f59e0b; }
}

.stat-value { font-size: 1.25rem; font-weight: 700; color: var(--wm-text); }
.stat-label { font-size: 0.75rem; color: var(--wm-text-muted); }

.stat-pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--wm-text-muted);
  margin-left: 0.5rem;

  &--active {
    background: var(--wm-success);
    animation: pulse 1.5s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
  50% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
}

/* Sections */
.dashboard-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--wm-text);
  display: flex;
  align-items: center;
  gap: 0.5rem;

  i {
    font-size: 0.9rem;
    color: var(--wm-text-muted);
  }
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

/* Sensor cards */
.sensor-card {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  padding: 1.25rem;
  box-shadow: var(--wm-shadow);
  transition: box-shadow var(--wm-transition);

  &:hover { box-shadow: var(--wm-shadow-md); }
}

.sensor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.sensor-name { font-weight: 600; font-size: 0.9rem; color: var(--wm-text); }
.sensor-unit { color: var(--wm-text-muted); font-size: 0.8rem; }

.sensor-value {
  font-size: 2.25rem;
  font-weight: 800;
  color: var(--wm-primary);
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  margin-bottom: 0.75rem;
}

.sensor-range {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.7rem;
  color: var(--wm-text-muted);
}

.sensor-bar {
  flex: 1;
  height: 4px;
  background: var(--wm-border-light);
  border-radius: 2px;
  overflow: hidden;
}

.sensor-bar-fill {
  height: 100%;
  background: var(--wm-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* Actuator cards */
.actuator-card {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  padding: 1.25rem;
  box-shadow: var(--wm-shadow);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.actuator-header { font-weight: 600; font-size: 0.9rem; color: var(--wm-text); }

.btn-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1.5rem;
  border: 2px solid var(--wm-border);
  border-radius: 9999px;
  background: var(--wm-bg);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &--active {
    background: var(--wm-success);
    border-color: var(--wm-success);
    color: #fff;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.35);
  }
}

/* Range cards */
.range-card {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  padding: 1.25rem;
  box-shadow: var(--wm-shadow);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;

  input[type='range'] {
    width: 100%;
    accent-color: var(--wm-primary);
  }
}

.range-header { font-weight: 600; font-size: 0.9rem; color: var(--wm-text); }

.range-value-label {
  text-align: center;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--wm-primary);

  small {
    font-size: 0.75rem;
    color: var(--wm-text-muted);
    font-weight: 500;
  }
}

/* Chart */
.chart-container {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  padding: 1.5rem;
  box-shadow: var(--wm-shadow);
  height: 380px;
}

/* Empty state */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--wm-text-muted);
  padding: 2.5rem 2rem;
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  box-shadow: var(--wm-shadow-sm);

  i {
    display: block;
    font-size: 2rem;
    margin-bottom: 0.5rem;
    opacity: 0.4;
  }
}
</style>
