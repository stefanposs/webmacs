/**
 * Tests for TypeScript type definitions and enum values.
 */
import { describe, it, expect } from 'vitest'
import { EventType, LoggingType } from '@/types'

describe('EventType enum', () => {
  it('has all expected values', () => {
    expect(EventType.sensor).toBe('sensor')
    expect(EventType.actuator).toBe('actuator')
    expect(EventType.range).toBe('range')
    expect(EventType.cmd_button).toBe('cmd_button')
    expect(EventType.cmd_opened).toBe('cmd_opened')
    expect(EventType.cmd_closed).toBe('cmd_closed')
  })

  it('has exactly 6 values', () => {
    expect(Object.keys(EventType)).toHaveLength(6)
  })
})

describe('LoggingType enum', () => {
  it('has all expected values', () => {
    expect(LoggingType.info).toBe('info')
    expect(LoggingType.warning).toBe('warning')
    expect(LoggingType.error).toBe('error')
  })
})
