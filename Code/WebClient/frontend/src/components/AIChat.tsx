import { useEffect, useRef, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useRobotStore } from '@/stores/robotStore'
import { Mic, MicOff, Bot } from 'lucide-react'

const MAX_RECONNECT_DELAY = 10000 // 10 seconds max
const INITIAL_RECONNECT_DELAY = 1000 // 1 second

export function AIChat() {
  const { connected, mode, aiState, aiTranscript, setAiState, addAiMessage } = useRobotStore()
  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY)
  const [error, setError] = useState<string | null>(null)

  const isAIMode = mode === 3

  const playAudio = useCallback(async (base64Data: string) => {
    try {
      // TTS returns WAV audio
      const response = await fetch(`data:audio/wav;base64,${base64Data}`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => URL.revokeObjectURL(url)
      await audio.play()
    } catch (e) {
      console.error('Failed to play audio:', e)
    }
  }, [])

  // Use ref for reconnection to avoid circular dependency
  const connectAIRef = useRef<() => void>(() => {})

  const connectAI = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(`ws://${window.location.host}/ws/ai`)
    wsRef.current = ws

    ws.onopen = () => {
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY
      setError(null)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'state') {
          setAiState(data.state)
        } else if (data.type === 'transcript') {
          addAiMessage(data.role, data.text)
        } else if (data.type === 'audio') {
          // Play TTS audio
          playAudio(data.data)
        } else if (data.type === 'error') {
          setError(data.message)
        }
      } catch (e) {
        console.error('Failed to parse AI message:', e)
      }
    }

    ws.onerror = () => {
      setError('AI WebSocket connection error')
    }

    ws.onclose = () => {
      wsRef.current = null
      setAiState('idle')
      // Only reconnect if still in AI mode and connected
      const state = useRobotStore.getState()
      if (state.connected && state.mode === 3) {
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(
            reconnectDelayRef.current * 2,
            MAX_RECONNECT_DELAY
          )
          connectAIRef.current()
        }, reconnectDelayRef.current)
      }
    }
  }, [setAiState, addAiMessage, playAudio])

  // Keep ref in sync (must be in useEffect to avoid "cannot update ref during render")
  useEffect(() => {
    connectAIRef.current = connectAI
  }, [connectAI])

  // Connect WebSocket when in AI mode
  useEffect(() => {
    if (!connected || !isAIMode) {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY
      return
    }

    connectAI()

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
  }, [connected, isAIMode, connectAI])

  // Scroll to bottom on new messages
  const scrollToBottom = useCallback(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [aiTranscript, scrollToBottom])

  const startRecording = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected to AI service')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const base64 = await blobToBase64(blob)

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'audio',
            data: base64,
          }))
        }

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop())
      }

      recorder.start()
      setAiState('listening')
      wsRef.current.send(JSON.stringify({ type: 'start_listening' }))
      setError(null)
    } catch (e) {
      setError('Failed to access microphone')
      console.error('Microphone error:', e)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
      setAiState('thinking')
    }
  }

  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64 = (reader.result as string).split(',')[1]
        resolve(base64)
      }
      reader.onerror = reject
      reader.readAsDataURL(blob)
    })
  }

  if (!isAIMode) {
    return null
  }

  return (
    <Card className="flex-1 flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="h-5 w-5" />
            AI Assistant
          </CardTitle>
          <Badge
            variant={
              aiState === 'idle'
                ? 'secondary'
                : aiState === 'listening'
                  ? 'destructive'
                  : aiState === 'thinking'
                    ? 'default'
                    : 'success'
            }
          >
            {aiState}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-3 min-h-0">
        <div
          ref={scrollContainerRef}
          className="flex-1 border rounded-md p-2 overflow-y-auto max-h-64"
        >
          {aiTranscript.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              Hold the button to talk to the AI assistant
            </p>
          ) : (
            <div className="space-y-2">
              {aiTranscript.map((msg, i) => (
                <div
                  key={i}
                  className={`text-sm p-2 rounded ${
                    msg.role === 'user'
                      ? 'bg-primary/10 text-right'
                      : 'bg-muted'
                  }`}
                >
                  <span className="font-medium">
                    {msg.role === 'user' ? 'You' : 'AI'}:
                  </span>{' '}
                  {msg.text}
                </div>
              ))}
            </div>
          )}
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button
          size="lg"
          variant={aiState === 'listening' ? 'destructive' : 'default'}
          disabled={!connected || aiState === 'thinking' || aiState === 'speaking'}
          onPointerDown={startRecording}
          onPointerUp={stopRecording}
          onPointerLeave={stopRecording}
          className="touch-none"
        >
          {aiState === 'listening' ? (
            <>
              <MicOff className="h-5 w-5 mr-2" />
              Release to Send
            </>
          ) : (
            <>
              <Mic className="h-5 w-5 mr-2" />
              Hold to Talk
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
