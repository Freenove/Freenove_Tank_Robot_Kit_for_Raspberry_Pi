import { useEffect, useRef } from 'react'
import { api } from '@/lib/api'
import { useRobotStore } from '@/stores/robotStore'

const MOTOR_SPEED = 2000

export function useKeyboardControls() {
  const { connected, servo1Angle, servo2Angle, setServo1Angle, setServo2Angle } = useRobotStore()
  const activeKeysRef = useRef(new Set<string>())
  const motorStateRef = useRef({ left: 0, right: 0 })

  // Use refs to avoid effect re-running on every servo angle change
  const servo1Ref = useRef(servo1Angle)
  const servo2Ref = useRef(servo2Angle)

  // Keep refs in sync with state
  useEffect(() => {
    servo1Ref.current = servo1Angle
  }, [servo1Angle])

  useEffect(() => {
    servo2Ref.current = servo2Angle
  }, [servo2Angle])

  useEffect(() => {
    if (!connected) return

    const updateMotors = () => {
      const keys = activeKeysRef.current
      let left = 0
      let right = 0

      // WASD movement
      if (keys.has('w') || keys.has('arrowup')) {
        left = MOTOR_SPEED
        right = MOTOR_SPEED
      }
      if (keys.has('s') || keys.has('arrowdown')) {
        left = -MOTOR_SPEED
        right = -MOTOR_SPEED
      }
      if (keys.has('a') || keys.has('arrowleft')) {
        left = -MOTOR_SPEED
        right = MOTOR_SPEED
      }
      if (keys.has('d') || keys.has('arrowright')) {
        left = MOTOR_SPEED
        right = -MOTOR_SPEED
      }

      // Only send if changed
      if (left !== motorStateRef.current.left || right !== motorStateRef.current.right) {
        motorStateRef.current = { left, right }
        api.motor(left, right).catch(console.error)
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input
      if ((e.target as HTMLElement).tagName === 'INPUT') return

      const key = e.key.toLowerCase()

      // Camera controls with IJKL (I=up, K=down, J=left, L=right)
      // Use refs for current values to avoid stale closures
      if (key === 'i') {
        const newAngle = Math.min(150, servo2Ref.current + 5)
        servo2Ref.current = newAngle
        setServo2Angle(newAngle)
        api.servo(1, newAngle).catch(console.error)
        return
      }
      if (key === 'k') {
        const newAngle = Math.max(90, servo2Ref.current - 5)
        servo2Ref.current = newAngle
        setServo2Angle(newAngle)
        api.servo(1, newAngle).catch(console.error)
        return
      }
      if (key === 'j') {
        // Left = decrease servo1
        const newAngle = Math.max(90, servo1Ref.current - 5)
        servo1Ref.current = newAngle
        setServo1Angle(newAngle)
        api.servo(0, newAngle).catch(console.error)
        return
      }
      if (key === 'l') {
        // Right = increase servo1
        const newAngle = Math.min(150, servo1Ref.current + 5)
        servo1Ref.current = newAngle
        setServo1Angle(newAngle)
        api.servo(0, newAngle).catch(console.error)
        return
      }

      // Gripper controls O/P
      if (key === 'o') {
        api.gripper(1).catch(console.error) // Pinch/up
        return
      }
      if (key === 'p') {
        api.gripper(2).catch(console.error) // Drop/down
        return
      }

      // Home key resets camera
      if (key === 'home') {
        servo1Ref.current = 90
        servo2Ref.current = 140
        setServo1Angle(90)
        setServo2Angle(140)
        api.servo(0, 90).catch(console.error)
        api.servo(1, 140).catch(console.error)
        return
      }

      // Movement keys
      if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) {
        e.preventDefault()
        activeKeysRef.current.add(key)
        updateMotors()
      }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase()
      activeKeysRef.current.delete(key)
      updateMotors()
    }

    // Stop on focus loss
    const handleBlur = () => {
      activeKeysRef.current.clear()
      motorStateRef.current = { left: 0, right: 0 }
      api.stop().catch(console.error)
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    window.addEventListener('blur', handleBlur)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      window.removeEventListener('blur', handleBlur)
      api.stop().catch(console.error)
    }
  }, [connected, setServo1Angle, setServo2Angle])
}
