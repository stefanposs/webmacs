import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import type { Event } from '@/types'

export const useEventStore = defineStore('events', () => {
  const { items: events, total, loading, error, fetch, create, update, remove } =
    useCrudStore<Event>({ endpoint: '/events', name: 'event' })

  return {
    events,
    total,
    loading,
    error,
    fetchEvents: fetch,
    createEvent: create,
    updateEvent: update,
    deleteEvent: remove,
  }
})
