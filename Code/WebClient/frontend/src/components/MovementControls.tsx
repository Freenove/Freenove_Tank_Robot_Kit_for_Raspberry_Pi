import { useRef, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useRobotStore } from '@/stores/robotStore'
import { api } from '@/lib/api'
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Square } from 'lucide-react'

const MOTOR_SPEED = 2000

export function MovementControls() {
  const { connected } = useRobotStore()
  const activeRef = useRef(false)

  const sendMotor = useCallback(async (left: number, right: number) => {
    if (!connected) return
    try {
      await api.motor(left, right)
    } catch (e) {
      console.error('Motor error:', e)
    }
  }, [connected])

  const handlePointerDown = (left: number, right: number) => {
    if (!connected) return
    activeRef.current = true
    sendMotor(left, right)
  }

  const handlePointerUp = () => {
    if (activeRef.current) {
      activeRef.current = false
      sendMotor(0, 0)
    }
  }

  const handleStop = async () => {
    try {
      await api.stop()
    } catch (e) {
      console.error('Stop error:', e)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Movement</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-2 w-fit mx-auto">
          {/* Row 1: Forward */}
          <div />
          <Button
            size="lg"
            variant="secondary"
            disabled={!connected}
            onPointerDown={() => handlePointerDown(MOTOR_SPEED, MOTOR_SPEED)}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            className="touch-none"
            aria-label="Forward"
          >
            <ArrowUp className="h-6 w-6" />
          </Button>
          <div />

          {/* Row 2: Left, Stop, Right */}
          <Button
            size="lg"
            variant="secondary"
            disabled={!connected}
            onPointerDown={() => handlePointerDown(-MOTOR_SPEED, MOTOR_SPEED)}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            className="touch-none"
            aria-label="Turn Left"
          >
            <ArrowLeft className="h-6 w-6" />
          </Button>
          <Button
            size="lg"
            variant="destructive"
            disabled={!connected}
            onClick={handleStop}
            aria-label="Stop"
          >
            <Square className="h-6 w-6" />
          </Button>
          <Button
            size="lg"
            variant="secondary"
            disabled={!connected}
            onPointerDown={() => handlePointerDown(MOTOR_SPEED, -MOTOR_SPEED)}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            className="touch-none"
            aria-label="Turn Right"
          >
            <ArrowRight className="h-6 w-6" />
          </Button>

          {/* Row 3: Backward */}
          <div />
          <Button
            size="lg"
            variant="secondary"
            disabled={!connected}
            onPointerDown={() => handlePointerDown(-MOTOR_SPEED, -MOTOR_SPEED)}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            className="touch-none"
            aria-label="Backward"
          >
            <ArrowDown className="h-6 w-6" />
          </Button>
          <div />
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Use WASD or Arrow keys
        </p>
      </CardContent>
    </Card>
  )
}
