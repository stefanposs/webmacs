<template>
  <div class="view-datapoints">
    <div class="view-header">
      <h2>Datapoints</h2>
      <span class="total-badge" v-if="datapointStore.total">{{ datapointStore.total.toLocaleString() }} total</span>
    </div>

    <div v-if="datapointStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading datapoints...</div>

    <table v-else-if="datapointStore.datapoints.length" class="data-table">
      <thead>
        <tr>
          <th>Public ID</th>
          <th>Event</th>
          <th>Value</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="dp in datapointStore.datapoints" :key="dp.public_id">
          <td class="mono">{{ dp.public_id.slice(0, 8) }}…</td>
          <td class="mono">{{ dp.event_public_id.slice(0, 8) }}…</td>
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
      <span>Page {{ page }}</span>
      <button class="btn-secondary" @click="changePage(1)">
        Next <i class="pi pi-chevron-right" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useDatapointStore } from '@/stores/datapoints'
import { useFormatters } from '@/composables/useFormatters'

const datapointStore = useDatapointStore()
const { formatDate, formatNumber } = useFormatters()
const page = ref(1)

function changePage(delta: number) {
  page.value += delta
  datapointStore.fetchDatapoints(page.value)
}

onMounted(() => datapointStore.fetchDatapoints(page.value))
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.total-badge {
  font-size: 0.8rem;
  background: var(--wm-border-light);
  color: var(--wm-text-secondary);
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-weight: 600;
}
</style>
