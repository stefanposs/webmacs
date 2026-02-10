/**
 * WebSocket client service — generic reconnecting WebSocket wrapper.
 *
 * Features:
 * - Auto-reconnect with exponential back-off
 * - Ping/pong keep-alive
 * - Connection state tracking
 * - Clean close on dispose
 */

export type WSMessageHandler = (data: unknown) => void
export type WSStateHandler = (connected: boolean) => void

export interface WebSocketClientOptions {
  /** Full WebSocket URL (e.g. ws://localhost:8000/ws/datapoints/stream) */
  url: string
  /** Called for every incoming JSON message */
  onMessage: WSMessageHandler
  /** Called when connection state changes */
  onStateChange?: WSStateHandler
  /** Initial reconnect delay in ms (default: 1000) */
  reconnectDelay?: number
  /** Max reconnect delay in ms (default: 30000) */
  maxReconnectDelay?: number
  /** Ping interval in ms (default: 25000) */
  pingInterval?: number
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private currentDelay: number
  private disposed = false

  private readonly url: string
  private readonly onMessage: WSMessageHandler
  private readonly onStateChange: WSStateHandler
  private readonly reconnectDelay: number
  private readonly maxReconnectDelay: number
  private readonly pingInterval: number

  constructor(options: WebSocketClientOptions) {
    this.url = options.url
    this.onMessage = options.onMessage
    this.onStateChange = options.onStateChange ?? (() => {})
    this.reconnectDelay = options.reconnectDelay ?? 1000
    this.maxReconnectDelay = options.maxReconnectDelay ?? 30000
    this.pingInterval = options.pingInterval ?? 25000
    this.currentDelay = this.reconnectDelay
  }

  /** Establish connection */
  connect(): void {
    if (this.disposed) return
    this.cleanup()

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = this.url.startsWith('ws') ? this.url : `${protocol}//${window.location.host}${this.url}`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.currentDelay = this.reconnectDelay
        this.onStateChange(true)
        this.startPing()
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type !== 'pong') {
            this.onMessage(data)
          }
        } catch {
          // Ignore non-JSON messages
        }
      }

      this.ws.onclose = () => {
        this.onStateChange(false)
        this.stopPing()
        this.scheduleReconnect()
      }

      this.ws.onerror = () => {
        // onclose will fire after onerror
      }
    } catch {
      this.scheduleReconnect()
    }
  }

  /** Clean close */
  dispose(): void {
    this.disposed = true
    this.cleanup()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /** Send JSON message */
  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  private cleanup(): void {
    this.stopPing()
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close()
      }
      this.ws = null
    }
  }

  private startPing(): void {
    this.stopPing()
    this.pingTimer = setInterval(() => {
      this.send({ type: 'ping' })
    }, this.pingInterval)
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  private scheduleReconnect(): void {
    if (this.disposed) return
    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, this.currentDelay)
    this.currentDelay = Math.min(this.currentDelay * 2, this.maxReconnectDelay)
  }
}
