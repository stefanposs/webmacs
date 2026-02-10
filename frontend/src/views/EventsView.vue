<template>
  <div class="view-events">
    <div class="view-header">
      <h2>Events</h2>
      <button class="btn-primary" @click="showCreateDialog = true">
        <i class="pi pi-plus" /> New Event
      </button>
    </div>

    <div v-if="eventStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading events...</div>

    <table v-else-if="eventStore.events.length" class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Unit</th>
          <th>Range</th>
          <th>Public ID</th>
          <th style="width: 110px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="event in eventStore.events" :key="event.public_id">
          <td><strong>{{ event.name }}</strong></td>
          <td><span class="badge" :class="`badge--${event.type}`">{{ event.type }}</span></td>
          <td>{{ event.unit }}</td>
          <td>{{ event.min_value }} – {{ event.max_value }}</td>
          <td class="mono">{{ event.public_id.slice(0, 8) }}…</td>
          <td>
            <button class="btn-icon" @click="openEdit(event)" title="Edit">
              <i class="pi pi-pencil" />
            </button>
            <button class="btn-icon" @click="confirmDelete(event)" title="Delete">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-bolt" />
      No events yet. Create your first event to get started.
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog">
        <h3>Create Event</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" required placeholder="e.g. Temperature Sensor" />
          </div>
          <div class="form-group">
            <label>Type</label>
            <select v-model="form.type" required>
              <option v-for="t in eventTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Unit</label>
            <input v-model="form.unit" placeholder="e.g. °C, bar, %" />
          </div>
          <div style="display: flex; gap: 0.75rem">
            <div class="form-group" style="flex: 1">
              <label>Min Value</label>
              <input v-model.number="form.min_value" type="number" step="any" required />
            </div>
            <div class="form-group" style="flex: 1">
              <label>Max Value</label>
              <input v-model.number="form.max_value" type="number" step="any" required />
            </div>
          </div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="showCreateDialog = false">Cancel</button>
            <button type="submit" class="btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Dialog -->
    <div v-if="showEditDialog" class="dialog-overlay" @click.self="showEditDialog = false">
      <div class="dialog">
        <h3>Edit Event</h3>
        <form @submit.prevent="handleEdit">
          <div class="form-group">
            <label>Name</label>
            <input v-model="editForm.name" required />
          </div>
          <div class="form-group">
            <label>Type</label>
            <select v-model="editForm.type" required>
              <option v-for="t in eventTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Unit</label>
            <input v-model="editForm.unit" />
          </div>
          <div style="display: flex; gap: 0.75rem">
            <div class="form-group" style="flex: 1">
              <label>Min Value</label>
              <input v-model.number="editForm.min_value" type="number" step="any" required />
            </div>
            <div class="form-group" style="flex: 1">
              <label>Max Value</label>
              <input v-model.number="editForm.max_value" type="number" step="any" required />
            </div>
          </div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="showEditDialog = false">Cancel</button>
            <button type="submit" class="btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { useEventStore } from '@/stores/events'
import { useNotification } from '@/composables/useNotification'
import { EventType } from '@/types'
import type { Event } from '@/types'

const eventStore = useEventStore()
const { success, error } = useNotification()
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingEvent = ref<Event | null>(null)
const eventTypes = Object.values(EventType)

const form = reactive({
  name: '',
  type: EventType.sensor,
  unit: '',
  min_value: 0,
  max_value: 100,
})

const editForm = reactive({
  name: '',
  type: EventType.sensor as EventType,
  unit: '',
  min_value: 0,
  max_value: 100,
})

async function handleCreate() {
  try {
    await eventStore.createEvent({ ...form })
    success('Event created', `"${form.name}" was added successfully.`)
    showCreateDialog.value = false
    Object.assign(form, { name: '', type: EventType.sensor, unit: '', min_value: 0, max_value: 100 })
  } catch (err: unknown) {
    error('Failed to create event', (err as Error).message)
  }
}

function openEdit(event: Event) {
  editingEvent.value = event
  Object.assign(editForm, {
    name: event.name,
    type: event.type,
    unit: event.unit,
    min_value: event.min_value,
    max_value: event.max_value,
  })
  showEditDialog.value = true
}

async function handleEdit() {
  if (!editingEvent.value) return
  try {
    await eventStore.updateEvent(editingEvent.value.public_id, { ...editForm })
    success('Event updated', `"${editForm.name}" was saved.`)
    showEditDialog.value = false
    editingEvent.value = null
  } catch (err: unknown) {
    error('Failed to update event', (err as Error).message)
  }
}

async function confirmDelete(event: Event) {
  if (confirm(`Delete event "${event.name}"?`)) {
    try {
      await eventStore.deleteEvent(event.public_id)
      success('Event deleted', `"${event.name}" was removed.`)
    } catch (err: unknown) {
      error('Failed to delete event', (err as Error).message)
    }
  }
}

onMounted(() => eventStore.fetchEvents())
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';
</style>
