import { useEffect, useRef, useCallback } from 'react'
import { useRobotStore } from '@/stores/robotStore'

const MAX_RECONNECT_DELAY = 10000 // 10 seconds max
const INITIAL_RECONNECT_DELAY = 1000 // 1 second

export function useSensors() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY)
  const { connected, setUltrasonicDistance, setGripperStatus } = useRobotStore()

  // Use ref for reconnection to avoid circular dependency
  const connectRef = useRef<() => void>(() => {})

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(`ws://${window.location.host}/ws/sensors`)
    wsRef.current = ws

    ws.onopen = () => {
      // Reset reconnect delay on successful connection
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'ultrasonic') {
          setUltrasonicDistance(data.value)
        } else if (data.type === 'gripper') {
          setGripperStatus(data.value)
        } else if (data.type === 'initial') {
          if (data.ultrasonic !== null) {
            setUltrasonicDistance(data.ultrasonic)
          }
          if (data.gripper !== null) {
            setGripperStatus(data.gripper)
          }
        }
        // Ignore ping messages
      } catch (e) {
        console.error('Failed to parse sensor data:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('Sensor WebSocket error:', error)
    }

    ws.onclose = () => {
      wsRef.current = null
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
  }, [setUltrasonicDistance, setGripperStatus])

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
    }
  }, [connected, connect])

  const requestUltrasonic = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'request_ultrasonic' }))
    }
  }

  return { requestUltrasonic }
}
