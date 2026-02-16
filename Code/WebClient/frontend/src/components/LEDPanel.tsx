import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { useRobotStore } from '@/stores/robotStore'
import { api } from '@/lib/api'
import { Lightbulb } from 'lucide-react'

export function LEDPanel() {
  const { connected, ledR, ledG, ledB, ledMask, setLedColor, setLedMask } = useRobotStore()
  const [ledMode, setLedMode] = useState(0)

  // Individual LED toggles
  const leds = [
    { id: 1, bit: 0x01 },
    { id: 2, bit: 0x02 },
    { id: 3, bit: 0x04 },
    { id: 4, bit: 0x08 },
  ]

  const handleLedToggle = (bit: number, checked: boolean) => {
    const newMask = checked ? ledMask | bit : ledMask & ~bit
    setLedMask(newMask)
  }

  const sendLed = async (mode: number) => {
    if (!connected) return
    try {
      await api.led(mode, ledR, ledG, ledB, ledMask)
    } catch (e) {
      console.error('LED error:', e)
    }
  }

  const handleColorChange = (channel: 'r' | 'g' | 'b', value: string) => {
    const num = Math.max(0, Math.min(255, parseInt(value) || 0))
    if (channel === 'r') setLedColor(num, ledG, ledB)
    else if (channel === 'g') setLedColor(ledR, num, ledB)
    else setLedColor(ledR, ledG, num)
  }

  const handleModeClick = async (mode: number) => {
    if (ledMode === mode) {
      // Toggle off
      setLedMode(0)
      await sendLed(0)
    } else {
      setLedMode(mode)
      await sendLed(mode)
    }
  }

  const handleApply = () => sendLed(1) // mode 1 = solid color

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          LEDs
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* LED selection */}
        <div className="flex items-center justify-between">
          {leds.map((led) => (
            <div key={led.id} className="flex items-center gap-1">
              <Checkbox
                id={`led-${led.id}`}
                checked={(ledMask & led.bit) !== 0}
                onCheckedChange={(checked) => handleLedToggle(led.bit, !!checked)}
                disabled={!connected}
              />
              <Label htmlFor={`led-${led.id}`} className="text-xs">
                L{led.id}
              </Label>
            </div>
          ))}
          <Button
            size="sm"
            variant="outline"
            onClick={() => setLedMask(ledMask === 0x0f ? 0 : 0x0f)}
            disabled={!connected}
          >
            {ledMask === 0x0f ? 'None' : 'All'}
          </Button>
        </div>

        {/* RGB inputs */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <Label className="text-xs text-red-500">R</Label>
            <Input
              type="number"
              min={0}
              max={255}
              value={ledR}
              onChange={(e) => handleColorChange('r', e.target.value)}
              disabled={!connected}
              className="h-8"
            />
          </div>
          <div>
            <Label className="text-xs text-green-500">G</Label>
            <Input
              type="number"
              min={0}
              max={255}
              value={ledG}
              onChange={(e) => handleColorChange('g', e.target.value)}
              disabled={!connected}
              className="h-8"
            />
          </div>
          <div>
            <Label className="text-xs text-blue-500">B</Label>
            <Input
              type="number"
              min={0}
              max={255}
              value={ledB}
              onChange={(e) => handleColorChange('b', e.target.value)}
              disabled={!connected}
              className="h-8"
            />
          </div>
        </div>

        {/* Color preview */}
        <div
          className="h-6 rounded-md border"
          style={{ backgroundColor: `rgb(${ledR}, ${ledG}, ${ledB})` }}
        />

        {/* Apply button */}
        <Button
          size="sm"
          className="w-full"
          disabled={!connected}
          onClick={handleApply}
        >
          Apply Color
        </Button>

        {/* LED modes */}
        <div className="grid grid-cols-4 gap-1">
          {[2, 3, 4, 5].map((mode) => (
            <Button
              key={mode}
              size="sm"
              variant={ledMode === mode ? 'default' : 'outline'}
              disabled={!connected}
              onClick={() => handleModeClick(mode)}
              className="text-xs"
            >
              M{mode - 1}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
