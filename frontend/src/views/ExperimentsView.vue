<template>
  <div class="view-experiments">
    <div class="view-header">
      <h2>Experiments</h2>
      <button class="btn-primary" @click="showCreateDialog = true">
        <i class="pi pi-plus" /> New Experiment
      </button>
    </div>

    <div v-if="experimentStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading experiments...</div>

    <table v-else-if="experimentStore.experiments.length" class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Started</th>
          <th>Stopped</th>
          <th style="width: 120px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="exp in experimentStore.experiments" :key="exp.public_id">
          <td><strong>{{ exp.name }}</strong></td>
          <td>
            <span class="badge" :class="!exp.stopped_on ? 'badge--running' : 'badge--stopped'">
              {{ !exp.stopped_on ? 'Running' : 'Stopped' }}
            </span>
          </td>
          <td>{{ formatDate(exp.started_on) }}</td>
          <td>{{ formatDate(exp.stopped_on) }}</td>
          <td class="action-cell">
            <button class="btn-icon btn-csv" @click="handleExport(exp)" title="Download CSV">
              <i class="pi pi-download" />
            </button>
            <button v-if="!exp.stopped_on" class="btn-icon btn-stop" @click="handleStop(exp)" title="Stop">
              <i class="pi pi-stop-circle" />
            </button>
            <button class="btn-icon" @click="handleDelete(exp)" title="Delete">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-play-circle" />
      No experiments yet. Start your first experiment.
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog">
        <h3>Start Experiment</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" required placeholder="e.g. Pressure test #12" />
          </div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="showCreateDialog = false">Cancel</button>
            <button type="submit" class="btn-primary"><i class="pi pi-play" /> Start</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { useExperimentStore } from '@/stores/experiments'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import type { Experiment } from '@/types'

const experimentStore = useExperimentStore()
const { success, error } = useNotification()
const { formatDate } = useFormatters()
const showCreateDialog = ref(false)
const form = reactive({ name: '' })

async function handleCreate() {
  try {
    await experimentStore.createExperiment({ ...form })
    success('Experiment started', `"${form.name}" is now running.`)
    showCreateDialog.value = false
    form.name = ''
  } catch (err: unknown) {
    error('Failed to start experiment', (err as Error).message)
  }
}

async function handleExport(exp: Experiment) {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`/api/v1/experiments/${exp.public_id}/export/csv`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) throw new Error('Export failed')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `experiment_${exp.name.replace(/\s+/g, '_')}.csv`
    a.click()
    URL.revokeObjectURL(url)
    success('CSV exported', `"${exp.name}" data downloaded.`)
  } catch (err: unknown) {
    error('Export failed', (err as Error).message)
  }
}

async function handleStop(exp: Experiment) {
  try {
    await experimentStore.stopExperiment(exp.public_id)
    success('Experiment stopped', `"${exp.name}" was stopped.`)
  } catch (err: unknown) {
    error('Failed to stop experiment', (err as Error).message)
  }
}

async function handleDelete(exp: Experiment) {
  if (confirm(`Delete experiment "${exp.name}"?`)) {
    try {
      await experimentStore.deleteExperiment(exp.public_id)
      success('Experiment deleted', `"${exp.name}" was removed.`)
    } catch (err: unknown) {
      error('Failed to delete experiment', (err as Error).message)
    }
  }
}

onMounted(() => experimentStore.fetchExperiments())
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.btn-stop { color: var(--wm-warning); &:hover { color: var(--wm-danger); } }
.btn-csv { color: var(--wm-info, #3b82f6); &:hover { color: var(--wm-primary); } }
.action-cell { display: flex; gap: 0.25rem; }
</style>
