import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import type { Webhook, WebhookCreatePayload, WebhookUpdatePayload } from '@/types'

export const useWebhookStore = defineStore('webhooks', () => {
  const { items: webhooks, total, loading, error, fetch, create, update, remove } =
    useCrudStore<Webhook>({ endpoint: '/webhooks', name: 'webhook' })

  /** Typed wrapper preserving the stricter WebhookCreatePayload contract. */
  async function createWebhook(payload: WebhookCreatePayload): Promise<void> {
    await create(payload)
  }

  /** Typed wrapper preserving the stricter WebhookUpdatePayload contract. */
  async function updateWebhook(publicId: string, payload: WebhookUpdatePayload): Promise<void> {
    await update(publicId, payload)
  }

  return {
    webhooks,
    total,
    loading,
    error,
    fetchWebhooks: fetch,
    createWebhook,
    updateWebhook,
    deleteWebhook: remove,
  }
})
