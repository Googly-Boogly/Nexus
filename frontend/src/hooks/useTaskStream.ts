import { useEffect, useRef, useState, useCallback } from 'react'
import type { TaskEvent, RagSource } from '../types'

interface UseTaskStreamReturn {
  events: TaskEvent[]
  ragSources: RagSource[]
  connected: boolean
  disconnect: () => void
}

export function useTaskStream(taskId: string | null): UseTaskStreamReturn {
  const [events, setEvents] = useState<TaskEvent[]>([])
  const [ragSources, setRagSources] = useState<RagSource[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const shouldReconnect = useRef(true)

  const disconnect = useCallback(() => {
    shouldReconnect.current = false
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    wsRef.current?.close()
    setConnected(false)
  }, [])

  useEffect(() => {
    if (!taskId) return

    shouldReconnect.current = true
    setEvents([])
    setRagSources([])

    const token = localStorage.getItem('access_token')
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${window.location.host}/api/tasks/ws/${taskId}${token ? `?token=${token}` : ''}`

    let retryDelay = 1000

    function connect() {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        retryDelay = 1000
      }

      ws.onmessage = (e) => {
        try {
          const raw = JSON.parse(e.data)
          // Worker publishes {event, data, timestamp}; normalise to {type, data, timestamp}
          const event: TaskEvent = { type: raw.event ?? raw.type ?? 'unknown', data: raw.data ?? {}, timestamp: raw.timestamp ?? '' }
          setEvents((prev) => [...prev, event])

          if (event.type === 'rag_retrieval') {
            const sources = event.data.sources as RagSource[] | undefined
            if (sources) setRagSources(sources)
          }

          if (event.type === 'completed' || event.type === 'failed') {
            shouldReconnect.current = false
            ws.close()
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (shouldReconnect.current) {
          reconnectTimer.current = setTimeout(() => {
            retryDelay = Math.min(retryDelay * 2, 30000)
            connect()
          }, retryDelay)
        }
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      shouldReconnect.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [taskId])

  return { events, ragSources, connected, disconnect }
}
