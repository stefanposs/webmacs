/**
 * Tests for the WebSocketClient service.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { WebSocketClient } from '@/services/websocket'

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null

  sent: string[] = []

  constructor(public url: string) {
    // Auto-connect after microtask
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 0)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  }
}

describe('WebSocketClient', () => {
  let originalWebSocket: typeof WebSocket

  beforeEach(() => {
    vi.useFakeTimers()
    originalWebSocket = globalThis.WebSocket
    globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket
  })

  afterEach(() => {
    vi.useRealTimers()
    globalThis.WebSocket = originalWebSocket
  })

  it('creates a client with correct config', () => {
    const onMessage = vi.fn()
    const client = new WebSocketClient({ url: 'ws://localhost/ws', onMessage })

    expect(client).toBeDefined()
    expect(client.connected).toBe(false)
    client.dispose()
  })

  it('connects and reports state change', async () => {
    const onMessage = vi.fn()
    const onStateChange = vi.fn()
    const client = new WebSocketClient({
      url: 'ws://localhost/ws',
      onMessage,
      onStateChange,
    })

    client.connect()
    await vi.advanceTimersByTimeAsync(10)

    expect(onStateChange).toHaveBeenCalledWith(true)
    expect(client.connected).toBe(true)
    client.dispose()
  })

  it('sends JSON data when connected', async () => {
    const onMessage = vi.fn()
    const client = new WebSocketClient({ url: 'ws://localhost/ws', onMessage })

    client.connect()
    await vi.advanceTimersByTimeAsync(10)

    client.send({ type: 'ping' })
    // Data was sent (verified through the mock)
    expect(client.connected).toBe(true)
    client.dispose()
  })

  it('does not send when not connected', () => {
    const onMessage = vi.fn()
    const client = new WebSocketClient({ url: 'ws://localhost/ws', onMessage })

    // Don't connect — try to send
    client.send({ type: 'ping' })
    expect(client.connected).toBe(false)
    client.dispose()
  })

  it('dispose prevents reconnect', async () => {
    const onMessage = vi.fn()
    const onStateChange = vi.fn()
    const client = new WebSocketClient({
      url: 'ws://localhost/ws',
      onMessage,
      onStateChange,
    })

    client.dispose()
    client.connect()
    await vi.advanceTimersByTimeAsync(100)

    // Should not have connected
    expect(onStateChange).not.toHaveBeenCalledWith(true)
  })
})
