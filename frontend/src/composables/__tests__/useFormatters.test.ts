/**
 * Tests for useFormatters composable.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useFormatters } from '@/composables/useFormatters'

describe('useFormatters', () => {
  const { formatDate, formatRelativeTime, formatNumber } = useFormatters()

  describe('formatDate', () => {
    it('returns dash for null', () => {
      expect(formatDate(null)).toBe('—')
    })

    it('returns dash for undefined', () => {
      expect(formatDate(undefined)).toBe('—')
    })

    it('returns dash for empty string', () => {
      expect(formatDate('')).toBe('—')
    })

    it('formats a valid ISO date string', () => {
      const result = formatDate('2025-06-15T10:30:00Z')
      expect(result).toBeTruthy()
      expect(result).not.toBe('—')
    })
  })

  describe('formatRelativeTime', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2025-06-15T12:00:00Z'))
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('returns dash for null', () => {
      expect(formatRelativeTime(null)).toBe('—')
    })

    it('returns seconds ago for recent timestamps', () => {
      const result = formatRelativeTime('2025-06-15T11:59:30Z')
      expect(result).toBe('30s ago')
    })

    it('returns minutes ago', () => {
      const result = formatRelativeTime('2025-06-15T11:55:00Z')
      expect(result).toBe('5m ago')
    })

    it('returns hours ago', () => {
      const result = formatRelativeTime('2025-06-15T09:00:00Z')
      expect(result).toBe('3h ago')
    })

    it('falls back to formatDate for old timestamps', () => {
      const result = formatRelativeTime('2025-06-13T12:00:00Z')
      expect(result).not.toContain('ago')
      expect(result).not.toBe('—')
    })
  })

  describe('formatNumber', () => {
    it('returns dash for null', () => {
      expect(formatNumber(null)).toBe('—')
    })

    it('returns dash for undefined', () => {
      expect(formatNumber(undefined)).toBe('—')
    })

    it('formats a number with default 2 decimals', () => {
      expect(formatNumber(3.14159)).toBe('3.14')
    })

    it('formats a number with custom decimals', () => {
      expect(formatNumber(3.14159, 4)).toBe('3.1416')
    })

    it('handles string numbers', () => {
      expect(formatNumber('42.5')).toBe('42.50')
    })

    it('returns dash for non-numeric string', () => {
      expect(formatNumber('not-a-number')).toBe('—')
    })

    it('formats zero correctly', () => {
      expect(formatNumber(0)).toBe('0.00')
    })
  })
})
