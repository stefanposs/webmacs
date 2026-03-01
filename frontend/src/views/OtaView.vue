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

    <!-- ── Per-Service Version Cards ─────────────────────────────────── -->
    <div class="services-grid">
      <div
        v-for="svc in systemStore.versions"
        :key="svc.name"
        class="svc-card"
        :class="`svc-card--${svc.status}`"
      >
        <div class="svc-card__header">
          <i :class="serviceIcon(svc.name)" class="svc-card__icon" />
          <span class="svc-card__name">{{ serviceLabel(svc.name) }}</span>
          <span class="badge" :class="statusBadgeClass(svc.status)">{{ serviceStatusLabel(svc.status) }}</span>
        </div>

        <div class="svc-card__versions">
          <div class="svc-card__version-row">
            <span class="svc-card__version-label">Installed</span>
            <span class="svc-card__version-value">{{ svc.installed ?? '—' }}</span>
          </div>
          <div class="svc-card__version-row">
            <span class="svc-card__version-label">Available</span>
            <span class="svc-card__version-value">
              <template v-if="svc.available">
                <span :class="isNewer(svc.available, svc.installed) ? 'text-warn' : 'text-ok'">
                  {{ svc.available }}
                </span>
                <span v-if="isNewer(svc.available, svc.installed)" class="badge badge--warning" style="margin-left:0.4rem">new</span>
              </template>
              <template v-else>
                <span class="svc-card__version-value--muted">—</span>
              </template>
            </span>
          </div>
        </div>

        <div class="svc-card__image">
          <i class="pi pi-box" /> {{ svc.image ?? '—' }}
        </div>
      </div>

      <!-- Skeleton cards while loading -->
      <template v-if="systemStore.loading && !systemStore.versions.length">
        <div v-for="n in 3" :key="n" class="svc-card svc-card--loading">
          <div class="svc-card__header">
            <i class="pi pi-server svc-card__icon" />
            <span class="svc-card__name skeleton skeleton--text" style="width:80px" />
          </div>
        </div>
      </template>
    </div>

    <!-- ── One-Click Update Section ──────────────────────────────────── -->
    <div class="update-section">
      <!-- Update Progress (active) -->
      <div v-if="systemStore.isUpdating || justFinished" class="update-progress-card">
        <div class="update-progress-card__header">
          <i class="pi" :class="systemStore.isUpdating ? 'pi-spin pi-spinner' : (systemStore.updateProgress?.overall_status === 'completed' ? 'pi-check-circle' : 'pi-times-circle')" />
          <span>{{ systemStore.updateProgress?.current_step ?? 'Updating…' }}</span>
        </div>
        <div class="update-steps">
          <div
            v-for="svc in ['backend', 'frontend', 'controller']"
            :key="svc"
            class="update-step"
            :class="`update-step--${systemStore.updateProgress?.services[svc] ?? 'unknown'}`"
          >
            <i class="pi" :class="stepIcon(systemStore.updateProgress?.services[svc])" />
            <span>{{ serviceLabel(svc) }}</span>
          </div>
        </div>
        <div v-if="systemStore.updateProgress?.error" class="update-progress-card__error">
          <i class="pi pi-exclamation-triangle" /> {{ systemStore.updateProgress.error }}
        </div>
      </div>

      <!-- Trigger button (idle / has update) -->
      <div v-else class="update-trigger">
        <div v-if="hasUpdateAvailable" class="update-trigger__info">
          <i class="pi pi-info-circle" />
          <span>Version <strong>{{ latestAvailable }}</strong> is available for all services.</span>
        </div>
        <div v-else-if="systemStore.versions.length" class="update-trigger__info update-trigger__info--ok">
          <i class="pi pi-check-circle" />
          <span>All services are up to date.</span>
        </div>

        <div style="display:flex; gap:0.75rem; align-items:center; flex-wrap:wrap">
          <button
            class="btn-secondary"
            :disabled="systemStore.loading"
            @click="handleRefreshVersions"
          >
            <i class="pi pi-refresh" :class="{ 'pi-spin': systemStore.loading }" /> Refresh Status
          </button>
          <button
            v-if="hasUpdateAvailable && authStore.isAdmin"
            class="btn-primary"
            @click="handleOneClickUpdate"
          >
            <i class="pi pi-cloud-download" /> Update to {{ latestAvailable }}
          </button>
        </div>
      </div>
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
    <div v-else style="margin-bottom:1rem">
      <button class="btn-secondary" :disabled="checking" @click="handleCheck">
        <i class="pi pi-github" :class="{ 'pi-spin': checking }" /> Check GitHub Releases
      </button>
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

    <div v-else-if="otaStore.updates.length" class="table-responsive">
    <table class="data-table">
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
            <span class="badge" :class="otaBadgeClass(update.status)">{{ update.status }}</span>
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
    </div>

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
import { useSystemStore } from '@/stores/system'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import api from '@/services/api'
import type { FirmwareUpdate, UpdateStatus, ServiceStatus } from '@/types'
import { useAuthStore } from '@/stores/auth'

const otaStore = useOtaStore()
const systemStore = useSystemStore()
const { success, error } = useNotification()
const { formatDate } = useFormatters()
const authStore = useAuthStore()

const showCreateDialog = ref(false)
const page = ref(1)
const checking = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

const githubRepo = 'stefanposs/webmacs'

/** True for a few seconds after update completes, so progress card stays visible. */
const justFinished = ref(false)

// ── Computed ────────────────────────────────────────────────────────────────

const latestAvailable = computed<string | null>(() => {
  for (const svc of systemStore.versions) {
    if (svc.available) return svc.available
  }
  return null
})

const hasUpdateAvailable = computed<boolean>(() => {
  return systemStore.versions.some((svc) => isNewer(svc.available, svc.installed))
})

// ── Helpers ─────────────────────────────────────────────────────────────────

function isNewer(available: string | null, installed: string | null): boolean {
  if (!available || !installed) return false
  const clean = (v: string) => v.replace(/^v/, '')
  const parse = (v: string) => clean(v).split('.').map(Number)
  try {
    const a = parse(available)
    const b = parse(installed)
    for (let i = 0; i < 3; i++) {
      if ((a[i] ?? 0) > (b[i] ?? 0)) return true
      if ((a[i] ?? 0) < (b[i] ?? 0)) return false
    }
    return false
  } catch {
    return false
  }
}

function serviceIcon(name: string): string {
  const icons: Record<string, string> = {
    backend: 'pi pi-server',
    frontend: 'pi pi-desktop',
    controller: 'pi pi-microchip',
  }
  return icons[name] ?? 'pi pi-box'
}

function serviceLabel(name: string): string {
  const labels: Record<string, string> = {
    backend: 'Backend',
    frontend: 'Frontend',
    controller: 'Controller',
  }
  return labels[name] ?? name
}

function serviceStatusLabel(status: ServiceStatus): string {
  const labels: Record<ServiceStatus, string> = {
    running: 'Running',
    stopped: 'Stopped',
    error: 'Error',
    updating: 'Updating…',
    unknown: 'Unknown',
  }
  return labels[status] ?? status
}

function statusBadgeClass(status: ServiceStatus): string {
  const map: Record<ServiceStatus, string> = {
    running: 'badge--sensor',
    stopped: 'badge--stopped',
    error: 'badge--error',
    updating: 'badge--info',
    unknown: 'badge--stopped',
  }
  return map[status] ?? ''
}

function stepIcon(status: ServiceStatus | undefined): string {
  switch (status) {
    case 'running': return 'pi-check-circle'
    case 'updating': return 'pi-spin pi-spinner'
    case 'error': return 'pi-times-circle'
    default: return 'pi-circle'
  }
}

function otaBadgeClass(status: UpdateStatus): string {
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

const form = reactive({ version: '', changelog: '' })

// ── Actions ─────────────────────────────────────────────────────────────────

function triggerUpload() {
  fileInput.value?.click()
}

async function handleRefreshVersions() {
  await systemStore.fetchVersions()
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
        if (e.total) uploadProgress.value = Math.round((e.loaded * 100) / e.total)
      },
    })
    success('Bundle uploaded', `"${file.name}" was uploaded. The update will be applied automatically.`)
    uploadProgress.value = 100
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (err as Error).message
    error('Upload failed', msg)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function changePage(delta: number) {
  page.value += delta
  otaStore.fetchUpdates(page.value)
}

async function handleCheck() {
  checking.value = true
  try {
    await otaStore.checkForUpdates()
  } catch (err: unknown) {
    error('Update check failed', (err as Error).message)
  } finally {
    checking.value = false
  }
}

async function handleCreate() {
  try {
    await otaStore.createUpdate({ version: form.version, changelog: form.changelog || undefined })
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

async function handleOneClickUpdate() {
  if (!authStore.isAdmin) {
    error('Unauthorized', 'Only administrators can perform system updates.')
    return
  }
  const latest = latestAvailable.value
  if (!latest) {
    error('No release', 'No available version found.')
    return
  }
  justFinished.value = false
  try {
    await systemStore.triggerUpdate(latest)
    success('Update started', `Pulling version ${latest} for all services.`)
    // Watch for completion then briefly keep progress card visible
    const prev = systemStore.updateProgress?.overall_status
    if (prev) {
      const watcher = setInterval(() => {
        const s = systemStore.updateProgress?.overall_status
        if (s === 'completed' || s === 'failed') {
          clearInterval(watcher)
          justFinished.value = true
          setTimeout(() => { justFinished.value = false }, 5000)
        }
      }, 500)
    }
  } catch (err: unknown) {
    error('Update trigger failed', (err as Error).message)
  }
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  otaStore.fetchUpdates(page.value)
  systemStore.initialize()
  try {
    await otaStore.checkForUpdates()
  } catch {
    // silently ignore — user can retry manually
  }
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

// ── Services Grid ───────────────────────────────────────────────────────────
.services-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.25rem;

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
}

.svc-card {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  box-shadow: var(--wm-shadow);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-left: 4px solid var(--wm-border);
  transition: border-color 0.2s;

  &--running  { border-left-color: var(--wm-success); }
  &--stopped  { border-left-color: var(--wm-text-muted); }
  &--error    { border-left-color: var(--wm-danger); }
  &--updating { border-left-color: var(--wm-primary); }
  &--unknown  { border-left-color: var(--wm-border); }

  &__header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  &__icon {
    font-size: 1.3rem;
    color: var(--wm-primary);
  }

  &__name {
    font-weight: 700;
    font-size: 1rem;
    color: var(--wm-text);
    flex: 1;
  }

  &__versions {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  &__version-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  &__version-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--wm-text-secondary);
    min-width: 4.5rem;
  }

  &__version-value {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--wm-text);
    display: flex;
    align-items: center;
    gap: 0.35rem;

    &--muted {
      color: var(--wm-text-muted);
      font-weight: 400;
    }
  }

  &__image {
    font-size: 0.72rem;
    color: var(--wm-text-muted);
    font-family: var(--wm-font-mono, monospace);
    display: flex;
    align-items: center;
    gap: 0.3rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.text-warn { color: var(--wm-warning); }
.text-ok   { color: var(--wm-success); }

// ── Update Section ──────────────────────────────────────────────────────────
.update-section {
  margin-bottom: 1.25rem;
}

.update-progress-card {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  box-shadow: var(--wm-shadow);
  padding: 1.25rem 1.5rem;

  &__header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-weight: 700;
    margin-bottom: 1rem;
    font-size: 1rem;

    > i { font-size: 1.25rem; color: var(--wm-primary); }
  }

  &__error {
    margin-top: 0.75rem;
    color: var(--wm-danger);
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
}

.update-steps {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.update-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;

  > i { font-size: 1rem; }

  &--running  > i, &--completed > i { color: var(--wm-success); }
  &--updating > i { color: var(--wm-primary); }
  &--error    > i { color: var(--wm-danger); }
  &--unknown  > i, &--stopped > i   { color: var(--wm-text-muted); }
}

.update-trigger {
  background: var(--wm-surface);
  border-radius: var(--wm-radius-lg);
  box-shadow: var(--wm-shadow);
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;

  &__info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    color: var(--wm-text-secondary);
    font-size: 0.9rem;

    > i { font-size: 1.1rem; color: var(--wm-warning); }

    &--ok > i { color: var(--wm-success); }
  }
}

// ── GitHub Card ─────────────────────────────────────────────────────────────
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

  &__body { padding: 1rem 1.25rem; }

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

    &--error { color: var(--wm-warning); }
  }

  &__actions {
    display: flex;
    gap: 0.5rem;
  }
}

// ── Error / Misc ─────────────────────────────────────────────────────────────
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

// ── Skeleton ─────────────────────────────────────────────────────────────────
.skeleton {
  background: var(--wm-bg);
  border-radius: 4px;
  animation: skeleton-pulse 1.5s ease-in-out infinite;

  &--text {
    display: inline-block;
    height: 1rem;
  }
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
</style>
