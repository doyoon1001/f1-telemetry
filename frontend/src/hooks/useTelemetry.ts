import { useEffect, useState, useRef, useCallback } from 'react'
import type { DriverTelemetry } from '../types/telemetry'

interface TelemetryMessage {
  type: 'telemetry' | 'connected' | 'session' | 'drivers'
  data?: DriverTelemetry
  message?: string
}

export function useTelemetry(url = '/ws/telemetry') {
  const [telemetry, setTelemetry] = useState<DriverTelemetry | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const msg: TelemetryMessage = JSON.parse(event.data)
          if (msg.type === 'telemetry' && msg.data) {
            setTelemetry(msg.data)
          }
        } catch {
          // ignore
        }
      }

      ws.onerror = () => {
        setError('WebSocket error')
      }

      ws.onclose = () => {
        setConnected(false)
        // auto reconnect
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect()
        }, 3000)
      }
    } catch (e) {
      setError('Failed to connect')
    }
  }, [url])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    wsRef.current?.close()
    wsRef.current = null
    setConnected(false)
  }, [])

  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { telemetry, connected, error, connect, disconnect, send }
}
