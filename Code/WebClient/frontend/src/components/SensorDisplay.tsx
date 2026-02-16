import { useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useRobotStore } from '@/stores/robotStore'
import { useSensors } from '@/hooks/useSensors'
import { Radar, RefreshCw, Hand } from 'lucide-react'

export function SensorDisplay() {
  const { connected, ultrasonicDistance, gripperStatus } = useRobotStore()
  const { requestUltrasonic } = useSensors()

  // Request ultrasonic reading periodically when connected
  useEffect(() => {
    if (!connected) return

    const interval = setInterval(() => {
      requestUltrasonic()
    }, 1000)

    return () => clearInterval(interval)
  }, [connected, requestUltrasonic])

  const getDistanceColor = () => {
    if (ultrasonicDistance === null) return 'secondary'
    if (ultrasonicDistance < 20) return 'destructive'
    if (ultrasonicDistance < 50) return 'default'
    return 'success'
  }

  const getGripperColor = () => {
    if (!gripperStatus) return 'secondary'
    if (gripperStatus === 'up_complete') return 'success'
    if (gripperStatus === 'down_complete') return 'default'
    return 'secondary' // stopped
  }

  const formatGripperStatus = () => {
    if (!gripperStatus) return 'N/A'
    if (gripperStatus === 'up_complete') return 'Closed'
    if (gripperStatus === 'down_complete') return 'Open'
    return 'Stopped'
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Radar className="h-5 w-5" />
          Sensors
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm">Ultrasonic</span>
          <div className="flex items-center gap-2">
            <Badge variant={getDistanceColor()}>
              {ultrasonicDistance !== null
                ? `${ultrasonicDistance.toFixed(1)} cm`
                : 'N/A'}
            </Badge>
            <Button
              size="icon"
              variant="ghost"
              className="h-6 w-6"
              disabled={!connected}
              onClick={requestUltrasonic}
            >
              <RefreshCw className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {ultrasonicDistance !== null && ultrasonicDistance < 20 && (
          <p className="text-xs text-destructive">Warning: Obstacle nearby!</p>
        )}

        {/* Gripper Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm flex items-center gap-1">
            <Hand className="h-3 w-3" />
            Gripper
          </span>
          <Badge variant={getGripperColor()}>
            {formatGripperStatus()}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}
