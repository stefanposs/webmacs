<template>
  <div class="view-logs">
    <div class="view-header">
      <h2>Logs</h2>
      <button class="btn-secondary" :disabled="logStore.exporting" @click="handleExport">
        <i class="pi pi-download" /> {{ logStore.exporting ? 'Exporting…' : 'Export CSV' }}
      </button>
    </div>

    <div class="filters-row">
      <select
        :value="logStore.filters.logging_type"
        @change="onTypeChange"
        class="filter-input"
      >
        <option value="">All types</option>
        <option value="info">info</option>
        <option value="warning">warning</option>
        <option value="error">error</option>
      </select>

      <input
        v-model="searchInput"
        class="filter-input filter-input--grow"
        type="text"
        placeholder="Search message…"
        @keyup.enter="applyFilters"
      />

      <input v-model="fromDateInput" class="filter-input" type="datetime-local" />
      <input v-model="toDateInput" class="filter-input" type="datetime-local" />

      <button class="btn-secondary" @click="applyFilters">
        <i class="pi pi-filter" /> Apply
      </button>
      <button class="btn-secondary" @click="resetFilters">
        <i class="pi pi-refresh" /> Reset
      </button>
    </div>

    <div v-if="logStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading logs...</div>

    <div v-else-if="logStore.error" class="empty-state">
      <i class="pi pi-exclamation-triangle" />
      {{ logStore.error }}
    </div>

    <table v-else-if="logStore.logs.length" class="data-table">
      <thead>
        <tr>
          <th style="width: 160px">Timestamp</th>
          <th style="width: 100px">Type</th>
          <th style="width: 100px">Status</th>
          <th style="width: 140px">User</th>
          <th>Message</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="log in logStore.logs" :key="log.public_id">
          <td class="mono">{{ formatRelativeTime(log.created_on) }}</td>
          <td><span class="badge" :class="`badge--${log.logging_type}`">{{ log.logging_type }}</span></td>
          <td>{{ log.status_type ?? '—' }}</td>
          <td class="mono">{{ displayUser(log.username, log.user_public_id) }}</td>
          <td>{{ log.content }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-file-edit" />
      No log entries yet.
    </div>

    <div class="pagination">
      <button class="btn-secondary" :disabled="logStore.page <= 1" @click="changePage(-1)">
        <i class="pi pi-chevron-left" /> Previous
      </button>
      <span>Page {{ logStore.page }} of {{ Math.max(1, Math.ceil(logStore.total / logStore.pageSize)) }}</span>
      <button class="btn-secondary" :disabled="logStore.page * logStore.pageSize >= logStore.total" @click="changePage(1)">
        Next <i class="pi pi-chevron-right" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useFormatters } from '@/composables/useFormatters'
import { useLogStore } from '@/stores/logs'
import type { LoggingType } from '@/types'

const { formatRelativeTime } = useFormatters()
const logStore = useLogStore()

const searchInput = ref(logStore.filters.search)
const fromDateInput = ref(logStore.filters.from_date)
const toDateInput = ref(logStore.filters.to_date)

function shortId(value: string | null | undefined): string {
  if (!value) return '—'
  return value.slice(0, 8)
}

function displayUser(username: string | null | undefined, userPublicId: string | null | undefined): string {
  if (username && username.trim().length > 0) return username
  return shortId(userPublicId)
}

function toIsoOrEmpty(value: string): string {
  if (!value) return ''
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '' : d.toISOString()
}

function onTypeChange(ev: Event) {
  const target = ev.target as HTMLSelectElement
  logStore.setFilters({ logging_type: target.value as LoggingType | '' })
}

function applyFilters() {
  logStore.setPage(1)
  logStore.setFilters({
    search: searchInput.value,
    from_date: toIsoOrEmpty(fromDateInput.value),
    to_date: toIsoOrEmpty(toDateInput.value),
  })
  logStore.fetchLogs()
}

function resetFilters() {
  logStore.resetFilters()
  searchInput.value = ''
  fromDateInput.value = ''
  toDateInput.value = ''
  logStore.fetchLogs()
}

async function handleExport() {
  await logStore.exportCsv()
}

function changePage(delta: number) {
  logStore.setPage(logStore.page + delta)
  logStore.fetchLogs()
}

onMounted(() => logStore.fetchLogs())
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.filters-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.filter-input {
  min-width: 160px;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--wm-border, #d1d5db);
  border-radius: var(--wm-radius, 8px);
  background: var(--wm-surface, #fff);
  color: var(--wm-text, #111827);

  &--grow {
    flex: 1;
    min-width: 220px;
  }
}
</style>