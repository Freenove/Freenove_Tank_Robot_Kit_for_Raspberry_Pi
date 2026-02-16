import { create } from 'zustand'

interface RobotState {
  // Connection
  connected: boolean
  ip: string
  setIp: (ip: string) => void
  setConnected: (connected: boolean) => void

  // Video
  videoUrl: string | null
  setVideoUrl: (url: string | null) => void

  // Servos
  servo1Angle: number
  servo2Angle: number
  setServo1Angle: (angle: number) => void
  setServo2Angle: (angle: number) => void

  // LEDs
  ledMask: number
  ledR: number
  ledG: number
  ledB: number
  setLedMask: (mask: number) => void
  setLedColor: (r: number, g: number, b: number) => void

  // Mode
  mode: number // 0=free, 1=sonic, 2=line, 3=ai
  setMode: (mode: number) => void

  // Sensors
  ultrasonicDistance: number | null
  gripperStatus: string | null
  setUltrasonicDistance: (distance: number | null) => void
  setGripperStatus: (status: string | null) => void

  // AI Mode
  aiState: 'idle' | 'listening' | 'thinking' | 'speaking'
  aiTranscript: Array<{ role: 'user' | 'assistant'; text: string }>
  setAiState: (state: 'idle' | 'listening' | 'thinking' | 'speaking') => void
  addAiMessage: (role: 'user' | 'assistant', text: string) => void
  clearAiTranscript: () => void
}

export const useRobotStore = create<RobotState>((set) => ({
  // Connection
  connected: false,
  ip: '192.168.4.1',
  setIp: (ip) => set({ ip }),
  setConnected: (connected) => set({ connected }),

  // Video
  videoUrl: null,
  setVideoUrl: (videoUrl) => set({ videoUrl }),

  // Servos (servo2 default is 140 to match PyQt)
  servo1Angle: 90,
  servo2Angle: 140,
  setServo1Angle: (servo1Angle) => set({ servo1Angle }),
  setServo2Angle: (servo2Angle) => set({ servo2Angle }),

  // LEDs (mask 15 = all LEDs selected)
  ledMask: 15,
  ledR: 255,
  ledG: 0,
  ledB: 0,
  setLedMask: (ledMask) => set({ ledMask }),
  setLedColor: (ledR, ledG, ledB) => set({ ledR, ledG, ledB }),

  // Mode
  mode: 0,
  setMode: (mode) => set({ mode }),

  // Sensors
  ultrasonicDistance: null,
  gripperStatus: null,
  setUltrasonicDistance: (ultrasonicDistance) => set({ ultrasonicDistance }),
  setGripperStatus: (gripperStatus) => set({ gripperStatus }),

  // AI Mode
  aiState: 'idle',
  aiTranscript: [],
  setAiState: (aiState) => set({ aiState }),
  addAiMessage: (role, text) =>
    set((state) => {
      const newTranscript = [...state.aiTranscript, { role, text }]
      // Limit to last 50 messages to prevent memory issues
      return { aiTranscript: newTranscript.slice(-50) }
    }),
  clearAiTranscript: () => set({ aiTranscript: [] }),
}))
