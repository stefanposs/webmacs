import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { Rule, PaginatedResponse } from '@/types'

export const useRuleStore = defineStore('rules', () => {
  const rules = ref<Rule[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchRules(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<Rule>>('/rules', {
        params: { page, page_size: pageSize },
      })
      rules.value = data.data
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch rules'
    } finally {
      loading.value = false
    }
  }

  async function createRule(payload: Partial<Rule>): Promise<void> {
    await api.post('/rules', payload)
    await fetchRules()
  }

  async function updateRule(publicId: string, payload: Partial<Rule>): Promise<void> {
    await api.put(`/rules/${publicId}`, payload)
    await fetchRules()
  }

  async function deleteRule(publicId: string): Promise<void> {
    const backup = [...rules.value]
    rules.value = rules.value.filter((r) => r.public_id !== publicId)
    try {
      await api.delete(`/rules/${publicId}`)
    } catch {
      rules.value = backup
      throw new Error('Failed to delete rule')
    }
  }

  return { rules, total, loading, error, fetchRules, createRule, updateRule, deleteRule }
})
