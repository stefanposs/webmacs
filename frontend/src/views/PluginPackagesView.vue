<template>
  <div class="view-packages">
    <div class="view-header">
      <h2>Plugin Packages</h2>
      <div style="display: flex; gap: 0.5rem">
        <router-link to="/plugins" class="btn-secondary">
          <i class="pi pi-arrow-left" /> Back to Plugins
        </router-link>
        <button class="btn-primary" @click="triggerUpload">
          <i class="pi pi-upload" /> Upload Package
        </button>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept=".whl"
        style="display: none"
        @change="handleFileUpload"
      />
    </div>

    <!-- Upload progress -->
    <div v-if="pluginStore.uploading" class="upload-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: pluginStore.uploadProgress + '%' }" />
      </div>
      <span class="progress-text">Uploading… {{ pluginStore.uploadProgress }}%</span>
    </div>

    <!-- Package list -->
    <div v-if="pluginStore.packages.length" class="package-grid">
      <div
        v-for="pkg in pluginStore.packages"
        :key="pkg.public_id"
        class="package-card"
        :class="{ 'package-card--uploaded': pkg.source === 'uploaded' }"
      >
        <div class="package-card-header">
          <div class="package-card-title">
            <i :class="pkg.source === 'bundled' ? 'pi pi-box' : 'pi pi-cloud-upload'" />
            <div>
              <h3>{{ pkg.package_name }}</h3>
              <span class="package-card-version">v{{ pkg.version }}</span>
            </div>
          </div>
          <span
            class="badge"
            :class="pkg.source === 'bundled' ? 'badge--sensor' : 'badge--range'"
          >
            {{ pkg.source }}
          </span>
        </div>

        <div class="package-card-body">
          <div class="package-card-meta">
            <div v-if="pkg.plugin_ids.length" class="meta-item">
              <span class="meta-label">Plugins:</span>
              <span class="meta-value">{{ pkg.plugin_ids.join(', ') }}</span>
            </div>
            <div v-if="pkg.file_size_bytes" class="meta-item">
              <span class="meta-label">Size:</span>
              <span class="meta-value">{{ formatBytes(pkg.file_size_bytes) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Installed:</span>
              <span class="meta-value">{{ formatDate(pkg.installed_on) }}</span>
            </div>
          </div>
        </div>

        <div v-if="pkg.removable" class="package-card-actions">
          <button class="btn-danger btn-sm" @click="confirmUninstall(pkg)">
            <i class="pi pi-trash" /> Uninstall
          </button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <i class="pi pi-box" />
      <p>No plugin packages registered yet.</p>
      <p class="empty-hint">
        Bundled plugins are registered automatically on first start.
        Upload a <code>.whl</code> file to add custom plugins.
      </p>
      <button class="btn-primary" @click="triggerUpload">
        <i class="pi pi-upload" /> Upload your first plugin
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { usePluginStore } from '@/stores/plugins'
import { useNotification } from '@/composables/useNotification'
import { useFormatters } from '@/composables/useFormatters'
import type { PluginPackage } from '@/types'

const pluginStore = usePluginStore()
const { success, error } = useNotification()
const { formatDate } = useFormatters()
const fileInput = ref<HTMLInputElement | null>(null)

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.name.endsWith('.whl')) {
    error('Invalid file', 'Please select a .whl (Python wheel) plugin package.')
    return
  }
  try {
    await pluginStore.uploadPackage(file)
    success('Package uploaded', `"${file.name}" was installed. Restart the controller to activate.`)
  } catch (err: unknown) {
    const msg =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      (err as Error).message
    error('Upload failed', msg)
  } finally {
    input.value = ''
  }
}

async function confirmUninstall(pkg: PluginPackage) {
  if (!confirm(`Uninstall "${pkg.package_name}"? Any plugin instances using it will stop working.`)) {
    return
  }
  try {
    await pluginStore.uninstallPackage(pkg.public_id)
    success('Package removed', `"${pkg.package_name}" was uninstalled.`)
  } catch (err: unknown) {
    error('Uninstall failed', (err as Error).message)
  }
}

onMounted(async () => {
  await pluginStore.fetchPackages()
})
</script>

<style lang="scss" scoped>
@import '@/assets/styles/views-shared';

.upload-progress {
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--wm-border);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--wm-primary);
  transition: width 0.2s ease;
}

.progress-text {
  font-size: 0.8rem;
  color: var(--wm-text-muted);
  white-space: nowrap;
}

.package-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1rem;
}

.package-card {
  background: var(--wm-surface);
  border: 1px solid var(--wm-border);
  border-radius: var(--wm-radius-lg);
  overflow: hidden;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;

  &:hover {
    border-color: var(--wm-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  &--uploaded {
    border-left: 3px solid var(--wm-primary);
  }
}

.package-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--wm-border);
}

.package-card-title {
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

.package-card-version {
  font-size: 0.75rem;
  color: var(--wm-text-muted);
}

.package-card-body {
  padding: 1rem 1.25rem;
}

.package-card-meta {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.meta-label {
  color: var(--wm-text-muted);
  min-width: 70px;
}

.meta-value {
  color: var(--wm-text);
}

.package-card-actions {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--wm-border);
  display: flex;
  justify-content: flex-end;
}

.btn-danger {
  background: var(--wm-danger, #ef4444);
  color: #fff;
  border: none;
  border-radius: var(--wm-radius);
  padding: 0.4rem 0.8rem;
  cursor: pointer;
  font-size: 0.8rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  transition: opacity 0.15s ease;

  &:hover {
    opacity: 0.85;
  }
}

.btn-sm {
  font-size: 0.8rem;
  padding: 0.35rem 0.75rem;
}

.empty-hint {
  font-size: 0.9rem;
  color: var(--wm-text-muted);
  margin-bottom: 1rem;

  code {
    background: var(--wm-surface);
    padding: 0.15rem 0.35rem;
    border-radius: 3px;
    font-size: 0.85rem;
  }
}
</style>
