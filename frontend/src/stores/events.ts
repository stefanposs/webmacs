import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { Event, PaginatedResponse } from '@/types'

export const useEventStore = defineStore('events', () => {
  const events = ref<Event[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchEvents(page = 1, pageSize = 50): Promise<void> {
    loading.value = true
    try {
      const { data } = await api.get<PaginatedResponse<Event>>('/events/', {
        params: { page, page_size: pageSize },
      })
      events.value = data.data
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function createEvent(payload: Partial<Event>): Promise<void> {
    await api.post('/events/', payload)
    await fetchEvents()
  }

  async function updateEvent(publicId: string, payload: Partial<Event>): Promise<void> {
    await api.put(`/events/${publicId}`, payload)
    await fetchEvents()
  }

  async function deleteEvent(publicId: string): Promise<void> {
    await api.delete(`/events/${publicId}`)
    events.value = events.value.filter((e) => e.public_id !== publicId)
  }

  return { events, total, loading, fetchEvents, createEvent, updateEvent, deleteEvent }
})
