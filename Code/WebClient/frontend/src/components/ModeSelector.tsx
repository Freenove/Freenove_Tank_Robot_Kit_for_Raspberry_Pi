import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { useRobotStore } from '@/stores/robotStore'
import { api } from '@/lib/api'
import { Settings } from 'lucide-react'

const modes = [
  { value: 0, label: 'Free', description: 'Manual control' },
  { value: 1, label: 'Sonic', description: 'Ultrasonic obstacle avoidance' },
  { value: 2, label: 'Line', description: 'Line following mode' },
  { value: 3, label: 'AI', description: 'AI voice control' },
]

export function ModeSelector() {
  const { connected, mode, setMode } = useRobotStore()

  const handleModeChange = async (value: string) => {
    const newMode = parseInt(value)
    setMode(newMode)
    if (connected && newMode !== 3) {
      // AI mode is handled separately
      try {
        await api.setMode(newMode)
      } catch (e) {
        console.error('Mode error:', e)
      }
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Mode
        </CardTitle>
      </CardHeader>
      <CardContent>
        <RadioGroup
          value={mode.toString()}
          onValueChange={handleModeChange}
          disabled={!connected}
          className="grid grid-cols-2 gap-2"
        >
          {modes.map((m) => (
            <div key={m.value} className="flex items-center space-x-2">
              <RadioGroupItem value={m.value.toString()} id={`mode-${m.value}`} />
              <Label
                htmlFor={`mode-${m.value}`}
                className="flex flex-col cursor-pointer"
              >
                <span className="font-medium">{m.label}</span>
                <span className="text-xs text-muted-foreground">{m.description}</span>
              </Label>
            </div>
          ))}
        </RadioGroup>
      </CardContent>
    </Card>
  )
}
