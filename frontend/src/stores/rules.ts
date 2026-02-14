import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import type { Rule } from '@/types'

export const useRuleStore = defineStore('rules', () => {
  const { items: rules, total, loading, error, fetch, create, update, remove } =
    useCrudStore<Rule>({ endpoint: '/rules', name: 'rule' })

  return {
    rules,
    total,
    loading,
    error,
    fetchRules: fetch,
    createRule: create,
    updateRule: update,
    deleteRule: remove,
  }
})
