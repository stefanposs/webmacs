import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type {
  Dashboard,
  DashboardCreatePayload,
  DashboardWidget,
  DashboardWidgetCreatePayload,
  PaginatedResponse,
} from '@/types'

export const useDashboardStore = defineStore('dashboards', () => {
  const dashboards = ref<Dashboard[]>([])
  const currentDashboard = ref<Dashboard | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchDashboards(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<Dashboard>>('/dashboards', {
        params: { page, page_size: pageSize },
      })
      dashboards.value = data.data
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch dashboards'
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboard(publicId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<Dashboard>(`/dashboards/${publicId}`)
      currentDashboard.value = data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch dashboard'
    } finally {
      loading.value = false
    }
  }

  async function createDashboard(payload: DashboardCreatePayload): Promise<Dashboard> {
    const { data } = await api.post<Dashboard>('/dashboards', payload)
    dashboards.value.unshift(data)
    total.value += 1
    return data
  }

  async function updateDashboard(
    publicId: string,
    payload: { name?: string; is_global?: boolean },
  ): Promise<void> {
    await api.put(`/dashboards/${publicId}`, payload)
    await fetchDashboards()
  }

  async function deleteDashboard(publicId: string): Promise<void> {
    const backup = [...dashboards.value]
    dashboards.value = dashboards.value.filter((d) => d.public_id !== publicId)
    try {
      await api.delete(`/dashboards/${publicId}`)
      total.value -= 1
    } catch {
      dashboards.value = backup
      throw new Error('Failed to delete dashboard')
    }
  }

  // Widget operations
  async function addWidget(
    dashboardId: string,
    payload: DashboardWidgetCreatePayload,
  ): Promise<DashboardWidget> {
    const { data } = await api.post<DashboardWidget>(
      `/dashboards/${dashboardId}/widgets`,
      payload,
    )
    if (currentDashboard.value?.public_id === dashboardId) {
      currentDashboard.value.widgets.push(data)
    }
    return data
  }

  async function updateWidget(
    dashboardId: string,
    widgetId: string,
    payload: Partial<DashboardWidgetCreatePayload>,
  ): Promise<void> {
    await api.put(`/dashboards/${dashboardId}/widgets/${widgetId}`, payload)
  }

  async function deleteWidget(dashboardId: string, widgetId: string): Promise<void> {
    await api.delete(`/dashboards/${dashboardId}/widgets/${widgetId}`)
    if (currentDashboard.value?.public_id === dashboardId) {
      currentDashboard.value.widgets = currentDashboard.value.widgets.filter(
        (w) => w.public_id !== widgetId,
      )
    }
  }

  return {
    dashboards,
    currentDashboard,
    total,
    loading,
    error,
    fetchDashboards,
    fetchDashboard,
    createDashboard,
    updateDashboard,
    deleteDashboard,
    addWidget,
    updateWidget,
    deleteWidget,
  }
})
