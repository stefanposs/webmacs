<template>
  <div class="custom-dashboard">
    <div class="view-header">
      <div class="header-left">
        <button class="btn-back" @click="$router.push({ name: 'dashboards' })" aria-label="Back to dashboards">
          <i class="pi pi-arrow-left" />
        </button>
        <h1 v-if="store.currentDashboard">{{ store.currentDashboard.name }}</h1>
        <h1 v-else>Loading...</h1>
      </div>
      <div class="header-right">
        <button class="btn-secondary" @click="editing = !editing">
          <i :class="editing ? 'pi pi-lock' : 'pi pi-pencil'" />
          {{ editing ? 'Lock' : 'Edit' }}
        </button>
        <button v-if="editing" class="btn-primary" @click="openAddDialog">
          <i class="pi pi-plus" /> Add Widget
        </button>
      </div>
    </div>

    <!-- Time Range Bar -->
    <div class="time-range-bar">
      <button
        v-for="tr in timeRanges"
        :key="tr.minutes"
        class="time-pill"
        :class="{ 'time-pill--active': timeRangeMinutes === tr.minutes }"
        @click="setTimeRange(tr.minutes)"
        :title="tr.tooltip"
      >
        {{ tr.label }}
      </button>
      <span v-if="secondsAgo >= 0" class="time-updated">
        <i class="pi pi-refresh" /> {{ lastUpdatedLabel }}
      </span>
    </div>

    <div v-if="store.loading" class="loading-state"><i class="pi pi-spin pi-spinner" /> Loading...</div>

    <div
      v-else-if="!store.currentDashboard || store.currentDashboard.widgets.length === 0"
      class="empty-state"
    >
      <i class="pi pi-th-large" />
      <p>No widgets yet. Click "Edit" then "Add Widget" to get started.</p>
    </div>

    <!-- Widget grid -->
    <div v-else class="widget-grid" :class="{ 'widget-grid--editing': editing }">
      <div
        v-for="widget in store.currentDashboard.widgets"
        :key="widget.public_id"
        class="widget-cell"
        :style="gridStyle(widget)"
      >
        <component
          :is="widgetComponent(widget.widget_type)"
          :widget="widget"
          :editable="editing"
          :time-range-minutes="timeRangeMinutes"
          :unit="eventForWidget(widget)?.unit"
          :min="eventForWidget(widget)?.min_value"
          :max="eventForWidget(widget)?.max_value"
          @edit="openEditDialog(widget)"
          @delete="handleDeleteWidget(widget.public_id)"
        />
      </div>
    </div>

    <!-- ─── Add Widget Dialog ────────────────────────────────────── -->
    <Transition name="modal">
      <div v-if="showAddWidget" class="modal-overlay" @click.self="showAddWidget = false">
        <div class="modal modal--wide">
          <h2><i class="pi pi-plus-circle" /> Add Widget</h2>
          <p v-if="editError" class="error-msg">{{ editError }}</p>

          <form @submit.prevent="handleAddWidget">
            <!-- Widget Type Cards -->
            <div class="form-section">
              <label class="section-label">Widget Type</label>
              <div class="type-cards">
                <button
                  v-for="wt in widgetTypes"
                  :key="wt.value"
                  type="button"
                  class="type-card"
                  :class="{ 'type-card--selected': wType === wt.value }"
                  @click="wType = wt.value"
                >
                  <i :class="wt.icon" class="type-card__icon" />
                  <span class="type-card__label">{{ wt.label }}</span>
                  <span class="type-card__desc">{{ wt.description }}</span>
                </button>
              </div>
            </div>

            <!-- Config -->
            <div class="form-section">
              <label class="section-label">Configuration</label>
              <label>Title</label>
              <input v-model="wTitle" type="text" placeholder="e.g. Temperature over Time" required maxlength="255" />

              <label>Data Source (Event)</label>
              <select v-model="wEvent">
                <option value="">-- no event linked --</option>
                <option v-for="ev in eventStore.events" :key="ev.public_id" :value="ev.public_id">
                  {{ ev.name }} ({{ ev.type }})
                </option>
              </select>
            </div>

            <!-- Size Presets -->
            <div class="form-section">
              <label class="section-label">Size</label>
              <div class="size-presets">
                <button
                  v-for="sp in sizePresets"
                  :key="sp.label"
                  type="button"
                  class="size-preset"
                  :class="{ 'size-preset--selected': wW === sp.w && wH === sp.h }"
                  @click="wW = sp.w; wH = sp.h"
                >
                  <div class="size-preset__preview">
                    <div class="size-preset__block" :style="previewBlockStyle(sp.w, sp.h)" />
                  </div>
                  <span class="size-preset__label">{{ sp.label }}</span>
                  <span class="size-preset__dims">{{ sp.w }} &times; {{ sp.h }}</span>
                </button>
              </div>

              <!-- Live Preview -->
              <div class="grid-preview">
                <div class="grid-preview__label">Preview (12-column grid)</div>
                <div class="grid-preview__grid">
                  <div v-for="r in 4" :key="r" class="grid-preview__row">
                    <div
                      v-for="c in 12"
                      :key="c"
                      class="grid-preview__cell"
                      :class="{ 'grid-preview__cell--active': c <= wW && r <= wH }"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="showAddWidget = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="!wTitle.trim()">
                <i class="pi pi-plus" /> Add Widget
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>

    <!-- ─── Edit Widget Dialog ───────────────────────────────────── -->
    <Transition name="modal">
      <div v-if="editingWidget" class="modal-overlay" @click.self="editingWidget = null">
        <div class="modal modal--wide">
          <h2>
            <i :class="widgetTypeIcon(editingWidget.widget_type)" />
            Edit Widget
            <span class="widget-type-badge">{{ editingWidget.widget_type.replace(/_/g, ' ') }}</span>
          </h2>
          <p v-if="editError" class="error-msg">{{ editError }}</p>

          <form @submit.prevent="handleEditWidget">
            <div class="form-section">
              <label class="section-label">Configuration</label>
              <label>Title</label>
              <input v-model="editTitle" type="text" placeholder="Widget title" required maxlength="255" />

              <label>Data Source (Event)</label>
              <select v-model="editEvent">
                <option value="">-- no event linked --</option>
                <option v-for="ev in eventStore.events" :key="ev.public_id" :value="ev.public_id">
                  {{ ev.name }} ({{ ev.type }})
                </option>
              </select>
            </div>

            <!-- Size Presets -->
            <div class="form-section">
              <label class="section-label">Size</label>
              <div class="size-presets">
                <button
                  v-for="sp in sizePresets"
                  :key="sp.label"
                  type="button"
                  class="size-preset"
                  :class="{ 'size-preset--selected': editW === sp.w && editH === sp.h }"
                  @click="editW = sp.w; editH = sp.h"
                >
                  <div class="size-preset__preview">
                    <div class="size-preset__block" :style="previewBlockStyle(sp.w, sp.h)" />
                  </div>
                  <span class="size-preset__label">{{ sp.label }}</span>
                  <span class="size-preset__dims">{{ sp.w }} &times; {{ sp.h }}</span>
                </button>
              </div>

              <div class="grid-preview">
                <div class="grid-preview__label">Preview (12-column grid)</div>
                <div class="grid-preview__grid">
                  <div v-for="r in 4" :key="r" class="grid-preview__row">
                    <div
                      v-for="c in 12"
                      :key="c"
                      class="grid-preview__cell"
                      :class="{ 'grid-preview__cell--active': c <= editW && r <= editH }"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="editingWidget = null">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="!editTitle.trim()">
                <i class="pi pi-check" /> Save Changes
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboards'
import { useEventStore } from '@/stores/events'
import { useNotification } from '@/composables/useNotification'
import LineChartWidget from '@/components/widgets/LineChartWidget.vue'
import GaugeWidget from '@/components/widgets/GaugeWidget.vue'
import StatCardWidget from '@/components/widgets/StatCardWidget.vue'
import ActuatorToggleWidget from '@/components/widgets/ActuatorToggleWidget.vue'
import type { DashboardWidget, Event, WidgetType } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useDashboardStore()
const eventStore = useEventStore()
const notify = useNotification()

const editing = ref(false)
const showAddWidget = ref(false)
const editError = ref<string | null>(null)

// ─── Time Range ───────────────────────────────────────────────────
const timeRanges = [
  { label: '20m', minutes: 20, tooltip: 'Last 20 minutes' },
  { label: '1h', minutes: 60, tooltip: 'Last hour' },
  { label: '6h', minutes: 360, tooltip: 'Last 6 hours' },
  { label: '24h', minutes: 1440, tooltip: 'Last 24 hours' },
  { label: '7d', minutes: 10080, tooltip: 'Last 7 days' },
  { label: '10d', minutes: 14400, tooltip: 'Last 10 days' },
]

function getStoredRange(dashId: string): number {
  try {
    const v = localStorage.getItem(`dashboard:${dashId}:timeRange`)
    return v ? Number(v) : 60
  } catch { return 60 }
}

const timeRangeMinutes = ref(60)
const secondsAgo = ref(0)

const lastUpdatedLabel = computed(() => {
  if (secondsAgo.value < 5) return 'just now'
  if (secondsAgo.value < 60) return `${secondsAgo.value}s ago`
  return `${Math.round(secondsAgo.value / 60)}m ago`
})

// Update the "ago" label every second
let agoInterval: ReturnType<typeof setInterval> | null = null

function setTimeRange(minutes: number) {
  timeRangeMinutes.value = minutes
  const dashId = route.params.id as string
  try { localStorage.setItem(`dashboard:${dashId}:timeRange`, String(minutes)) } catch {}
  router.replace({ query: { ...route.query, range: String(minutes) } })
  secondsAgo.value = 0
}

// ─── Add Widget State ───────────────────────────────────────────────────
const wType = ref<WidgetType>('line_chart')
const wTitle = ref('')
const wEvent = ref('')
const wW = ref(4)
const wH = ref(3)

// ─── Edit Widget State ──────────────────────────────────────────────────
const editingWidget = ref<DashboardWidget | null>(null)
const editTitle = ref('')
const editEvent = ref('')
const editW = ref(4)
const editH = ref(3)

// ─── Widget Type Definitions ────────────────────────────────────────────
const widgetTypes: { value: WidgetType; label: string; icon: string; description: string }[] = [
  { value: 'line_chart', label: 'Line Chart', icon: 'pi pi-chart-line', description: 'Time-series data trend' },
  { value: 'gauge', label: 'Gauge', icon: 'pi pi-gauge', description: 'Live value with arc meter' },
  { value: 'stat_card', label: 'Stat Card', icon: 'pi pi-hashtag', description: 'Large single number' },
  { value: 'actuator_toggle', label: 'Toggle', icon: 'pi pi-power-off', description: 'ON/OFF switch control' },
]

function widgetTypeIcon(type: WidgetType): string {
  return widgetTypes.find((wt) => wt.value === type)?.icon ?? 'pi pi-box'
}

// ─── Size Presets ───────────────────────────────────────────────────────
const sizePresets = [
  { label: 'Small', w: 3, h: 2 },
  { label: 'Medium', w: 4, h: 3 },
  { label: 'Wide', w: 6, h: 3 },
  { label: 'Large', w: 6, h: 4 },
  { label: 'Full Width', w: 12, h: 4 },
]

function previewBlockStyle(w: number, h: number) {
  return {
    width: `${(w / 12) * 100}%`,
    height: `${(h / 4) * 100}%`,
  }
}

// ─── Widget Component Map ───────────────────────────────────────────────
const widgetMap: Record<WidgetType, Component> = {
  line_chart: LineChartWidget,
  gauge: GaugeWidget,
  stat_card: StatCardWidget,
  actuator_toggle: ActuatorToggleWidget,
}

function widgetComponent(type: WidgetType): Component {
  return widgetMap[type] ?? StatCardWidget
}

function eventForWidget(widget: DashboardWidget): Event | undefined {
  if (!widget.event_public_id) return undefined
  return eventStore.events.find((e) => e.public_id === widget.event_public_id)
}

function gridStyle(widget: DashboardWidget) {
  return {
    gridColumn: `span ${widget.w}`,
    gridRow: `span ${widget.h}`,
  }
}

// ─── Handlers ───────────────────────────────────────────────────────────
function openAddDialog() {
  editError.value = null
  wType.value = 'line_chart'
  wTitle.value = ''
  wEvent.value = ''
  wW.value = 4
  wH.value = 3
  showAddWidget.value = true
}

async function handleAddWidget() {
  const dashId = store.currentDashboard?.public_id
  if (!dashId) return
  editError.value = null
  try {
    await store.addWidget(dashId, {
      widget_type: wType.value,
      title: wTitle.value,
      event_public_id: wEvent.value || null,
      w: wW.value,
      h: wH.value,
    })
    showAddWidget.value = false
    notify.success('Widget added', `"${wTitle.value}" has been added to the dashboard.`)
    wTitle.value = ''
    wEvent.value = ''
  } catch {
    editError.value = 'Failed to add widget. Please try again.'
  }
}

async function handleDeleteWidget(widgetId: string) {
  const dashId = store.currentDashboard?.public_id
  if (!dashId) return
  const widget = store.currentDashboard?.widgets.find((w) => w.public_id === widgetId)
  try {
    await store.deleteWidget(dashId, widgetId)
    notify.success('Widget removed', widget ? `"${widget.title}" has been deleted.` : undefined)
  } catch {
    notify.error('Delete failed', 'Could not remove widget. Please try again.')
  }
}

function openEditDialog(widget: DashboardWidget) {
  editError.value = null
  editingWidget.value = widget
  editTitle.value = widget.title
  editEvent.value = widget.event_public_id ?? ''
  editW.value = widget.w
  editH.value = widget.h
}

async function handleEditWidget() {
  const dashId = store.currentDashboard?.public_id
  const widget = editingWidget.value
  if (!dashId || !widget) return
  editError.value = null
  try {
    await store.updateWidget(dashId, widget.public_id, {
      title: editTitle.value,
      event_public_id: editEvent.value || null,
      w: editW.value,
      h: editH.value,
    })
    editingWidget.value = null
    notify.success('Widget updated', `"${editTitle.value}" has been saved.`)
  } catch {
    editError.value = 'Failed to update widget. Please try again.'
  }
}

onMounted(() => {
  const id = route.params.id as string
  // Restore time range: URL query > localStorage > default (60)
  const queryRange = route.query.range ? Number(route.query.range) : null
  const storedRange = getStoredRange(id)
  timeRangeMinutes.value = queryRange || storedRange
  store.fetchDashboard(id)
  eventStore.fetchEvents()
  agoInterval = setInterval(() => { secondsAgo.value++ }, 1000)
})

onUnmounted(() => {
  if (agoInterval) clearInterval(agoInterval)
})
</script>

<style scoped>
.custom-dashboard { padding: 1.5rem; }
.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.header-left h1 {
  font-size: 1.3rem;
  color: var(--wm-text, #e2e8f0);
}
.header-right {
  display: flex;
  gap: 0.5rem;
}
.btn-back {
  background: none;
  border: 1px solid var(--wm-border, #334155);
  color: var(--wm-text-muted, #94a3b8);
  border-radius: 8px;
  padding: 0.4rem 0.6rem;
  cursor: pointer;
}
.btn-back:hover { border-color: #3b82f6; color: #3b82f6; }

/* ─── Widget Grid ──────────────────────────────────────────────────── */
.widget-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 0.75rem;
  grid-auto-rows: 80px;
}
.widget-grid--editing .widget-cell {
  transition: all 0.3s ease;
}
.widget-cell {
  min-height: 0;
}

/* ─── Time Range Bar ────────────────────────────────────────────── */
.time-range-bar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 1rem;
  padding: 0.25rem;
  background: var(--wm-surface, #1e293b);
  border: 1px solid var(--wm-border, #334155);
  border-radius: 10px;
  width: fit-content;
}
.time-pill {
  padding: 0.35rem 0.75rem;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--wm-text-muted, #94a3b8);
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.time-pill:hover {
  color: var(--wm-text, #e2e8f0);
  background: rgba(255,255,255,0.05);
}
.time-pill--active {
  background: #3b82f6;
  color: #fff;
  box-shadow: 0 1px 4px rgba(59,130,246,0.3);
}
.time-updated {
  font-size: 0.65rem;
  color: var(--wm-text-muted, #94a3b8);
  margin-left: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  white-space: nowrap;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem;
  color: var(--wm-text-muted, #94a3b8);
}
.empty-state i { font-size: 2rem; }

/* ─── Buttons ──────────────────────────────────────────────────────── */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-primary:hover { background: #2563eb; }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: transparent;
  color: var(--wm-text-muted, #94a3b8);
  border: 1px solid var(--wm-border, #334155);
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
.btn-secondary:hover { border-color: #3b82f6; color: #3b82f6; }

/* ─── Modal ────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal {
  background: var(--wm-surface, #1e293b);
  border: 1px solid var(--wm-border, #334155);
  border-radius: 12px;
  padding: 1.5rem;
  min-width: 380px;
  max-height: 90vh;
  overflow-y: auto;
}
.modal--wide { min-width: 520px; max-width: 600px; }
.modal h2 {
  color: var(--wm-text, #e2e8f0);
  margin-bottom: 1.25rem;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* ─── Modal Transitions ────────────────────────────────────────────── */
.modal-enter-active { transition: opacity 0.2s ease; }
.modal-enter-active .modal { transition: transform 0.2s ease, opacity 0.2s ease; }
.modal-leave-active { transition: opacity 0.15s ease; }
.modal-leave-active .modal { transition: transform 0.15s ease, opacity 0.15s ease; }
.modal-enter-from { opacity: 0; }
.modal-enter-from .modal { transform: scale(0.95); opacity: 0; }
.modal-leave-to { opacity: 0; }
.modal-leave-to .modal { transform: scale(0.95); opacity: 0; }

/* ─── Form Sections ────────────────────────────────────────────────── */
.form-section {
  margin-bottom: 1.25rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--wm-border, #334155);
}
.form-section:last-of-type { border-bottom: none; }
.section-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--wm-text-muted, #94a3b8);
  margin-bottom: 0.75rem;
}
.modal label {
  display: block;
  font-size: 0.85rem;
  color: var(--wm-text-muted, #94a3b8);
  margin-bottom: 0.3rem;
}
.modal input[type="text"],
.modal input[type="number"],
.modal select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--wm-border, #334155);
  border-radius: 8px;
  background: var(--wm-bg, #0f172a);
  color: var(--wm-text, #e2e8f0);
  margin-bottom: 0.75rem;
  transition: border-color 0.2s;
}
.modal input:focus, .modal select:focus {
  outline: none;
  border-color: #3b82f6;
}

/* ─── Widget Type Cards ────────────────────────────────────────────── */
.type-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.75rem 0.5rem;
  background: var(--wm-bg, #0f172a);
  border: 2px solid var(--wm-border, #334155);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
  text-align: center;
}
.type-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
}
.type-card--selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.08);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.3);
}
.type-card__icon {
  font-size: 1.25rem;
  color: #60a5fa;
  margin-bottom: 0.15rem;
}
.type-card--selected .type-card__icon { color: #3b82f6; }
.type-card__label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--wm-text, #e2e8f0);
}
.type-card__desc {
  font-size: 0.65rem;
  color: var(--wm-text-muted, #94a3b8);
  line-height: 1.3;
}

/* ─── Size Presets ─────────────────────────────────────────────────── */
.size-presets {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}
.size-preset {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.5rem;
  min-width: 72px;
  background: var(--wm-bg, #0f172a);
  border: 2px solid var(--wm-border, #334155);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.size-preset:hover { border-color: rgba(59, 130, 246, 0.4); }
.size-preset--selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.08);
}
.size-preset__preview {
  width: 48px;
  height: 24px;
  background: rgba(255,255,255,0.03);
  border-radius: 3px;
  position: relative;
  overflow: hidden;
}
.size-preset__block {
  position: absolute;
  top: 0;
  left: 0;
  background: rgba(59, 130, 246, 0.25);
  border: 1px solid rgba(59, 130, 246, 0.5);
  border-radius: 2px;
  transition: all 0.2s;
}
.size-preset--selected .size-preset__block {
  background: rgba(59, 130, 246, 0.4);
  border-color: #3b82f6;
}
.size-preset__label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--wm-text, #e2e8f0);
}
.size-preset__dims {
  font-size: 0.6rem;
  color: var(--wm-text-muted, #94a3b8);
}

/* ─── Grid Preview ─────────────────────────────────────────────────── */
.grid-preview {
  margin-top: 0.5rem;
}
.grid-preview__label {
  font-size: 0.7rem;
  color: var(--wm-text-muted, #94a3b8);
  margin-bottom: 0.35rem;
}
.grid-preview__grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0.35rem;
  background: var(--wm-bg, #0f172a);
  border-radius: 6px;
  border: 1px solid var(--wm-border, #334155);
}
.grid-preview__row {
  display: flex;
  gap: 2px;
}
.grid-preview__cell {
  flex: 1;
  height: 12px;
  background: rgba(255,255,255,0.03);
  border-radius: 2px;
  transition: background 0.2s, border-color 0.2s;
  border: 1px solid transparent;
}
.grid-preview__cell--active {
  background: rgba(59, 130, 246, 0.3);
  border-color: rgba(59, 130, 246, 0.5);
}

/* ─── Status ───────────────────────────────────────────────────────── */
.modal-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem; }
.error-msg {
  color: #ef4444;
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
  padding: 0.5rem;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.1);
}
.widget-type-badge {
  font-size: 0.7rem;
  font-weight: 400;
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  text-transform: capitalize;
  margin-left: auto;
}
</style>
