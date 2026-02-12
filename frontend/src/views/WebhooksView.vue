<template>
  <div class="view-webhooks">
    <div class="view-header">
      <h2>Webhooks</h2>
      <button class="btn-primary" @click="showCreateDialog = true">
        <i class="pi pi-plus" /> New Webhook
      </button>
    </div>

    <div v-if="webhookStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading webhooks...</div>

    <table v-else-if="webhookStore.webhooks.length" class="data-table">
      <thead>
        <tr>
          <th>URL</th>
          <th>Event Types</th>
          <th>Active</th>
          <th>Created</th>
          <th style="width: 110px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="webhook in webhookStore.webhooks" :key="webhook.public_id">
          <td class="mono" :title="webhook.url">{{ truncateUrl(webhook.url) }}</td>
          <td>
            <span
              v-for="et in webhook.events"
              :key="et"
              class="badge badge--info"
              style="margin-right: 0.25rem"
            >{{ et }}</span>
          </td>
          <td>
            <span class="badge" :class="webhook.enabled ? 'badge--sensor' : 'badge--error'">
              {{ webhook.enabled ? 'Active' : 'Inactive' }}
            </span>
          </td>
          <td>{{ formatDate(webhook.created_on) }}</td>
          <td>
            <button class="btn-icon" @click="openEdit(webhook)" title="Edit" aria-label="Edit webhook">
              <i class="pi pi-pencil" />
            </button>
            <button class="btn-icon" @click="confirmDelete(webhook)" title="Delete" aria-label="Delete webhook">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-link" />
      No webhooks configured yet. Create one to receive event notifications.
    </div>

    <div class="pagination">
      <button class="btn-secondary" :disabled="page <= 1" @click="changePage(-1)">
        <i class="pi pi-chevron-left" /> Previous
      </button>
      <span>Page {{ page }}</span>
      <button class="btn-secondary" :disabled="page * 50 >= webhookStore.total" @click="changePage(1)">
        Next <i class="pi pi-chevron-right" />
      </button>
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog">
        <h3>Create Webhook</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>URL</label>
            <input v-model="form.url" required type="url" placeholder="https://example.com/webhook" />
          </div>
          <div class="form-group">
            <label>Secret (optional)</label>
            <input v-model="form.secret" placeholder="Shared secret for verification" />
          </div>
          <div class="form-group">
            <label>Event Types</label>
            <div class="checkbox-group">
              <label v-for="et in allEventTypes" :key="et" class="checkbox-label">
                <input type="checkbox" :value="et" v-model="form.events" />
                {{ et }}
              </label>
            </div>
          </div>
          <div class="form-group">
            <label>Active</label>
            <select v-model="form.enabled">
              <option :value="true">Yes</option>
              <option :value="false">No</option>
            </select>
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
        <h3>Edit Webhook</h3>
        <form @submit.prevent="handleEdit">
          <div class="form-group">
            <label>URL</label>
            <input v-model="editForm.url" required type="url" />
          </div>
          <div class="form-group">
            <label>Secret (optional)</label>
            <input v-model="editForm.secret" placeholder="Leave blank to keep current secret" />
          </div>
          <div class="form-group">
            <label>Event Types</label>
            <div class="checkbox-group">
              <label v-for="et in allEventTypes" :key="et" class="checkbox-label">
                <input type="checkbox" :value="et" v-model="editForm.events" />
                {{ et }}
              </label>
            </div>
          </div>
          <div class="form-group">
            <label>Active</label>
            <select v-model="editForm.enabled">
              <option :value="true">Yes</option>
              <option :value="false">No</option>
            </select>
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
import { useWebhookStore } from '@/stores/webhooks'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import type { Webhook, WebhookEventType, WebhookUpdatePayload } from '@/types'

const webhookStore = useWebhookStore()
const { success, error } = useNotification()
const { formatDate } = useFormatters()

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingWebhook = ref<Webhook | null>(null)
const page = ref(1)

const allEventTypes: WebhookEventType[] = [
  'sensor.threshold_exceeded',
  'sensor.reading',
  'experiment.started',
  'experiment.stopped',
  'system.health_changed',
]

const form = reactive({
  url: '',
  secret: '',
  events: [] as WebhookEventType[],
  enabled: true,
})

const editForm = reactive({
  url: '',
  secret: '',
  events: [] as WebhookEventType[],
  enabled: true,
})

function truncateUrl(url: string): string {
  return url.length > 50 ? url.slice(0, 50) + '…' : url
}

function changePage(delta: number) {
  page.value += delta
  webhookStore.fetchWebhooks(page.value)
}

async function handleCreate() {
  try {
    await webhookStore.createWebhook({
      url: form.url,
      secret: form.secret || null,
      events: [...form.events],
      enabled: form.enabled,
    })
    success('Webhook created', `Webhook for "${form.url}" was added.`)
    showCreateDialog.value = false
    Object.assign(form, { url: '', secret: '', events: [], enabled: true })
  } catch (err: unknown) {
    error('Failed to create webhook', (err as Error).message)
  }
}

function openEdit(webhook: Webhook) {
  editingWebhook.value = webhook
  Object.assign(editForm, {
    url: webhook.url,
    secret: '',
    events: [...webhook.events],
    enabled: webhook.enabled,
  })
  showEditDialog.value = true
}

async function handleEdit() {
  if (!editingWebhook.value) return
  try {
    const payload: WebhookUpdatePayload = {
      url: editForm.url,
      events: [...editForm.events],
      enabled: editForm.enabled,
    }
    if (editForm.secret) {
      payload.secret = editForm.secret
    }
    await webhookStore.updateWebhook(editingWebhook.value.public_id, payload)
    success('Webhook updated', `Webhook was saved.`)
    showEditDialog.value = false
    editingWebhook.value = null
  } catch (err: unknown) {
    error('Failed to update webhook', (err as Error).message)
  }
}

async function confirmDelete(webhook: Webhook) {
  if (confirm(`Delete webhook "${webhook.url}"?`)) {
    try {
      await webhookStore.deleteWebhook(webhook.public_id)
      success('Webhook deleted', `Webhook was removed.`)
    } catch (err: unknown) {
      error('Failed to delete webhook', (err as Error).message)
    }
  }
}

onMounted(() => webhookStore.fetchWebhooks(page.value))
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 400;
  text-transform: none;
  letter-spacing: normal;
  cursor: pointer;

  input[type='checkbox'] {
    width: auto;
  }
}
</style>
