<template>
  <div class="view-plugin-detail">
    <div class="view-header">
      <div class="view-header-back">
        <router-link to="/plugins" class="btn-icon" title="Back to plugins" aria-label="Back">
          <i class="pi pi-arrow-left" />
        </router-link>
        <div v-if="instance">
          <h2>{{ instance.instance_name }}</h2>
          <span class="plugin-detail-meta">{{ instance.plugin_id }} &middot; <span class="badge" :class="statusBadgeClass(instance.status)">{{ instance.status }}</span></span>
        </div>
      </div>
      <div v-if="instance" class="view-header-actions">
        <button class="btn-secondary" @click="showEditDialog = true">
          <i class="pi pi-pencil" /> Edit
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading...</div>

    <template v-else-if="instance">
      <div v-if="instance.demo_mode" class="demo-banner-full">
        <i class="pi pi-info-circle" />
        <div>
          <strong>Demo Mode Active</strong>
          <p>This plugin generates simulated data. No real hardware connection.</p>
        </div>
      </div>

      <!-- Channel Mappings -->
      <div class="section">
        <div class="section-header">
          <h3>Channel Mappings</h3>
          <small>Connect plugin channels to WebMACS events for data recording</small>
        </div>

        <div v-if="channels.length" class="channel-grid">
          <div v-for="ch in channels" :key="ch.public_id" class="channel-card">
            <div class="channel-card-header">
              <div class="channel-info">
                <span class="channel-name">{{ ch.channel_name }}</span>
                <code class="channel-id">{{ ch.channel_id }}</code>
              </div>
              <div class="channel-meta">
                <span class="badge" :class="directionBadgeClass(ch.direction)">{{ ch.direction }}</span>
                <span class="channel-unit">{{ ch.unit }}</span>
              </div>
            </div>

            <div class="channel-card-body">
              <div class="channel-mapping">
                <label>Mapped Event</label>
                <div class="mapping-select-row">
                  <select
                    :value="ch.event_public_id || ''"
                    @change="handleMappingChange(ch, ($event.target as HTMLSelectElement).value)"
                  >
                    <option value="">— Not mapped —</option>
                    <option v-for="ev in events" :key="ev.public_id" :value="ev.public_id">
                      {{ ev.name }} ({{ ev.unit }})
                    </option>
                  </select>
                  <span
                    v-if="ch.event_public_id"
                    class="mapping-status mapping-status--linked"
                    title="Linked to event"
                  >
                    <i class="pi pi-link" />
                  </span>
                  <span v-else class="mapping-status mapping-status--unlinked" title="Not linked">
                    <i class="pi pi-minus-circle" />
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state empty-state--inline">
          <i class="pi pi-list" />
          No channels discovered for this plugin.
        </div>
      </div>

      <!-- Quick Create Event Helper -->
      <div class="section">
        <div class="section-header">
          <h3>Quick Create Event</h3>
          <small>Create a new event to map an unmapped channel</small>
        </div>
        <div class="quick-create">
          <p class="quick-create-hint">
            Unmapped channels won't record data. Create an event for each channel you want to monitor.
          </p>
          <router-link to="/events" class="btn-secondary">
            <i class="pi pi-bolt" /> Go to Events
          </router-link>
        </div>
      </div>
    </template>

    <!-- Edit Dialog -->
    <div v-if="showEditDialog && instance" class="dialog-overlay" @click.self="showEditDialog = false">
      <div class="dialog">
        <h3>Edit Plugin Instance</h3>
        <form @submit.prevent="handleEdit">
          <div class="form-group">
            <label>Instance Name</label>
            <input v-model="editForm.instance_name" required />
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="editForm.demo_mode" />
              Demo Mode
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="editForm.enabled" />
              Enabled
            </label>
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
import { useRoute } from 'vue-router'
import { usePluginStore } from '@/stores/plugins'
import { useEventStore } from '@/stores/events'
import { useNotification } from '@/composables/useNotification'
import type { PluginInstance, ChannelMapping, PluginStatus, ChannelDirection } from '@/types'

const route = useRoute()
const pluginStore = usePluginStore()
const eventStore = useEventStore()
const { success, error } = useNotification()

const instance = ref<PluginInstance | null>(null)
const channels = ref<ChannelMapping[]>([])
const loading = ref(true)
const showEditDialog = ref(false)
const events = ref(eventStore.events)

const editForm = reactive({
  instance_name: '',
  demo_mode: false,
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

function directionBadgeClass(dir: ChannelDirection): string {
  const map: Record<ChannelDirection, string> = {
    input: 'badge--sensor',
    output: 'badge--actuator',
    bidirectional: 'badge--range',
  }
  return map[dir] || ''
}

async function handleMappingChange(ch: ChannelMapping, eventPublicId: string) {
  try {
    await pluginStore.updateChannelMapping(
      instance.value!.public_id,
      ch.public_id,
      { event_public_id: eventPublicId || null }
    )
    ch.event_public_id = eventPublicId || null
    success('Mapping updated', `Channel "${ch.channel_name}" ${eventPublicId ? 'linked' : 'unlinked'}.`)
  } catch (err: unknown) {
    error('Failed to update mapping', (err as Error).message)
  }
}

async function handleEdit() {
  if (!instance.value) return
  try {
    await pluginStore.updateInstance(instance.value.public_id, { ...editForm })
    instance.value = await pluginStore.getInstance(instance.value.public_id)
    success('Plugin updated', `"${editForm.instance_name}" saved.`)
    showEditDialog.value = false
  } catch (err: unknown) {
    error('Failed to update plugin', (err as Error).message)
  }
}

onMounted(async () => {
  const publicId = route.params.id as string
  try {
    instance.value = await pluginStore.getInstance(publicId)
    channels.value = await pluginStore.fetchChannels(publicId)
    await eventStore.fetchEvents()
    events.value = eventStore.events

    editForm.instance_name = instance.value.instance_name
    editForm.demo_mode = instance.value.demo_mode
    editForm.enabled = instance.value.enabled
  } catch {
    error('Plugin not found', 'Could not load plugin details.')
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.view-header-back {
  display: flex;
  align-items: center;
  gap: 0.75rem;

  h2 { margin: 0; }
}

.view-header-actions {
  display: flex;
  gap: 0.5rem;
}

.plugin-detail-meta {
  font-size: 0.8rem;
  color: var(--wm-text-muted);
}

.demo-banner-full {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: var(--wm-radius-lg);
  margin-bottom: 1.5rem;

  > i {
    font-size: 1.25rem;
    color: #3b82f6;
    margin-top: 0.1rem;
  }

  strong {
    display: block;
    color: #3b82f6;
    margin-bottom: 0.15rem;
  }

  p {
    margin: 0;
    font-size: 0.85rem;
    color: var(--wm-text-muted);
  }
}

.section {
  margin-bottom: 2rem;
}

.section-header {
  margin-bottom: 1rem;

  h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0 0 0.15rem;
  }

  small {
    color: var(--wm-text-muted);
    font-size: 0.8rem;
  }
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 0.75rem;
}

.channel-card {
  background: var(--wm-surface);
  border: 1px solid var(--wm-border);
  border-radius: var(--wm-radius);
  overflow: hidden;
}

.channel-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--wm-border);
  background: var(--wm-surface-alt, rgba(0, 0, 0, 0.02));
}

.channel-info {
  display: flex;
  flex-direction: column;
}

.channel-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.channel-id {
  font-size: 0.7rem;
  color: var(--wm-text-muted);
  font-family: var(--wm-font-mono, monospace);
}

.channel-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.channel-unit {
  font-size: 0.8rem;
  color: var(--wm-text-muted);
  font-weight: 500;
}

.channel-card-body {
  padding: 0.75rem 1rem;
}

.channel-mapping {
  label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--wm-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.3rem;
  }
}

.mapping-select-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;

  select {
    flex: 1;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--wm-border);
    border-radius: var(--wm-radius);
    background: var(--wm-bg);
    color: var(--wm-text);
    font-size: 0.85rem;
  }
}

.mapping-status {
  font-size: 1rem;

  &--linked {
    color: #22c55e;
  }

  &--unlinked {
    color: var(--wm-text-muted);
  }
}

.empty-state--inline {
  padding: 1.5rem;
  font-size: 0.9rem;
}

.quick-create {
  background: var(--wm-surface);
  border: 1px solid var(--wm-border);
  border-radius: var(--wm-radius);
  padding: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.quick-create-hint {
  font-size: 0.85rem;
  color: var(--wm-text-muted);
  margin: 0;
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
