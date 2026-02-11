<template>
  <div class="custom-dashboard">
    <div class="view-header">
      <div class="header-left">
        <button class="btn-back" @click="$router.push({ name: 'dashboards' })">
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
        <button v-if="editing" class="btn-primary" @click="showAddWidget = true">
          <i class="pi pi-plus" /> Add Widget
        </button>
      </div>
    </div>

    <div v-if="store.loading" class="loading-state"><i class="pi pi-spin pi-spinner" /> Loading...</div>

    <div
      v-else-if="!store.currentDashboard || store.currentDashboard.widgets.length === 0"
      class="empty-state"
    >
      <i class="pi pi-th-large" />
      <p>No widgets yet. Click "Edit" then "Add Widget" to get started.</p>
    </div>

    <!-- Widget grid (CSS Grid fallback — no dependency needed) -->
    <div v-else class="widget-grid">
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
          @edit="openEditDialog(widget)"
          @delete="handleDeleteWidget(widget.public_id)"
        />
      </div>
    </div>

    <!-- Add widget dialog -->
    <div v-if="showAddWidget" class="modal-overlay" @click.self="showAddWidget = false">
      <div class="modal">
        <h2>Add Widget</h2>
        <p v-if="editError" class="error-msg">{{ editError }}</p>
        <form @submit.prevent="handleAddWidget">
          <label>Type</label>
          <select v-model="wType" required>
            <option value="line_chart">Line Chart</option>
            <option value="gauge">Gauge</option>
            <option value="stat_card">Stat Card</option>
            <option value="actuator_toggle">Actuator Toggle</option>
          </select>

          <label>Title</label>
          <input v-model="wTitle" type="text" placeholder="Widget title" required maxlength="255" />

          <label>Event</label>
          <select v-model="wEvent">
            <option value="">-- none --</option>
            <option v-for="ev in eventStore.events" :key="ev.public_id" :value="ev.public_id">
              {{ ev.name }} ({{ ev.type }})
            </option>
          </select>

          <div class="grid-fields">
            <div><label>W</label><input v-model.number="wW" type="number" min="1" max="12" /></div>
            <div><label>H</label><input v-model.number="wH" type="number" min="1" max="12" /></div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showAddWidget = false">Cancel</button>
            <button type="submit" class="btn-primary">Add</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit widget dialog -->
    <div v-if="editingWidget" class="modal-overlay" @click.self="editingWidget = null">
      <div class="modal">
        <h2>Edit Widget <span class="widget-type-badge">{{ editingWidget.widget_type.replace('_', ' ') }}</span></h2>
        <p v-if="editError" class="error-msg">{{ editError }}</p>
        <form @submit.prevent="handleEditWidget">
          <label>Title</label>
          <input v-model="editTitle" type="text" placeholder="Widget title" required maxlength="255" />

          <label>Event</label>
          <select v-model="editEvent">
            <option value="">-- none --</option>
            <option v-for="ev in eventStore.events" :key="ev.public_id" :value="ev.public_id">
              {{ ev.name }} ({{ ev.type }})
            </option>
          </select>

          <div class="grid-fields">
            <div><label>W</label><input v-model.number="editW" type="number" min="1" max="12" /></div>
            <div><label>H</label><input v-model.number="editH" type="number" min="1" max="12" /></div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="editingWidget = null">Cancel</button>
            <button type="submit" class="btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, type Component } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboards'
import { useEventStore } from '@/stores/events'
import LineChartWidget from '@/components/widgets/LineChartWidget.vue'
import GaugeWidget from '@/components/widgets/GaugeWidget.vue'
import StatCardWidget from '@/components/widgets/StatCardWidget.vue'
import ActuatorToggleWidget from '@/components/widgets/ActuatorToggleWidget.vue'
import type { DashboardWidget, WidgetType } from '@/types'

const route = useRoute()
const store = useDashboardStore()
const eventStore = useEventStore()

const editing = ref(false)
const showAddWidget = ref(false)
const wType = ref<WidgetType>('line_chart')
const wTitle = ref('')
const wEvent = ref('')
const wW = ref(4)
const wH = ref(3)

// Edit-widget state
const editingWidget = ref<DashboardWidget | null>(null)
const editTitle = ref('')
const editEvent = ref('')
const editW = ref(4)
const editH = ref(3)

const widgetMap: Record<WidgetType, Component> = {
  line_chart: LineChartWidget,
  gauge: GaugeWidget,
  stat_card: StatCardWidget,
  actuator_toggle: ActuatorToggleWidget,
}

function widgetComponent(type: WidgetType): Component {
  return widgetMap[type] ?? StatCardWidget
}

function gridStyle(widget: DashboardWidget) {
  return {
    gridColumn: `span ${widget.w}`,
    gridRow: `span ${widget.h}`,
  }
}

const editError = ref<string | null>(null)

async function handleAddWidget() {
  const dashId = store.currentDashboard?.public_id
  if (!dashId) return
  editError.value = null
  try {
    await store.addWidget(dashId, {
      widget_type: wType.value,
      title: wTitle.value,
      event_public_id: wEvent.value || null,
      x: 0,
      y: 0,
      w: wW.value,
      h: wH.value,
    })
    showAddWidget.value = false
    wTitle.value = ''
    wEvent.value = ''
  } catch {
    editError.value = 'Failed to add widget. Please try again.'
  }
}

async function handleDeleteWidget(widgetId: string) {
  const dashId = store.currentDashboard?.public_id
  if (!dashId) return
  if (confirm('Delete this widget?')) {
    await store.deleteWidget(dashId, widgetId)
  }
}

function openEditDialog(widget: DashboardWidget) {
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
  } catch {
    editError.value = 'Failed to update widget. Please try again.'
  }
}

onMounted(() => {
  const id = route.params.id as string
  store.fetchDashboard(id)
  eventStore.fetchEvents()
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

.widget-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 0.75rem;
  grid-auto-rows: 80px;
}
.widget-cell {
  min-height: 0;
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
}
.btn-primary:hover { background: #2563eb; }
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
}
.btn-secondary:hover { border-color: #3b82f6; color: #3b82f6; }

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
}
.modal h2 { color: var(--wm-text, #e2e8f0); margin-bottom: 1rem; font-size: 1.1rem; }
.modal label { display: block; font-size: 0.85rem; color: var(--wm-text-muted, #94a3b8); margin-bottom: 0.3rem; }
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
}
.grid-fields {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.grid-fields > div { flex: 1; }
.grid-fields input { width: 100%; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.5rem; }
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
  margin-left: 0.5rem;
  vertical-align: middle;
}
</style>
