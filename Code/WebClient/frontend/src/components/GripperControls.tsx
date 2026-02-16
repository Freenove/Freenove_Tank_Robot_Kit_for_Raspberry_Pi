import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { useRobotStore } from '@/stores/robotStore'
import { api } from '@/lib/api'
import { Hand } from 'lucide-react'

export function GripperControls() {
  const { connected } = useRobotStore()
  const [pinching, setPinching] = useState(false)
  const [dropping, setDropping] = useState(false)

  const handlePinch = async (checked: boolean) => {
    setPinching(checked)
    if (checked) {
      setDropping(false)
    }

    if (!connected) return

    try {
      if (checked) {
        await api.gripper(1) // up/pinch
      } else if (!dropping) {
        await api.gripper(0) // stop
      }
    } catch (e) {
      console.error('Gripper error:', e)
    }
  }

  const handleDrop = async (checked: boolean) => {
    setDropping(checked)
    if (checked) {
      setPinching(false)
    }

    if (!connected) return

    try {
      if (checked) {
        await api.gripper(2) // down/drop
      } else if (!pinching) {
        await api.gripper(0) // stop
      }
    } catch (e) {
      console.error('Gripper error:', e)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Hand className="h-5 w-5" />
          Gripper
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="pinch"
            checked={pinching}
            onCheckedChange={handlePinch}
            disabled={!connected}
          />
          <Label htmlFor="pinch" className="cursor-pointer">
            Pinch (up)
          </Label>
        </div>
        <div className="flex items-center space-x-2">
          <Checkbox
            id="drop"
            checked={dropping}
            onCheckedChange={handleDrop}
            disabled={!connected}
          />
          <Label htmlFor="drop" className="cursor-pointer">
            Drop (down)
          </Label>
        </div>
        <p className="text-xs text-muted-foreground">
          Keys: O = Pinch, P = Drop
        </p>
      </CardContent>
    </Card>
  )
}
