<template>
  <div class="view-datapoints">
    <div class="view-header">
      <h2>Datapoints</h2>
      <span class="total-badge" v-if="datapointStore.total">{{ datapointStore.total.toLocaleString() }} total</span>
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
import { computed, onMounted, ref } from 'vue'
import { useDatapointStore } from '@/stores/datapoints'
import { usePluginStore } from '@/stores/plugins'
import { useFormatters } from '@/composables/useFormatters'

const datapointStore = useDatapointStore()
const pluginStore = usePluginStore()
const { formatDate, formatNumber } = useFormatters()
const page = ref(1)

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

function changePage(delta: number) {
  page.value += delta
  datapointStore.fetchDatapoints(page.value)
}

onMounted(() => {
  datapointStore.fetchDatapoints(page.value)
  pluginStore.fetchInstances()
})
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
