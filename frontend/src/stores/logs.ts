import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import { useNotification } from '@/composables/useNotification'
import type { LogEntry, LoggingType, PaginatedResponse } from '@/types'

export interface LogFilters {
  logging_type: LoggingType | ''
  search: string
  from_date: string
  to_date: string
}

export const useLogStore = defineStore('logs', () => {
  const logs = ref<LogEntry[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(50)
  const loading = ref(false)
  const exporting = ref(false)
  const error = ref<string | null>(null)

  const filters = ref<LogFilters>({
    logging_type: '',
    search: '',
    from_date: '',
    to_date: '',
  })

  const notify = useNotification()

  function buildParams() {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: pageSize.value,
    }

    if (filters.value.logging_type) params.logging_type = filters.value.logging_type
    if (filters.value.search.trim()) params.search = filters.value.search.trim()
    if (filters.value.from_date) params.from_date = filters.value.from_date
    if (filters.value.to_date) params.to_date = filters.value.to_date

    return params
  }

  async function fetchLogs(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<LogEntry>>('/logging', {
        params: buildParams(),
      })
      logs.value = data.data
      total.value = data.total
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to fetch logs'
      error.value = msg
      notify.error('Fetch failed', msg)
    } finally {
      loading.value = false
    }
  }

  async function exportCsv(): Promise<void> {
    exporting.value = true
    try {
      const token = localStorage.getItem('access_token')
      const params = new URLSearchParams()
      if (filters.value.logging_type) params.set('logging_type', filters.value.logging_type)
      if (filters.value.search.trim()) params.set('search', filters.value.search.trim())
      if (filters.value.from_date) params.set('from_date', filters.value.from_date)
      if (filters.value.to_date) params.set('to_date', filters.value.to_date)

      const query = params.toString()
      const response = await fetch(`/api/v1/logging/export/csv${query ? `?${query}` : ''}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (!response.ok) throw new Error('CSV export failed')

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `logs_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`
      a.click()
      URL.revokeObjectURL(url)

      notify.success('CSV exported', 'Log entries were downloaded.')
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to export logs'
      notify.error('Export failed', msg)
      throw e
    } finally {
      exporting.value = false
    }
  }

  function setPage(next: number): void {
    page.value = Math.max(1, next)
  }

  function setFilters(next: Partial<LogFilters>): void {
    filters.value = { ...filters.value, ...next }
  }

  function resetFilters(): void {
    filters.value = {
      logging_type: '',
      search: '',
      from_date: '',
      to_date: '',
    }
    page.value = 1
  }

  return {
    logs,
    total,
    page,
    pageSize,
    loading,
    exporting,
    error,
    filters,
    fetchLogs,
    exportCsv,
    setPage,
    setFilters,
    resetFilters,
  }
})