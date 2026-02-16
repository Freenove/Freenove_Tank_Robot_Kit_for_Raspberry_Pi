import { ConnectionPanel } from '@/components/ConnectionPanel'
import { VideoStream } from '@/components/VideoStream'
import { MovementControls } from '@/components/MovementControls'
import { CameraControls } from '@/components/CameraControls'
import { LEDPanel } from '@/components/LEDPanel'
import { ModeSelector } from '@/components/ModeSelector'
import { GripperControls } from '@/components/GripperControls'
import { SensorDisplay } from '@/components/SensorDisplay'
import { AIChat } from '@/components/AIChat'
import { useKeyboardControls } from '@/hooks/useKeyboardControls'
import { useRobotStore } from '@/stores/robotStore'
import './index.css'

function App() {
  useKeyboardControls()
  const { mode } = useRobotStore()
  const isAIMode = mode === 3

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Tank Robot Control</h1>
          <div className="text-sm text-muted-foreground">
            WASD: Move | IJKL: Camera | O/P: Gripper
          </div>
        </header>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column: Video + AI Chat */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            <VideoStream />
            {isAIMode && <AIChat />}
          </div>

          {/* Right Column: Controls */}
          <div className="space-y-4">
            <ConnectionPanel />
            <ModeSelector />
            <MovementControls />
            <CameraControls />
          </div>
        </div>

        {/* Bottom Row: Secondary Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <LEDPanel />
          <GripperControls />
          <SensorDisplay />
        </div>
      </div>
    </div>
  )
}

export default App
