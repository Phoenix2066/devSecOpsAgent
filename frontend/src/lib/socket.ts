// WebSocket client — connects to Go backend WS endpoint
// One connection per pipeline page — disconnects on page unmount
import { useEffect, useRef } from "react"
import { WSMessage, WSEventType } from "./types"

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8080"

export class PipelineSocket {
  private ws: WebSocket | null = null
  private pipelineId: string
  private handlers: Map<WSEventType, ((data: any) => void)[]> = new Map()
  private reconnectAttempts = 0
  private maxReconnects = 5

  constructor(pipelineId: string) {
    this.pipelineId = pipelineId
  }

  connect(): void {
    if (this.ws) return
    
    const url = `${WS_BASE}/ws/pipeline/${this.pipelineId}`
    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        const handlers = this.handlers.get(msg.event)
        if (handlers) {
          handlers.forEach(h => h(msg.data))
        }
      } catch (e) {
        console.error("Failed to parse WS message", e)
      }
    }

    this.ws.onclose = () => {
      this.ws = null
      if (this.reconnectAttempts < this.maxReconnects) {
        const delay = Math.pow(2, this.reconnectAttempts) * 1000
        setTimeout(() => {
          this.reconnectAttempts++
          this.connect()
        }, delay)
      }
    }

    this.ws.onerror = (error) => {
      console.error("WebSocket error", error)
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      console.log("WebSocket connected", this.pipelineId)
    }
  }

  on(event: WSEventType, handler: (data: any) => void): void {
    const list = this.handlers.get(event) ?? []
    list.push(handler)
    this.handlers.set(event, list)
  }

  off(event: WSEventType, handler: (data: any) => void): void {
    const list = this.handlers.get(event) ?? []
    this.handlers.set(event, list.filter(h => h !== handler))
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.handlers.clear()
    this.reconnectAttempts = 0
  }
}

// React hook wrapping PipelineSocket
export function usePipelineSocket(pipelineId: string) {
  const socketRef = useRef<PipelineSocket | null>(null)

  useEffect(() => {
    if (!pipelineId) return

    const socket = new PipelineSocket(pipelineId)
    socket.connect()
    socketRef.current = socket

    return () => {
      socket.disconnect()
      socketRef.current = null
    }
  }, [pipelineId])

  return {
    on: (event: WSEventType, handler: (data: any) => void) => {
      if (socketRef.current) socketRef.current.on(event, handler);
    },
    off: (event: WSEventType, handler: (data: any) => void) => {
      if (socketRef.current) socketRef.current.off(event, handler);
    }
  }
}
