import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type {
  PluginMeta,
  PluginInstance,
  PluginInstanceCreatePayload,
  PluginInstanceUpdatePayload,
  ChannelMapping,
  ChannelMappingUpdatePayload,
  PluginPackage,
  PaginatedResponse,
} from '@/types'

export const usePluginStore = defineStore('plugins', () => {
  const availablePlugins = ref<PluginMeta[]>([])
  const instances = ref<PluginInstance[]>([])
  const packages = ref<PluginPackage[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const uploading = ref(false)
  const uploadProgress = ref(0)

  async function fetchAvailablePlugins(): Promise<void> {
    try {
      const { data } = await api.get<PluginMeta[]>('/plugins/available')
      availablePlugins.value = data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch available plugins'
    }
  }

  async function fetchInstances(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<PluginInstance>>('/plugins', {
        params: { page, page_size: pageSize },
      })
      instances.value = data.data
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch plugin instances'
    } finally {
      loading.value = false
    }
  }

  async function getInstance(publicId: string): Promise<PluginInstance> {
    const { data } = await api.get<PluginInstance>(`/plugins/${publicId}`)
    return data
  }

  async function createInstance(payload: PluginInstanceCreatePayload): Promise<void> {
    await api.post('/plugins', payload)
    await fetchInstances()
  }

  async function updateInstance(publicId: string, payload: PluginInstanceUpdatePayload): Promise<void> {
    await api.put(`/plugins/${publicId}`, payload)
    await fetchInstances()
  }

  async function deleteInstance(publicId: string): Promise<void> {
    const backup = [...instances.value]
    instances.value = instances.value.filter((i) => i.public_id !== publicId)
    try {
      await api.delete(`/plugins/${publicId}`)
    } catch {
      instances.value = backup
      throw new Error('Failed to delete plugin instance')
    }
  }

  async function fetchChannels(instancePublicId: string): Promise<ChannelMapping[]> {
    const { data } = await api.get<ChannelMapping[]>(`/plugins/${instancePublicId}/channels`)
    return data
  }

  async function updateChannelMapping(
    instancePublicId: string,
    mappingPublicId: string,
    payload: ChannelMappingUpdatePayload,
  ): Promise<void> {
    await api.put(`/plugins/${instancePublicId}/channels/${mappingPublicId}`, payload)
  }

  // ── Plugin packages ─────────────────────────────────────────────────

  async function fetchPackages(): Promise<void> {
    try {
      const { data } = await api.get<PluginPackage[]>('/plugins/packages')
      packages.value = data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch packages'
    }
  }

  async function uploadPackage(file: File): Promise<void> {
    uploading.value = true
    uploadProgress.value = 0
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.post('/plugins/packages/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) uploadProgress.value = Math.round((e.loaded * 100) / e.total)
        },
      })
      uploadProgress.value = 100
      await fetchPackages()
      await fetchAvailablePlugins()
    } finally {
      uploading.value = false
    }
  }

  async function uninstallPackage(publicId: string): Promise<void> {
    await api.delete(`/plugins/packages/${publicId}`)
    await fetchPackages()
    await fetchAvailablePlugins()
  }

  return {
    availablePlugins,
    instances,
    packages,
    total,
    loading,
    error,
    uploading,
    uploadProgress,
    fetchAvailablePlugins,
    fetchInstances,
    getInstance,
    createInstance,
    updateInstance,
    deleteInstance,
    fetchChannels,
    updateChannelMapping,
    fetchPackages,
    uploadPackage,
    uninstallPackage,
  }
})
