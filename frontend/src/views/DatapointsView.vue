<template>
  <div class="view-datapoints">
    <div class="view-header">
      <h2>Datapoints</h2>
      <span class="total-badge" v-if="datapointStore.total">{{ datapointStore.total.toLocaleString() }} total</span>
      <div class="view-mode-toggle">
        <button class="btn-mode" :class="{ 'btn-mode--active': viewMode === 'table' }" @click="viewMode = 'table'">
          <i class="pi pi-table" /> Table
        </button>
        <button class="btn-mode" :class="{ 'btn-mode--active': viewMode === 'live' }" @click="viewMode = 'live'">
          <i class="pi pi-bolt" /> Live Tail
        </button>
      </div>
    </div>

    <!-- Plugin state banners -->
    <div v-if="showNoPlugin" class="plugin-hint plugin-hint--amber">
      <i class="pi pi-info-circle plugin-hint__icon" />
      <div class="plugin-hint__content">
        <strong>No plugin configured</strong>
        <span>Datapoints are only recorded when a plugin is configured and enabled. Set up a device plugin to start collecting data.</span>
      </div>
      <router-link to="/plugins" class="plugin-hint__action">
        <i class="pi pi-arrow-right" /> Configure Plugins
      </router-link>
    </div>
    <div v-else-if="showDisabledBanner" class="plugin-hint plugin-hint--orange">
      <i class="pi pi-pause-circle plugin-hint__icon" />
      <div class="plugin-hint__content">
        <strong>Plugin disabled</strong>
        <span>{{ disabledPluginName }} is disabled. No new datapoints will be recorded. Enable it to resume data collection.</span>
      </div>
      <router-link to="/plugins" class="plugin-hint__action plugin-hint__action--outline">
        <i class="pi pi-arrow-right" /> Manage Plugins
      </router-link>
    </div>
    <div v-else-if="showDemoBanner" class="plugin-hint plugin-hint--blue">
      <i class="pi pi-play-circle plugin-hint__icon" />
      <div class="plugin-hint__content">
        <strong>Demo Mode</strong>
        <span>{{ demoPluginName }} is running in demo mode with simulated data.</span>
      </div>
      <router-link to="/plugins" class="plugin-hint__action plugin-hint__action--blue">
        <i class="pi pi-arrow-right" /> Manage Plugins
      </router-link>
    </div>

    <!-- Stream Controls (shown in Live Tail mode) -->
    <div v-if="viewMode === 'live'" class="stream-controls">
      <button class="btn-pause" :class="{ 'btn-pause--active': isPaused }" @click="togglePause" :title="isPaused ? 'Resume live updates' : 'Pause live updates'" :aria-label="isPaused ? 'Resume live updates' : 'Pause live updates'">
        <i :class="isPaused ? 'pi pi-play' : 'pi pi-pause'" />
        {{ isPaused ? 'Resume' : 'Pause' }}
      </button>
      <div class="throttle-control">
        <label class="throttle-label">Update interval:</label>
        <select class="throttle-select" :value="throttleMs" @change="onThrottleChange">
          <option :value="250">0.25s</option>
          <option :value="500">0.5s</option>
          <option :value="1000">1s</option>
          <option :value="2000">2s</option>
          <option :value="5000">5s</option>
        </select>
      </div>
      <div class="connection-badge" :class="{ 'connection-badge--live': isConnected || connectionMode === 'polling' }">
        <div class="connection-dot" />
        {{ connectionMode === 'websocket' ? 'WebSocket' : connectionMode === 'polling' ? 'Polling' : 'Connecting…' }}
      </div>
      <span v-if="isPaused" class="pause-indicator"><i class="pi pi-info-circle" /> Paused — data still being collected</span>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="filter-group">
        <i class="pi pi-search filter-icon" />
        <input v-model="searchQuery" type="text" class="filter-input" placeholder="Search by event name, ID, or value…" aria-label="Search datapoints" />
      </div>
      <select v-model="filterEventId" class="filter-select" aria-label="Filter by event">
        <option value="">All Events</option>
        <option v-for="ev in eventStore.events" :key="ev.public_id" :value="ev.public_id">
          {{ ev.name }} ({{ ev.type }})
        </option>
      </select>
      <select v-if="viewMode === 'table'" v-model="pageSize" class="filter-select filter-select--sm" @change="onPageSizeChange">
        <option :value="25">25 / page</option>
        <option :value="50">50 / page</option>
        <option :value="100">100 / page</option>
        <option :value="200">200 / page</option>
      </select>
      <button v-if="viewMode === 'table'" class="btn-export" @click="exportCsv" title="Export as CSV">
        <i class="pi pi-download" /> CSV
      </button>
    </div>

    <!-- Loading -->
    <div v-if="datapointStore.loading && viewMode === 'table'" class="loading"><i class="pi pi-spin pi-spinner" /> Loading datapoints...</div>

    <!-- Live Tail Mode -->
    <div v-else-if="viewMode === 'live'">
      <table v-if="filteredLiveDatapoints.length" class="data-table data-table--live" aria-label="Live datapoints">
        <thead>
          <tr>
            <th>Event</th>
            <th>Value</th>
            <th>Last Updated</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="dp in filteredLiveDatapoints"
            :key="dp.event_public_id"
            class="live-row"
            :class="getChangeClass(dp.event_public_id)"
          >
            <td>
              <span class="event-name">{{ getEventName(dp.event_public_id) }}</span>
              <span class="event-type-badge">{{ getEventType(dp.event_public_id) }}</span>
            </td>
            <td class="value-cell">
              <strong>{{ formatNumber(dp.value) }}</strong>
              <span class="value-unit">{{ getEventUnit(dp.event_public_id) }}</span>
            </td>
            <td class="mono">{{ formatRelativeTime(dp.timestamp) }}</td>
            <td class="change-cell">
              <span v-if="getValueDelta(dp.event_public_id) !== null" :class="getDeltaClass(dp.event_public_id)">
                <i :class="getDeltaIcon(dp.event_public_id)" />
                {{ formatDelta(dp.event_public_id) }}
              </span>
              <span v-else class="text-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        <i class="pi pi-bolt" />
        Waiting for live datapoints…
      </div>
    </div>

    <!-- Table Mode (paginated) -->
    <template v-else>
      <table v-if="filteredTableDatapoints.length" class="data-table" aria-label="Datapoints table">
        <thead>
          <tr>
            <th>Public ID</th>
            <th>Event</th>
            <th>Value</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="dp in filteredTableDatapoints" :key="dp.public_id">
            <td class="mono">{{ dp.public_id.slice(0, 8) }}…</td>
            <td>
              <span class="event-name">{{ getEventName(dp.event_public_id) }}</span>
              <span class="event-type-badge">{{ getEventType(dp.event_public_id) }}</span>
            </td>
            <td><strong>{{ formatNumber(dp.value) }}</strong></td>
            <td>{{ formatDate(dp.timestamp) }}</td>
          </tr>
        </tbody>
      </table>

      <div v-else class="empty-state">
        <i class="pi pi-chart-line" />
        No datapoints recorded yet.
      </div>

      <div class="pagination">
        <button class="btn-secondary" :disabled="page <= 1" @click="changePage(-1)">
          <i class="pi pi-chevron-left" /> Previous
        </button>
        <span>Page {{ page }} <small v-if="totalPages > 0">of {{ totalPages }}</small></span>
        <button class="btn-secondary" :disabled="page >= totalPages" @click="changePage(1)">
          Next <i class="pi pi-chevron-right" />
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useDatapointStore } from '@/stores/datapoints'
import { usePluginStore } from '@/stores/plugins'
import { useEventStore } from '@/stores/events'
import { useRealtimeDatapoints } from '@/composables/useRealtimeDatapoints'
import { useFormatters } from '@/composables/useFormatters'
import type { Datapoint } from '@/types'

const datapointStore = useDatapointStore()
const pluginStore = usePluginStore()
const eventStore = useEventStore()
const { formatDate, formatRelativeTime, formatNumber } = useFormatters()

// ─── View mode ──────────────────────────────────────────────────
const viewMode = ref<'table' | 'live'>('live')
const page = ref(1)
const pageSize = ref(50)
const searchQuery = ref('')
const filterEventId = ref('')

// ─── Realtime composable ────────────────────────────────────────
const { latestDatapoints, connectionMode, isConnected, isPaused, togglePause, throttleMs, setThrottleMs } = useRealtimeDatapoints(1500)

// ─── Change tracking with CSS animation triggers ────────────────
const previousValues = ref<Map<string, number>>(new Map())
const changeTimestamps = ref<Map<string, { time: number; direction: 'up' | 'down' }>>(new Map())

watch(latestDatapoints, (newDps, oldDps) => {
  // 1. Build previous values map from oldDps
  const oldMap = new Map<string, number>()
  if (oldDps) {
    for (const dp of oldDps) {
      oldMap.set(dp.event_public_id, dp.value)
    }
  }

  // 2. Track changes and schedule highlight removal
  const now = Date.now()
  for (const dp of newDps) {
    const prev = oldMap.get(dp.event_public_id)
    if (prev !== undefined && prev !== dp.value) {
      changeTimestamps.value.set(dp.event_public_id, {
        time: now,
        direction: dp.value > prev ? 'up' : 'down',
      })
      // Auto-remove highlight after animation completes
      const eventId = dp.event_public_id
      setTimeout(() => {
        changeTimestamps.value.delete(eventId)
      }, 2000)
    }
  }

  previousValues.value = oldMap
})

function getChangeClass(eventPublicId: string): string {
  const change = changeTimestamps.value.get(eventPublicId)
  if (!change) return ''
  return change.direction === 'up' ? 'row-flash--up' : 'row-flash--down'
}

function getValueDelta(eventPublicId: string): number | null {
  const current = latestDatapoints.value.find(d => d.event_public_id === eventPublicId)
  const prev = previousValues.value.get(eventPublicId)
  if (!current || prev === undefined) return null
  return current.value - prev
}

function formatDelta(eventPublicId: string): string {
  const delta = getValueDelta(eventPublicId)
  if (delta === null) return '—'
  const sign = delta >= 0 ? '+' : ''
  return `${sign}${delta.toFixed(2)}`
}

function getDeltaClass(eventPublicId: string): string {
  const delta = getValueDelta(eventPublicId)
  if (delta === null || delta === 0) return 'delta--neutral'
  return delta > 0 ? 'delta--up' : 'delta--down'
}

function getDeltaIcon(eventPublicId: string): string {
  const delta = getValueDelta(eventPublicId)
  if (delta === null || delta === 0) return 'pi pi-minus'
  return delta > 0 ? 'pi pi-arrow-up' : 'pi pi-arrow-down'
}

// ─── Event name resolution ──────────────────────────────────────
const eventMap = computed(() => {
  const map = new Map<string, { name: string; type: string; unit: string }>()
  for (const ev of eventStore.events) {
    map.set(ev.public_id, { name: ev.name, type: ev.type, unit: ev.unit })
  }
  return map
})

function getEventName(eventPublicId: string): string {
  return eventMap.value.get(eventPublicId)?.name ?? eventPublicId.slice(0, 8) + '…'
}

function getEventType(eventPublicId: string): string {
  return eventMap.value.get(eventPublicId)?.type ?? ''
}

function getEventUnit(eventPublicId: string): string {
  return eventMap.value.get(eventPublicId)?.unit ?? ''
}

// ─── Filtering ──────────────────────────────────────────────────
const filteredLiveDatapoints = computed(() => {
  let dps = latestDatapoints.value
  if (filterEventId.value) {
    dps = dps.filter(dp => dp.event_public_id === filterEventId.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    dps = dps.filter(dp => {
      const name = getEventName(dp.event_public_id).toLowerCase()
      const id = dp.event_public_id.toLowerCase()
      const val = String(dp.value)
      return name.includes(q) || id.includes(q) || val.includes(q)
    })
  }
  return dps
})

const filteredTableDatapoints = computed(() => {
  let dps = datapointStore.datapoints
  if (filterEventId.value) {
    dps = dps.filter(dp => dp.event_public_id === filterEventId.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    dps = dps.filter(dp => {
      const name = getEventName(dp.event_public_id).toLowerCase()
      const id = dp.event_public_id.toLowerCase()
      const val = String(dp.value)
      return name.includes(q) || id.includes(q) || val.includes(q)
    })
  }
  return dps
})

const totalPages = computed(() => Math.max(1, Math.ceil((datapointStore.total || 0) / pageSize.value)))

// ─── Plugin state banners ───────────────────────────────────────
const showNoPlugin = computed(() => pluginStore.instances.length === 0 && !pluginStore.loading)
const showDisabledBanner = computed(
  () => pluginStore.instances.length > 0 && pluginStore.instances.every((p) => !p.enabled),
)
const disabledPluginName = computed(
  () => pluginStore.instances.find((p) => !p.enabled)?.instance_name ?? 'Plugin',
)
const showDemoBanner = computed(
  () =>
    pluginStore.instances.some((p) => p.enabled && p.demo_mode) && !showDisabledBanner.value,
)
const demoPluginName = computed(
  () => pluginStore.instances.find((p) => p.enabled && p.demo_mode)?.instance_name ?? 'Plugin',
)

// ─── Actions ────────────────────────────────────────────────────
function changePage(delta: number) {
  page.value = Math.max(1, Math.min(totalPages.value, page.value + delta))
  datapointStore.fetchDatapoints(page.value, pageSize.value)
}

function onPageSizeChange() {
  page.value = 1
  datapointStore.fetchDatapoints(page.value, pageSize.value)
}

function onThrottleChange(ev: globalThis.Event) {
  const target = ev.target as HTMLSelectElement
  setThrottleMs(parseInt(target.value, 10))
}

function exportCsv() {
  const source: Datapoint[] = viewMode.value === 'live' ? filteredLiveDatapoints.value : filteredTableDatapoints.value
  if (source.length === 0) return

  const headers = ['Public ID', 'Event', 'Event ID', 'Value', 'Unit', 'Timestamp']
  const rows = source.map(dp => [
    dp.public_id ?? 'N/A',
    getEventName(dp.event_public_id),
    dp.event_public_id,    
    String(dp.value),
    getEventUnit(dp.event_public_id),
    dp.timestamp ?? '',
  ])

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')),
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `datapoints_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await Promise.all([
    datapointStore.fetchDatapoints(page.value, pageSize.value),
    pluginStore.fetchInstances(),
    eventStore.fetchEvents(),
  ])
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.view-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.total-badge {
  font-size: 0.8rem;
  background: var(--wm-border-light);
  color: var(--wm-text-secondary);
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-weight: 600;
}

/* View mode toggle */
.view-mode-toggle {
  display: flex;
  margin-left: auto;
  border: 1.5px solid var(--wm-border);
  border-radius: var(--wm-radius, 8px);
  overflow: hidden;
}

.btn-mode {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  border: none;
  background: var(--wm-surface);
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--wm-text-muted);
  cursor: pointer;
  transition: all 0.15s ease;

  &:not(:last-child) {
    border-right: 1.5px solid var(--wm-border);
  }

  &--active {
    background: var(--wm-primary);
    color: #fff;
  }

  &:hover:not(.btn-mode--active) {
    background: var(--wm-border-light);
  }
}

/* Stream Controls */
.stream-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.btn-pause {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 1rem;
  border: 1.5px solid var(--wm-border);
  border-radius: var(--wm-radius, 8px);
  background: var(--wm-surface);
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
  color: var(--wm-text);
  transition: all 0.2s ease;

  &:hover {
    background: var(--wm-border-light);
  }

  &--active {
    background: #fef3c7;
    border-color: #fbbf24;
    color: #92400e;

    &:hover {
      background: #fde68a;
    }
  }
}

.throttle-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.throttle-label {
  font-size: 0.8rem;
  color: var(--wm-text-muted);
  white-space: nowrap;
}

.throttle-select {
  padding: 0.35rem 0.6rem;
  border: 1.5px solid var(--wm-border);
  border-radius: var(--wm-radius, 8px);
  background: var(--wm-surface);
  font-size: 0.8rem;
  color: var(--wm-text);
  cursor: pointer;
}

.connection-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--wm-text-muted);
  font-weight: 500;
}

.connection-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wm-text-muted);
}

.connection-badge--live .connection-dot {
  background: var(--wm-success, #10b981);
  animation: dot-pulse 1.5s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
  50% { box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }
}

.pause-indicator {
  font-size: 0.8rem;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

/* Filter Bar */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.filter-group {
  position: relative;
  flex: 1;
  min-width: 200px;
}

.filter-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--wm-text-muted);
  font-size: 0.85rem;
}

.filter-input {
  width: 100%;
  padding: 0.5rem 0.75rem 0.5rem 2.25rem;
  border: 1.5px solid var(--wm-border);
  border-radius: var(--wm-radius, 8px);
  background: var(--wm-surface);
  font-size: 0.85rem;
  color: var(--wm-text);
  outline: none;
  transition: border-color 0.15s;

  &:focus {
    border-color: var(--wm-primary);
  }

  &::placeholder {
    color: var(--wm-text-muted);
  }
}

.filter-select {
  padding: 0.5rem 0.75rem;
  border: 1.5px solid var(--wm-border);
  border-radius: var(--wm-radius, 8px);
  background: var(--wm-surface);
  font-size: 0.85rem;
  color: var(--wm-text);
  cursor: pointer;
  min-width: 140px;

  &--sm {
    min-width: 100px;
  }
}

.btn-export {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.85rem;
  border: 1.5px solid var(--wm-border);
  border-radius: var(--wm-radius, 8px);
  background: var(--wm-surface);
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--wm-text);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;

  &:hover {
    background: var(--wm-border-light);
  }
}

/* Live table */
.data-table--live {
  .live-row {
    transition: background-color 0.6s ease;
  }
}

.row-flash--up {
  background-color: rgba(16, 185, 129, 0.12) !important;
  animation: flash-up 1.5s ease-out;
}

.row-flash--down {
  background-color: rgba(239, 68, 68, 0.12) !important;
  animation: flash-down 1.5s ease-out;
}

@keyframes flash-up {
  0% { background-color: rgba(16, 185, 129, 0.25); }
  100% { background-color: transparent; }
}

@keyframes flash-down {
  0% { background-color: rgba(239, 68, 68, 0.25); }
  100% { background-color: transparent; }
}

/* Event name & badges */
.event-name {
  font-weight: 600;
  color: var(--wm-text);
}

.event-type-badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  margin-left: 0.5rem;
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-radius: 4px;
  background: var(--wm-border-light);
  color: var(--wm-text-muted);
}

.value-cell {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
}

.value-unit {
  font-size: 0.75rem;
  color: var(--wm-text-muted);
}

/* Change delta */
.change-cell {
  white-space: nowrap;
}

.delta--up {
  color: #10b981;
  font-weight: 600;
  font-size: 0.85rem;
}

.delta--down {
  color: #ef4444;
  font-weight: 600;
  font-size: 0.85rem;
}

.delta--neutral {
  color: var(--wm-text-muted);
  font-size: 0.85rem;
}

.text-muted {
  color: var(--wm-text-muted);
}

/* Plugin hint banner */
.plugin-hint {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: var(--wm-radius-lg, 12px);
  color: #92400e;
}

.plugin-hint__icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.plugin-hint__content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;

  span {
    font-size: 0.85rem;
  }
}

.plugin-hint__action {
  white-space: nowrap;
  font-weight: 600;
  color: #92400e;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 0.35rem;

  &:hover {
    text-decoration: underline;
  }

  &--outline {
    color: #9a3412;
    border: 1.5px solid #fb923c;
    padding: 0.35rem 0.75rem;
    border-radius: var(--wm-radius, 8px);
    background: transparent;

    &:hover {
      background: #fff7ed;
      text-decoration: none;
    }
  }

  &--blue {
    color: #1e40af;

    &:hover {
      color: #1d4ed8;
    }
  }
}

.plugin-hint--orange {
  background: #fff7ed;
  border-color: #fb923c;
  color: #9a3412;
}

.plugin-hint--blue {
  background: #eff6ff;
  border-color: #60a5fa;
  color: #1e40af;
}
</style>
