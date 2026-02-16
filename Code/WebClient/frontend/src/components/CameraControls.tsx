import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Label } from '@/components/ui/label'
import { useRobotStore } from '@/stores/robotStore'
import { api } from '@/lib/api'
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Home } from 'lucide-react'

export function CameraControls() {
  const { connected, servo1Angle, servo2Angle, setServo1Angle, setServo2Angle } = useRobotStore()

  const handlePan = async (value: number[]) => {
    const angle = value[0]
    setServo1Angle(angle)
    if (connected) {
      try {
        await api.servo(0, angle)
      } catch (e) {
        console.error('Servo error:', e)
      }
    }
  }

  const handleTilt = async (value: number[]) => {
    const angle = value[0]
    setServo2Angle(angle)
    if (connected) {
      try {
        await api.servo(1, angle)
      } catch (e) {
        console.error('Servo error:', e)
      }
    }
  }

  const handleHome = async () => {
    setServo1Angle(90)
    setServo2Angle(140)
    if (connected) {
      try {
        await api.servo(0, 90)
        await api.servo(1, 140)
      } catch (e) {
        console.error('Servo error:', e)
      }
    }
  }

  const adjust = async (channel: number, delta: number) => {
    if (!connected) return
    const current = channel === 0 ? servo1Angle : servo2Angle
    const newAngle = Math.max(90, Math.min(150, current + delta))
    if (channel === 0) {
      setServo1Angle(newAngle)
    } else {
      setServo2Angle(newAngle)
    }
    try {
      await api.servo(channel, newAngle)
    } catch (e) {
      console.error('Servo error:', e)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Camera</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Pan (horizontal) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Pan</Label>
            <span className="text-sm text-muted-foreground">{servo1Angle}°</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={!connected}
              onClick={() => adjust(0, -5)}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <Slider
              value={[servo1Angle]}
              onValueChange={handlePan}
              min={90}
              max={150}
              step={1}
              disabled={!connected}
              className="flex-1"
            />
            <Button
              size="sm"
              variant="outline"
              disabled={!connected}
              onClick={() => adjust(0, 5)}
            >
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Tilt (vertical) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Tilt</Label>
            <span className="text-sm text-muted-foreground">{servo2Angle}°</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={!connected}
              onClick={() => adjust(1, -5)}
            >
              <ArrowDown className="h-4 w-4" />
            </Button>
            <Slider
              value={[servo2Angle]}
              onValueChange={handleTilt}
              min={90}
              max={150}
              step={1}
              disabled={!connected}
              className="flex-1"
            />
            <Button
              size="sm"
              variant="outline"
              disabled={!connected}
              onClick={() => adjust(1, 5)}
            >
              <ArrowUp className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Home button */}
        <Button
          variant="secondary"
          size="sm"
          className="w-full"
          disabled={!connected}
          onClick={handleHome}
        >
          <Home className="h-4 w-4 mr-2" />
          Home (90°, 140°)
        </Button>

        <p className="text-xs text-muted-foreground text-center">
          Use IJKL keys
        </p>
      </CardContent>
    </Card>
  )
}
