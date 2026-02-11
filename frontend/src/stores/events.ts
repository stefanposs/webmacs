import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { Event, PaginatedResponse } from '@/types'

export const useEventStore = defineStore('events', () => {
  const events = ref<Event[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchEvents(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<Event>>('/events', {
        params: { page, page_size: pageSize },
      })
      events.value = data.data
      total.value = data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch events'
    } finally {
      loading.value = false
    }
  }

  async function createEvent(payload: Partial<Event>): Promise<void> {
    await api.post('/events', payload)
    await fetchEvents()
  }

  async function updateEvent(publicId: string, payload: Partial<Event>): Promise<void> {
    await api.put(`/events/${publicId}`, payload)
    await fetchEvents()
  }

  async function deleteEvent(publicId: string): Promise<void> {
    const backup = [...events.value]
    events.value = events.value.filter((e) => e.public_id !== publicId)
    try {
      await api.delete(`/events/${publicId}`)
    } catch {
      events.value = backup
      throw new Error('Failed to delete event')
    }
  }

  return { events, total, loading, error, fetchEvents, createEvent, updateEvent, deleteEvent }
})
