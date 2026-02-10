<template>
  <div class="view-logs">
    <div class="view-header">
      <h2>Logs</h2>
    </div>

    <div v-if="loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading logs...</div>

    <table v-else-if="logs.length" class="data-table">
      <thead>
        <tr>
          <th style="width: 160px">Timestamp</th>
          <th style="width: 100px">Type</th>
          <th style="width: 100px">Status</th>
          <th>Message</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="log in logs" :key="log.public_id">
          <td class="mono">{{ formatRelativeTime(log.user_public_id) }}</td>
          <td><span class="badge" :class="`badge--${log.logging_type}`">{{ log.logging_type }}</span></td>
          <td>{{ log.status_type ?? '—' }}</td>
          <td>{{ log.content }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-file-edit" />
      No log entries yet.
    </div>

    <div class="pagination">
      <button class="btn-secondary" :disabled="page <= 1" @click="changePage(-1)">
        <i class="pi pi-chevron-left" /> Previous
      </button>
      <span>Page {{ page }}</span>
      <button class="btn-secondary" @click="changePage(1)">
        Next <i class="pi pi-chevron-right" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/services/api'
import { useFormatters } from '@/composables/useFormatters'
import type { LogEntry, PaginatedResponse } from '@/types'

const { formatRelativeTime } = useFormatters()
const logs = ref<LogEntry[]>([])
const loading = ref(false)
const page = ref(1)

async function fetchLogs() {
  loading.value = true
  try {
    const { data } = await api.get<PaginatedResponse<LogEntry>>('/logging/', {
      params: { page: page.value, page_size: 50 },
    })
    logs.value = data.data
  } finally {
    loading.value = false
  }
}

function changePage(delta: number) {
  page.value += delta
  fetchLogs()
}

onMounted(fetchLogs)
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';
</style>
