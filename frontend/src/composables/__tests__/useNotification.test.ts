/**
 * Tests for useNotification composable.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useNotification, useNotifications } from '@/composables/useNotification'

describe('useNotification', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // Clear existing notifications
    const { notifications } = useNotifications()
    notifications.value = []
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('adds a success notification', () => {
    const { success } = useNotification()
    success('Done!')

    const { notifications } = useNotifications()
    expect(notifications.value).toHaveLength(1)
    expect(notifications.value[0].severity).toBe('success')
    expect(notifications.value[0].summary).toBe('Done!')
  })

  it('adds an error notification with longer life', () => {
    const { error } = useNotification()
    error('Failed!', 'Something went wrong')

    const { notifications } = useNotifications()
    expect(notifications.value).toHaveLength(1)
    expect(notifications.value[0].severity).toBe('error')
    expect(notifications.value[0].detail).toBe('Something went wrong')
    expect(notifications.value[0].life).toBe(5000)
  })

  it('auto-removes notifications after life expires', () => {
    const { info } = useNotification()
    info('Temporary')

    const { notifications } = useNotifications()
    expect(notifications.value).toHaveLength(1)

    vi.advanceTimersByTime(4000) // Default life is 3500ms
    expect(notifications.value).toHaveLength(0)
  })

  it('supports all severity levels', () => {
    const { success, info, warn, error } = useNotification()
    success('s')
    info('i')
    warn('w')
    error('e')

    const { notifications } = useNotifications()
    expect(notifications.value).toHaveLength(4)

    const severities = notifications.value.map((n) => n.severity)
    expect(severities).toEqual(['success', 'info', 'warn', 'error'])
  })

  it('manually removes a notification', () => {
    const { info } = useNotification()
    info('Will be removed')

    const { notifications, remove } = useNotifications()
    expect(notifications.value).toHaveLength(1)

    remove(notifications.value[0].id)
    expect(notifications.value).toHaveLength(0)
  })
})
