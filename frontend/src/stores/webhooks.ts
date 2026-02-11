import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { Webhook, WebhookCreatePayload, WebhookUpdatePayload, PaginatedResponse } from '@/types'

export const useWebhookStore = defineStore('webhooks', () => {
  const webhooks = ref<Webhook[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchWebhooks(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<Webhook>>('/webhooks', {
        params: { page, page_size: pageSize },
      })
      webhooks.value = data.data
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch webhooks'
    } finally {
      loading.value = false
    }
  }

  async function createWebhook(payload: WebhookCreatePayload): Promise<void> {
    await api.post('/webhooks', payload)
    await fetchWebhooks()
  }

  async function updateWebhook(publicId: string, payload: WebhookUpdatePayload): Promise<void> {
    await api.put(`/webhooks/${publicId}`, payload)
    await fetchWebhooks()
  }

  async function deleteWebhook(publicId: string): Promise<void> {
    const backup = [...webhooks.value]
    webhooks.value = webhooks.value.filter((w) => w.public_id !== publicId)
    try {
      await api.delete(`/webhooks/${publicId}`)
    } catch {
      webhooks.value = backup
      throw new Error('Failed to delete webhook')
    }
  }

  return { webhooks, total, loading, error, fetchWebhooks, createWebhook, updateWebhook, deleteWebhook }
})
