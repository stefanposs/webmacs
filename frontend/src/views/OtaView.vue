<template>
  <div class="view-ota">
    <div class="view-header">
      <h2>OTA Updates</h2>
      <div style="display: flex; gap: 0.5rem">
        <button class="btn-secondary" @click="triggerUpload">
          <i class="pi pi-upload" /> Upload Bundle
        </button>
        <button class="btn-primary" @click="showCreateDialog = true">
          <i class="pi pi-plus" /> New Update
        </button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept=".tar.gz,.tgz"
        style="display: none"
        @change="handleFileUpload"
      />
    </div>

    <!-- System Version Card -->
    <div class="version-card">
      <div class="version-card__info">
        <i class="pi pi-server" />
        <div>
          <div class="version-card__label">System Version</div>
          <div class="version-card__value">{{ otaStore.checkResult?.current_version ?? '—' }}</div>
        </div>
      </div>
      <div class="version-card__status">
        <template v-if="checking">
          <span class="badge badge--info">Checking…</span>
        </template>
        <template v-else-if="otaStore.checkResult?.update_available">
          <span class="badge badge--warning">Update available: {{ otaStore.checkResult.latest_version }}</span>
        </template>
        <template v-else-if="otaStore.checkResult && !otaStore.checkResult.github_error">
          <span class="badge badge--sensor">Up to date</span>
        </template>
        <template v-else-if="otaStore.checkResult?.github_error">
          <span class="badge badge--stopped" :title="otaStore.checkResult.github_error">GitHub unavailable</span>
        </template>
        <template v-else>
          <span class="badge badge--stopped">Not checked</span>
        </template>
      </div>
      <button class="btn-secondary" :disabled="checking" @click="handleCheck">
        <i class="pi pi-refresh" :class="{ 'pi-spin': checking }" /> Check for Updates
      </button>
    </div>

    <!-- GitHub Release Info -->
    <div v-if="otaStore.checkResult" class="github-card">
      <div class="github-card__header">
        <i class="pi pi-github" />
        <span>GitHub Releases</span>
        <span class="github-card__repo">{{ githubRepo }}</span>
      </div>
      <div class="github-card__body">
        <template v-if="otaStore.checkResult.github_error">
          <div class="github-card__status github-card__status--error">
            <i class="pi pi-exclamation-triangle" />
            <span>{{ otaStore.checkResult.github_error }}</span>
          </div>
        </template>
        <template v-else-if="otaStore.checkResult.github_latest_version">
          <div class="github-card__version">
            <span class="github-card__label">Latest Release</span>
            <span class="github-card__value">v{{ otaStore.checkResult.github_latest_version }}</span>
            <span v-if="isGithubNewer" class="badge badge--warning" style="margin-left: 0.5rem">newer</span>
            <span v-else class="badge badge--sensor" style="margin-left: 0.5rem">installed</span>
          </div>
          <div class="github-card__actions">
            <a
              v-if="otaStore.checkResult.github_release_url"
              :href="otaStore.checkResult.github_release_url"
              target="_blank"
              rel="noopener"
              class="btn-secondary"
            >
              <i class="pi pi-external-link" /> View Release
            </a>
            <a
              v-if="otaStore.checkResult.github_download_url"
              :href="otaStore.checkResult.github_download_url"
              class="btn-primary"
            >
              <i class="pi pi-download" /> Download Bundle
            </a>
          </div>
        </template>
        <template v-else>
          <div class="github-card__status">
            <i class="pi pi-info-circle" />
            <span>No releases published yet</span>
          </div>
        </template>
      </div>
    </div>

    <!-- Upload Progress -->
    <div v-if="uploading" class="upload-progress">
      <div class="upload-progress__bar">
        <div class="upload-progress__fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
      <span class="upload-progress__text">
        Uploading bundle… {{ uploadProgress }}%
      </span>
    </div>

    <div v-if="otaStore.loading" class="loading"><i class="pi pi-spin pi-spinner" /> Loading updates...</div>

    <table v-else-if="otaStore.updates.length" class="data-table">
      <thead>
        <tr>
          <th>Version</th>
          <th>Changelog</th>
          <th>Status</th>
          <th>Has File</th>
          <th>Created</th>
          <th>Completed</th>
          <th style="width: 150px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="update in otaStore.updates" :key="update.public_id">
          <td><strong>{{ update.version }}</strong></td>
          <td>{{ update.changelog ?? '—' }}</td>
          <td>
            <span class="badge" :class="statusBadgeClass(update.status)">{{ update.status }}</span>
            <div v-if="update.error_message" class="error-hint">{{ update.error_message }}</div>
          </td>
          <td>
            <i v-if="update.has_firmware_file" class="pi pi-check-circle" style="color: var(--wm-success)" />
            <i v-else class="pi pi-times-circle" style="color: var(--wm-text-muted)" />
          </td>
          <td>{{ formatDate(update.created_on) }}</td>
          <td>{{ formatDate(update.completed_on) }}</td>
          <td class="action-cell">
            <button
              v-if="update.status === 'pending'"
              class="btn-icon btn-apply"
              @click="handleApply(update)"
              title="Apply update"
            >
              <i class="pi pi-play" />
            </button>
            <button
              v-if="update.status === 'completed'"
              class="btn-icon btn-rollback"
              @click="handleRollback(update)"
              title="Rollback"
            >
              <i class="pi pi-undo" />
            </button>
            <button class="btn-icon" @click="confirmDelete(update)" title="Delete" aria-label="Delete firmware update">
              <i class="pi pi-trash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      <i class="pi pi-cloud-download" />
      No firmware updates yet. Create one to manage OTA deployments.
    </div>

    <div class="pagination">
      <button class="btn-secondary" :disabled="page <= 1" @click="changePage(-1)">
        <i class="pi pi-chevron-left" /> Previous
      </button>
      <span>Page {{ page }}</span>
      <button class="btn-secondary" :disabled="page * 50 >= otaStore.total" @click="changePage(1)">
        Next <i class="pi pi-chevron-right" />
      </button>
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
      <div class="dialog">
        <h3>Create Update</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Version</label>
            <input v-model="form.version" required placeholder="e.g. 1.2.0" pattern="^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$" title="Must be valid semver (e.g. 1.2.0)" />
          </div>
          <div class="form-group">
            <label>Changelog (optional)</label>
            <textarea v-model="form.changelog" rows="4" placeholder="Describe the changes in this version"></textarea>
          </div>
          <div class="dialog-actions">
            <button type="button" class="btn-secondary" @click="showCreateDialog = false">Cancel</button>
            <button type="submit" class="btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive } from 'vue'
import { useOtaStore } from '@/stores/ota'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import api from '@/services/api'
import type { FirmwareUpdate, UpdateStatus } from '@/types'

const otaStore = useOtaStore()
const { success, error } = useNotification()
const { formatDate } = useFormatters()

const showCreateDialog = ref(false)
const page = ref(1)
const checking = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

const githubRepo = 'stefanposs/webmacs'

const isGithubNewer = computed(() => {
  const cr = otaStore.checkResult
  if (!cr?.github_latest_version || !cr.current_version) return false
  const parse = (v: string) => v.split('.').map(Number)
  try {
    const cur = parse(cr.current_version)
    const gh = parse(cr.github_latest_version)
    for (let i = 0; i < 3; i++) {
      if ((gh[i] ?? 0) > (cur[i] ?? 0)) return true
      if ((gh[i] ?? 0) < (cur[i] ?? 0)) return false
    }
    return false
  } catch {
    return false
  }
})

const form = reactive({
  version: '',
  changelog: '',
})

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!file.name.endsWith('.tar.gz') && !file.name.endsWith('.tgz')) {
    error('Invalid file', 'Please select a .tar.gz update bundle.')
    return
  }

  uploading.value = true
  uploadProgress.value = 0

  try {
    const formData = new FormData()
    formData.append('file', file)

    await api.post('/ota/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) {
          uploadProgress.value = Math.round((e.loaded * 100) / e.total)
        }
      },
    })
    success('Bundle uploaded', `"${file.name}" was uploaded. The update will be applied automatically.`)
    uploadProgress.value = 100
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      ?? (err as Error).message
    error('Upload failed', msg)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function statusBadgeClass(status: UpdateStatus): string {
  const map: Record<UpdateStatus, string> = {
    pending: 'badge--warning',
    downloading: 'badge--info',
    verifying: 'badge--info',
    applying: 'badge--info',
    completed: 'badge--sensor',
    failed: 'badge--error',
    rolled_back: 'badge--stopped',
  }
  return map[status] ?? ''
}

function changePage(delta: number) {
  page.value += delta
  otaStore.fetchUpdates(page.value)
}

async function handleCheck() {
  checking.value = true
  try {
    await otaStore.checkForUpdates()
    success('Update check complete', otaStore.checkResult?.update_available ? 'A new update is available.' : 'System is up to date.')
  } catch (err: unknown) {
    error('Update check failed', (err as Error).message)
  } finally {
    checking.value = false
  }
}

async function handleCreate() {
  try {
    await otaStore.createUpdate({
      version: form.version,
      changelog: form.changelog || undefined,
    })
    success('Update created', `Version ${form.version} was added.`)
    showCreateDialog.value = false
    Object.assign(form, { version: '', changelog: '' })
  } catch (err: unknown) {
    error('Failed to create update', (err as Error).message)
  }
}

async function handleApply(update: FirmwareUpdate) {
  if (confirm(`Apply update to version ${update.version}? This will start the update process.`)) {
    try {
      await otaStore.applyUpdate(update.public_id)
      success('Update started', `Applying version ${update.version}.`)
    } catch (err: unknown) {
      error('Failed to apply update', (err as Error).message)
    }
  }
}

async function handleRollback(update: FirmwareUpdate) {
  if (confirm(`Rollback version ${update.version}? This will revert the system to the previous version.`)) {
    try {
      await otaStore.rollbackUpdate(update.public_id)
      success('Rollback started', `Rolling back version ${update.version}.`)
    } catch (err: unknown) {
      error('Rollback failed', (err as Error).message)
    }
  }
}

async function confirmDelete(update: FirmwareUpdate) {
  if (confirm(`Delete update "${update.version}"?`)) {
    try {
      await otaStore.deleteUpdate(update.public_id)
      success('Update deleted', `Version ${update.version} was removed.`)
    } catch (err: unknown) {
      error('Failed to delete update', (err as Error).message)
    }
  }
}

onMounted(async () => {
  otaStore.fetchUpdates(page.value)
  try {
    await otaStore.checkForUpdates()
  } catch {
    // silently ignore — user can manually retry via button
  }
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.version-card {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.25rem 1.5rem;
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  box-shadow: var(--wm-shadow);
  margin-bottom: 1.5rem;

  &__info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1;

    > i {
      font-size: 1.5rem;
      color: var(--wm-primary);
    }
  }

  &__label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--wm-text-secondary);
  }

  &__value {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--wm-text);
  }

  &__status {
    flex-shrink: 0;
  }
}

.error-hint {
  font-size: 0.72rem;
  color: var(--wm-danger);
  margin-top: 0.2rem;
}

.action-cell {
  display: flex;
  gap: 0.25rem;
}

.btn-apply {
  color: var(--wm-success);
  &:hover { color: #059669; background: var(--wm-success-bg); }
}

.btn-rollback {
  color: var(--wm-warning);
  &:hover { color: #d97706; background: var(--wm-warning-bg); }
}

.upload-progress {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: var(--wm-surface);
  border-radius: var(--wm-radius);
  box-shadow: var(--wm-shadow);

  &__bar {
    width: 100%;
    height: 8px;
    background: var(--wm-bg);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 0.5rem;
  }

  &__fill {
    height: 100%;
    background: var(--wm-primary);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  &__text {
    font-size: 0.8rem;
    color: var(--wm-text-secondary);
  }
}

.github-card {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  box-shadow: var(--wm-shadow);
  margin-bottom: 1.5rem;
  overflow: hidden;

  &__header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.25rem;
    background: var(--wm-bg);
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--wm-text-secondary);
    border-bottom: 1px solid var(--wm-border);

    > i { font-size: 1.1rem; }
  }

  &__repo {
    margin-left: auto;
    font-weight: 400;
    font-size: 0.78rem;
    color: var(--wm-text-muted);
    font-family: var(--wm-font-mono, monospace);
  }

  &__body {
    padding: 1rem 1.25rem;
  }

  &__version {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  &__label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--wm-text-secondary);
  }

  &__value {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--wm-text);
  }

  &__status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--wm-text-secondary);
    font-size: 0.85rem;

    > i { font-size: 1rem; }

    &--error {
      color: var(--wm-warning);
    }
  }

  &__actions {
    display: flex;
    gap: 0.5rem;
  }
}
</style>
