<template>
  <div class="view-plugins">
    <div class="view-header">
      <h2>Plugins</h2>
      <div style="display: flex; gap: 0.5rem">
        <router-link to="/plugins/packages" class="btn-secondary">
          <i class="pi pi-box" /> Packages
        </router-link>
        <button class="btn-primary" @click="showInstallDialog = true">
          <i class="pi pi-plus" /> New Instance
        </button>
      </div>
    </div>

    <div v-if="pluginStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading plugins...</div>

    <div v-else-if="pluginStore.instances.length" class="plugin-grid">
      <div
        v-for="instance in pluginStore.instances"
        :key="instance.public_id"
        class="plugin-card"
        :class="{ 'plugin-card--disabled': !instance.enabled }"
      >
        <div class="plugin-card-header">
          <div class="plugin-card-title">
            <i class="pi pi-microchip" />
            <div>
              <h3>{{ instance.instance_name }}</h3>
              <span class="plugin-card-type">{{ instance.plugin_id }}</span>
            </div>
          </div>
          <span class="badge" :class="statusBadgeClass(instance.status)">{{ instance.status }}</span>
        </div>

        <div class="plugin-card-body">
          <div class="plugin-card-stats">
            <div class="stat">
              <span class="stat-value">{{ instance.channel_mappings.length }}</span>
              <span class="stat-label">Channels</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ mappedCount(instance) }}</span>
              <span class="stat-label">Mapped</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ instance.demo_mode ? 'Yes' : 'No' }}</span>
              <span class="stat-label">Demo</span>
            </div>
          </div>

          <div v-if="instance.demo_mode" class="demo-banner">
            <i class="pi pi-info-circle" /> Demo mode — generating simulated data
          </div>

          <div v-if="instance.error_message" class="error-banner">
            <i class="pi pi-exclamation-triangle" /> {{ instance.error_message }}
          </div>
        </div>

        <div class="plugin-card-actions">
          <router-link :to="`/plugins/${instance.public_id}`" class="btn-secondary btn-sm">
            <i class="pi pi-cog" /> Configure
          </router-link>
          <button class="btn-icon" @click="confirmDelete(instance)" title="Delete" aria-label="Delete plugin">
            <i class="pi pi-trash" />
          </button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <i class="pi pi-microchip" />
      <p>No plugins installed yet.</p>
      <p class="empty-hint">
        Install a plugin to connect sensors and actuators to your WebMACS system.
      </p>
      <div style="display: flex; gap: 0.5rem">
        <router-link to="/plugins/packages" class="btn-secondary">
          <i class="pi pi-box" /> Manage Packages
        </router-link>
        <button class="btn-primary" @click="showInstallDialog = true">
          <i class="pi pi-plus" /> New Instance
        </button>
      </div>
    </div>

    <!-- Install Dialog -->
    <div v-if="showInstallDialog" class="dialog-overlay" @click.self="showInstallDialog = false">
      <div class="dialog dialog--wide">
        <h3>New Plugin Instance</h3>

        <div v-if="!availablePlugins.length" class="dialog-empty">
          <i class="pi pi-info-circle" />
          <p>No plugin packages found. <router-link to="/plugins/packages">Upload a package</router-link> first.</p>
        </div>

        <template v-else>
          <div class="plugin-select">
            <div
              v-for="plugin in availablePlugins"
              :key="plugin.id"
              class="plugin-option"
              :class="{ 'plugin-option--selected': installForm.plugin_id === plugin.id }"
              @click="selectPlugin(plugin)"
            >
              <div class="plugin-option-info">
                <strong>{{ plugin.name }}</strong>
                <span class="plugin-option-version">v{{ plugin.version }}</span>
                <span class="plugin-option-vendor">by {{ plugin.vendor }}</span>
              </div>
              <p class="plugin-option-desc">{{ plugin.description }}</p>
            </div>
          </div>

          <form v-if="installForm.plugin_id" @submit.prevent="handleInstall">
            <div class="form-group">
              <label>Instance Name</label>
              <input
                v-model="installForm.instance_name"
                required
                placeholder="e.g. Lab Sensor Rack 1"
              />
              <small class="form-hint">A friendly name to identify this plugin instance.</small>
            </div>

            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="installForm.demo_mode" />
                Demo Mode
              </label>
              <small class="form-hint">
                Generate simulated data instead of reading real hardware. Great for testing.
              </small>
            </div>

            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showInstallDialog = false">Cancel</button>
              <button type="submit" class="btn-primary">
                <i class="pi pi-download" /> Install
              </button>
            </div>
          </form>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive, computed } from 'vue'
import { usePluginStore } from '@/stores/plugins'
import { useNotification } from '@/composables/useNotification'
import type { PluginMeta, PluginInstance, PluginStatus } from '@/types'

const pluginStore = usePluginStore()
const { success, error } = useNotification()
const showInstallDialog = ref(false)
const availablePlugins = computed(() => pluginStore.availablePlugins)

const installForm = reactive({
  plugin_id: '',
  instance_name: '',
  demo_mode: true,
  enabled: true,
})

function statusBadgeClass(status: PluginStatus): string {
  const map: Record<PluginStatus, string> = {
    connected: 'badge--sensor',
    demo: 'badge--range',
    inactive: 'badge--cmd_button',
    error: 'badge--actuator',
  }
  return map[status] || ''
}

function mappedCount(instance: PluginInstance): number {
  return instance.channel_mappings.filter((m) => m.event_public_id).length
}

function selectPlugin(plugin: PluginMeta) {
  installForm.plugin_id = plugin.id
  if (!installForm.instance_name) {
    installForm.instance_name = plugin.name
  }
}

async function handleInstall() {
  try {
    await pluginStore.createInstance({ ...installForm })
    success('Plugin installed', `"${installForm.instance_name}" is ready.`)
    showInstallDialog.value = false
    Object.assign(installForm, { plugin_id: '', instance_name: '', demo_mode: true, enabled: true })
  } catch (err: unknown) {
    error('Failed to install plugin', (err as Error).message)
  }
}

async function confirmDelete(instance: PluginInstance) {
  if (confirm(`Remove plugin "${instance.instance_name}" and all its channel mappings?`)) {
    try {
      await pluginStore.deleteInstance(instance.public_id)
      success('Plugin removed', `"${instance.instance_name}" was deleted.`)
    } catch (err: unknown) {
      error('Failed to remove plugin', (err as Error).message)
    }
  }
}

onMounted(async () => {
  await Promise.all([pluginStore.fetchInstances(), pluginStore.fetchAvailablePlugins()])
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.plugin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1rem;
}

.plugin-card {
  background: var(--wm-surface);
  border: 1px solid var(--wm-border);
  border-radius: var(--wm-radius-lg);
  overflow: hidden;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;

  &:hover {
    border-color: var(--wm-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  &--disabled {
    opacity: 0.6;
  }
}

.plugin-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--wm-border);
}

.plugin-card-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;

  > i {
    font-size: 1.5rem;
    color: var(--wm-primary);
  }

  h3 {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
    color: var(--wm-text);
  }
}

.plugin-card-type {
  font-size: 0.75rem;
  color: var(--wm-text-muted);
}

.plugin-card-body {
  padding: 1rem 1.25rem;
}

.plugin-card-stats {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 0.75rem;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--wm-text);
}

.stat-label {
  font-size: 0.7rem;
  color: var(--wm-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.demo-banner {
  padding: 0.5rem 0.75rem;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--wm-radius);
  font-size: 0.8rem;
  color: #3b82f6;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.error-banner {
  padding: 0.5rem 0.75rem;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--wm-radius);
  font-size: 0.8rem;
  color: #ef4444;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.plugin-card-actions {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--wm-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.btn-sm {
  font-size: 0.8rem;
  padding: 0.35rem 0.75rem;
}

.empty-hint {
  font-size: 0.9rem;
  color: var(--wm-text-muted);
  margin-bottom: 1rem;
}

// Install dialog
.dialog--wide {
  max-width: 560px;
}

.dialog-empty {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--wm-text-muted);

  > i {
    font-size: 2rem;
    margin-bottom: 0.75rem;
    display: block;
  }
}

.plugin-select {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.plugin-option {
  padding: 0.8rem 1rem;
  border: 2px solid var(--wm-border);
  border-radius: var(--wm-radius);
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    border-color: var(--wm-primary);
    background: rgba(59, 130, 246, 0.04);
  }

  &--selected {
    border-color: var(--wm-primary);
    background: rgba(59, 130, 246, 0.08);
  }
}

.plugin-option-info {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.plugin-option-version {
  font-size: 0.75rem;
  color: var(--wm-text-muted);
}

.plugin-option-vendor {
  font-size: 0.75rem;
  color: var(--wm-text-muted);
}

.plugin-option-desc {
  font-size: 0.8rem;
  color: var(--wm-text-muted);
  margin: 0;
}

.form-hint {
  display: block;
  font-size: 0.75rem;
  color: var(--wm-text-muted);
  margin-top: 0.25rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 500;

  input[type="checkbox"] {
    width: 1rem;
    height: 1rem;
    accent-color: var(--wm-primary);
  }
}
</style>
