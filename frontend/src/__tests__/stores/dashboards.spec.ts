/**
 * Pinia Dashboard Store – unit tests.
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDashboardStore } from '@/stores/dashboards'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

const SAMPLE_DASHBOARD = {
  public_id: 'dash-1',
  name: 'My Dashboard',
  is_global: false,
  created_on: '2024-06-01T00:00:00Z',
  user_public_id: 'u1',
  widgets: [],
}

describe('Dashboard Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchDashboards() populates state', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: [SAMPLE_DASHBOARD] },
    })

    const store = useDashboardStore()
    await store.fetchDashboards()

    expect(store.dashboards).toHaveLength(1)
    expect(store.dashboards[0].name).toBe('My Dashboard')
    expect(store.total).toBe(1)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchDashboards() sets error on failure', async () => {
    ;(api.get as Mock).mockRejectedValueOnce(new Error('Network error'))

    const store = useDashboardStore()
    await store.fetchDashboards()

    expect(store.error).toBe('Network error')
    expect(store.dashboards).toHaveLength(0)
    expect(store.loading).toBe(false)
  })

  it('createDashboard() posts and adds to list', async () => {
    ;(api.post as Mock).mockResolvedValueOnce({ data: SAMPLE_DASHBOARD })

    const store = useDashboardStore()
    const result = await store.createDashboard({ name: 'My Dashboard', is_global: false })

    expect(api.post).toHaveBeenCalledWith('/dashboards', { name: 'My Dashboard', is_global: false })
    expect(result.public_id).toBe('dash-1')
    expect(store.dashboards).toHaveLength(1)
    expect(store.total).toBe(1)
  })

  it('deleteDashboard() removes from list with optimistic rollback', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: [SAMPLE_DASHBOARD] },
    })

    const store = useDashboardStore()
    await store.fetchDashboards()
    expect(store.dashboards).toHaveLength(1)

    // Successful delete
    ;(api.delete as Mock).mockResolvedValueOnce({})
    await store.deleteDashboard('dash-1')
    expect(store.dashboards).toHaveLength(0)
  })

  it('deleteDashboard() rolls back on failure', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: [SAMPLE_DASHBOARD] },
    })

    const store = useDashboardStore()
    await store.fetchDashboards()

    ;(api.delete as Mock).mockRejectedValueOnce(new Error('Server error'))

    await expect(store.deleteDashboard('dash-1')).rejects.toThrow('Failed to delete dashboard')
    expect(store.dashboards).toHaveLength(1) // rolled back
  })

  it('fetchDashboard() loads single dashboard', async () => {
    ;(api.get as Mock).mockResolvedValueOnce({ data: SAMPLE_DASHBOARD })

    const store = useDashboardStore()
    await store.fetchDashboard('dash-1')

    expect(store.currentDashboard).toBeTruthy()
    expect(store.currentDashboard?.name).toBe('My Dashboard')
  })

  it('addWidget() appends to currentDashboard.widgets', async () => {
    const widget = {
      public_id: 'w-1',
      widget_type: 'line_chart',
      title: 'Temperature',
      event_public_id: 'evt-1',
      x: 0,
      y: 0,
      w: 6,
      h: 4,
      config_json: null,
    }
    ;(api.get as Mock).mockResolvedValueOnce({ data: { ...SAMPLE_DASHBOARD, widgets: [] } })
    ;(api.post as Mock).mockResolvedValueOnce({ data: widget })

    const store = useDashboardStore()
    await store.fetchDashboard('dash-1')
    const result = await store.addWidget('dash-1', {
      widget_type: 'line_chart',
      title: 'Temperature',
      event_public_id: 'evt-1',
      x: 0,
      y: 0,
      w: 6,
      h: 4,
    })

    expect(result.public_id).toBe('w-1')
    expect(store.currentDashboard?.widgets).toHaveLength(1)
  })

  it('deleteWidget() removes from currentDashboard.widgets', async () => {
    const widget = {
      public_id: 'w-1',
      widget_type: 'stat_card',
      title: 'Stat',
      event_public_id: null,
      x: 0,
      y: 0,
      w: 3,
      h: 2,
      config_json: null,
    }
    ;(api.get as Mock).mockResolvedValueOnce({ data: { ...SAMPLE_DASHBOARD, widgets: [widget] } })
    ;(api.delete as Mock).mockResolvedValueOnce({})

    const store = useDashboardStore()
    await store.fetchDashboard('dash-1')
    expect(store.currentDashboard?.widgets).toHaveLength(1)

    await store.deleteWidget('dash-1', 'w-1')
    expect(store.currentDashboard?.widgets).toHaveLength(0)
  })

  // ── updateWidget ──────────────────────────────────────────────────────

  it('updateWidget() calls PUT and updates local widget state', async () => {
    const widget = {
      public_id: 'w-1',
      widget_type: 'line_chart',
      title: 'Original',
      event_public_id: 'evt-1',
      x: 0,
      y: 0,
      w: 6,
      h: 4,
      config_json: null,
    }
    ;(api.get as Mock).mockResolvedValueOnce({ data: { ...SAMPLE_DASHBOARD, widgets: [widget] } })
    ;(api.put as Mock).mockResolvedValueOnce({ data: { status: 'success' } })

    const store = useDashboardStore()
    await store.fetchDashboard('dash-1')

    await store.updateWidget('dash-1', 'w-1', { title: 'Updated', w: 8 })

    expect(api.put).toHaveBeenCalledWith('/dashboards/dash-1/widgets/w-1', {
      title: 'Updated',
      w: 8,
    })
    // Local state should reflect the change immediately
    expect(store.currentDashboard?.widgets[0].title).toBe('Updated')
    expect(store.currentDashboard?.widgets[0].w).toBe(8)
    // Unchanged fields preserved
    expect(store.currentDashboard?.widgets[0].h).toBe(4)
    expect(store.currentDashboard?.widgets[0].event_public_id).toBe('evt-1')
  })

  it('updateWidget() propagates API error', async () => {
    const widget = {
      public_id: 'w-1',
      widget_type: 'gauge',
      title: 'Gauge',
      event_public_id: null,
      x: 0,
      y: 0,
      w: 4,
      h: 3,
      config_json: null,
    }
    ;(api.get as Mock).mockResolvedValueOnce({ data: { ...SAMPLE_DASHBOARD, widgets: [widget] } })
    ;(api.put as Mock).mockRejectedValueOnce(new Error('Server error'))

    const store = useDashboardStore()
    await store.fetchDashboard('dash-1')

    await expect(store.updateWidget('dash-1', 'w-1', { title: 'Fail' })).rejects.toThrow(
      'Server error',
    )
    // Local state should NOT have been updated (put throws before Object.assign)
    expect(store.currentDashboard?.widgets[0].title).toBe('Gauge')
  })

  // ── updateDashboard ───────────────────────────────────────────────────

  it('updateDashboard() calls PUT and re-fetches list', async () => {
    const updated = { ...SAMPLE_DASHBOARD, name: 'Renamed' }
    ;(api.put as Mock).mockResolvedValueOnce({ data: { status: 'success' } })
    // updateDashboard calls fetchDashboards() internally
    ;(api.get as Mock).mockResolvedValueOnce({
      data: { page: 1, page_size: 50, total: 1, data: [updated] },
    })

    const store = useDashboardStore()
    await store.updateDashboard('dash-1', { name: 'Renamed' })

    expect(api.put).toHaveBeenCalledWith('/dashboards/dash-1', { name: 'Renamed' })
    // After re-fetch, dashboards list should reflect the update
    expect(store.dashboards).toHaveLength(1)
    expect(store.dashboards[0].name).toBe('Renamed')
  })

  it('updateDashboard() propagates API error', async () => {
    ;(api.put as Mock).mockRejectedValueOnce(new Error('Forbidden'))

    const store = useDashboardStore()
    await expect(store.updateDashboard('dash-1', { name: 'Nope' })).rejects.toThrow('Forbidden')
  })
})
