<template>
  <div class="view-tokens">
    <div class="view-header">
      <h2>API Tokens</h2>
      <button class="btn-primary" @click="showCreateDialog = true">
        <i class="pi pi-plus" /> New Token
      </button>
    </div>

    <div v-if="loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading tokens...</div>

    <table v-else-if="tokens.length" class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Created</th>
          <th>Last Used</th>
          <th>Expires</th>
          <th style="width: 80px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="token in tokens" :key="token.public_id">
          <td>{{ token.name }}</td>
          <td>{{ formatDate(token.created_at) }}</td>
          <td>{{ token.last_used_at ? formatDate(token.last_used_at) : 'Never' }}</td>
          <td>
            <span v-if="token.expires_at" :class="isExpired(token.expires_at) ? 'badge badge--error' : ''">
              {{ formatDate(token.expires_at) }}
            </span>
            <span v-else class="badge badge--info">Never</span>
          </td>
          <td>
            <button class="btn-icon" @click="confirmDelete(token)" title="Revoke" aria-label="Revoke token">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-key" />
      No API tokens yet. Create one for machine-to-machine authentication.
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog">
        <h3>Create API Token</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" required placeholder="e.g. Controller Token" />
          </div>
          <div class="form-group">
            <label>Expires (optional)</label>
            <input v-model="form.expires_at" type="datetime-local" />
          </div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="showCreateDialog = false">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="creating">
              <i v-if="creating" class="pi pi-spin pi-spinner" /> Create
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Token Created Dialog (show once) -->
    <div v-if="newToken" class="dialog-overlay">
      <div class="dialog">
        <h3>Token Created</h3>
        <p class="token-warning">
          <i class="pi pi-exclamation-triangle" />
          Copy this token now. It will not be shown again.
        </p>
        <div class="token-display">
          <code>{{ newToken }}</code>
          <button class="btn-icon" @click="copyToken" title="Copy">
            <i class="pi pi-copy" />
          </button>
        </div>
        <div class="dialog-actions">
          <button class="btn-primary" @click="newToken = null">Done</button>
        </div>
      </div>
    </div>

    <!-- Delete Confirm Dialog -->
    <div v-if="tokenToDelete" class="dialog-overlay" @click.self="tokenToDelete = null">
      <div class="dialog">
        <h3>Revoke Token</h3>
        <p>Are you sure you want to revoke <strong>{{ tokenToDelete.name }}</strong>? This cannot be undone.</p>
        <div class="dialog-actions">
          <button class="btn-secondary" @click="tokenToDelete = null">Cancel</button>
          <button class="btn-danger" @click="handleDelete">Revoke</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/services/api'
import type { ApiToken, ApiTokenCreated, PaginatedResponse } from '@/types'

const tokens = ref<ApiToken[]>([])
const loading = ref(false)
const creating = ref(false)
const showCreateDialog = ref(false)
const newToken = ref<string | null>(null)
const tokenToDelete = ref<ApiToken | null>(null)

const form = ref({ name: '', expires_at: '' })

async function fetchTokens() {
  loading.value = true
  try {
    const { data } = await api.get<PaginatedResponse<ApiToken>>('/tokens')
    tokens.value = data.data
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    const payload: Record<string, unknown> = { name: form.value.name }
    if (form.value.expires_at) {
      payload.expires_at = new Date(form.value.expires_at).toISOString()
    }
    const { data } = await api.post<ApiTokenCreated>('/tokens', payload)
    newToken.value = data.token
    showCreateDialog.value = false
    form.value = { name: '', expires_at: '' }
    await fetchTokens()
  } finally {
    creating.value = false
  }
}

function confirmDelete(token: ApiToken) {
  tokenToDelete.value = token
}

async function handleDelete() {
  if (!tokenToDelete.value) return
  await api.delete(`/tokens/${tokenToDelete.value.public_id}`)
  tokenToDelete.value = null
  await fetchTokens()
}

function copyToken() {
  if (newToken.value) {
    navigator.clipboard.writeText(newToken.value)
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function isExpired(dateStr: string): boolean {
  return new Date(dateStr) < new Date()
}

onMounted(fetchTokens)
</script>

<style scoped lang="scss">
@import '@/assets/styles/views-shared';

.token-warning {
  color: var(--wm-warning);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-weight: 500;
}

.token-display {
  background: var(--wm-border-light);
  border: 1px solid var(--wm-border);
  border-radius: var(--wm-radius);
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.token-display code {
  flex: 1;
  word-break: break-all;
  font-size: 0.85rem;
  color: var(--wm-primary);
}
</style>
