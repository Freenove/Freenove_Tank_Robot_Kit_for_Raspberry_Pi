import { useEffect, useRef, useCallback } from 'react'
import { useRobotStore } from '@/stores/robotStore'

const MAX_RECONNECT_DELAY = 10000 // 10 seconds max
const INITIAL_RECONNECT_DELAY = 1000 // 1 second

export function useVideoStream() {
  const wsRef = useRef<WebSocket | null>(null)
  const prevUrlRef = useRef<string | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY)
  const { connected, setVideoUrl } = useRobotStore()

  const cleanup = useCallback(() => {
    if (prevUrlRef.current) {
      URL.revokeObjectURL(prevUrlRef.current)
      prevUrlRef.current = null
    }
    setVideoUrl(null)
  }, [setVideoUrl])

  // Use ref for reconnection to avoid circular dependency
  const connectRef = useRef<() => void>(() => {})

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(`ws://${window.location.host}/ws/video`)
    ws.binaryType = 'blob'
    wsRef.current = ws

    ws.onopen = () => {
      // Reset reconnect delay on successful connection
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY
    }

    ws.onmessage = (event) => {
      // Revoke previous URL to prevent memory leak
      if (prevUrlRef.current) {
        URL.revokeObjectURL(prevUrlRef.current)
      }
      const url = URL.createObjectURL(event.data)
      prevUrlRef.current = url
      setVideoUrl(url)
    }

    ws.onerror = (error) => {
      console.error('Video WebSocket error:', error)
    }

    ws.onclose = () => {
      wsRef.current = null
      cleanup()
      // Only reconnect if still supposed to be connected
      if (useRobotStore.getState().connected) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(
            reconnectDelayRef.current * 2,
            MAX_RECONNECT_DELAY
          )
          connectRef.current()
        }, reconnectDelayRef.current)
      }
    }
  }, [setVideoUrl, cleanup])

  // Keep ref in sync (must be in useEffect to avoid "cannot update ref during render")
  useEffect(() => {
    connectRef.current = connect
  }, [connect])

  useEffect(() => {
    if (!connected) {
      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      cleanup()
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY
      return
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      cleanup()
    }
  }, [connected, connect, cleanup])

  return { cleanup }
}
