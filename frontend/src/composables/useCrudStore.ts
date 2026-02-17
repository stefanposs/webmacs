/**
 * Generic CRUD store factory composable.
 *
 * Eliminates boilerplate across resource stores (events, webhooks, rules,
 * experiments, etc.) by encapsulating the shared paginated-fetch / create /
 * update / optimistic-delete pattern.
 *
 * Usage:
 *   const { items, total, loading, error, fetch, create, update, remove } =
 *     useCrudStore<Event>({ endpoint: '/events', name: 'events' })
 */

import { ref, type Ref } from 'vue'
import api from '@/services/api'
import { useNotification } from '@/composables/useNotification'
import type { PaginatedResponse } from '@/types'

/** Per-resource configuration passed to the factory. */
export interface CrudStoreOptions<T> {
  /** REST endpoint path, e.g. '/events' */
  endpoint: string

  /** Human-readable singular name used in notifications, e.g. 'event' */
  name: string

  /** Default page size sent to the backend (default: 50) */
  pageSize?: number

  /**
   * Property on each item used as the unique identifier.
   * Defaults to 'public_id'.
   */
  idKey?: keyof T & string

  /**
   * Optional transform applied to each item after it is received from the
   * backend.  Useful for date parsing, computed fields, etc.
   */
  parseItem?: (raw: unknown) => T
}

/** Return type of useCrudStore — fully typed reactive state + actions. */
export interface CrudStore<T> {
  /** Reactive list of items for the current page. */
  items: Ref<T[]>

  /** Total number of items reported by the backend. */
  total: Ref<number>

  /** Whether a fetch request is currently in flight. */
  loading: Ref<boolean>

  /** Latest error message, or null. */
  error: Ref<string | null>

  /** Fetch a page of items from the backend. */
  fetch: (page?: number, pageSize?: number, showLoading?: boolean) => Promise<void>

  /** Create a new item and re-fetch the list. */
  create: (payload: Partial<T> | Record<string, unknown>) => Promise<void>

  /** Update an existing item by id and re-fetch the list. */
  update: (id: string, payload: Partial<T> | Record<string, unknown>) => Promise<void>

  /** Optimistically remove an item; rolls back on failure. */
  remove: (id: string) => Promise<void>
}

/**
 * Factory that produces a fully-typed CRUD composable for any resource.
 *
 * ```ts
 * // inside a Pinia defineStore setup function:
 * const crud = useCrudStore<Event>({ endpoint: '/events', name: 'event' })
 * ```
 */
export function useCrudStore<T>(
  options: CrudStoreOptions<T>,
): CrudStore<T> {
  const {
    endpoint,
    name,
    pageSize: defaultPageSize = 50,
    idKey = 'public_id' as keyof T & string,
    parseItem,
  } = options

  const notify = useNotification()

  // ── Reactive state ──────────────────────────────────────────────────────
  const items = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ── Actions ─────────────────────────────────────────────────────────────

  async function fetch(
    page = 1,
    pageSize: number = defaultPageSize,
    showLoading = true,
  ): Promise<void> {
    if (showLoading) loading.value = true
    error.value = null
    try {
      const { data } = await api.get<PaginatedResponse<T>>(endpoint, {
        params: { page, page_size: pageSize },
      })

      items.value = parseItem ? data.data.map((raw) => parseItem(raw)) : data.data
      total.value = data.total
    } catch (e) {
      const msg = e instanceof Error ? e.message : `Failed to fetch ${name}s`
      error.value = msg
      notify.error(`Fetch failed`, msg)
    } finally {
      if (showLoading) loading.value = false
    }
  }

  async function create(payload: Partial<T> | Record<string, unknown>): Promise<void> {
    try {
      await api.post(endpoint, payload)
      notify.success(`${capitalize(name)} created`)
      await fetch(1, defaultPageSize, false)
    } catch (e) {
      const msg = e instanceof Error ? e.message : `Failed to create ${name}`
      notify.error(`Create failed`, msg)
      throw e
    }
  }

  async function update(
    id: string,
    payload: Partial<T> | Record<string, unknown>,
  ): Promise<void> {
    try {
      await api.put(`${endpoint}/${id}`, payload)
      notify.success(`${capitalize(name)} updated`)
      await fetch(1, defaultPageSize, false)
    } catch (e) {
      const msg = e instanceof Error ? e.message : `Failed to update ${name}`
      notify.error(`Update failed`, msg)
      throw e
    }
  }

  async function remove(id: string): Promise<void> {
    // Optimistic delete — remove from local list immediately
    const backup = [...items.value]
    items.value = items.value.filter(
      (item) => String((item as Record<string, unknown>)[idKey]) !== id,
    )

    try {
      await api.delete(`${endpoint}/${id}`)
      total.value = Math.max(0, total.value - 1)
      notify.success(`${capitalize(name)} deleted`)
    } catch {
      // Roll back on failure
      items.value = backup
      notify.error(`Delete failed`, `Failed to delete ${name}`)
      throw new Error(`Failed to delete ${name}`)
    }
  }

  return { items, total, loading, error, fetch, create, update, remove }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
