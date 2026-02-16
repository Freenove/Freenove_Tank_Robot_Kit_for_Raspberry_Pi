import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useRobotStore } from '@/stores/robotStore'
import { useVideoStream } from '@/hooks/useVideoStream'
import { Video, VideoOff } from 'lucide-react'

export function VideoStream() {
  const { videoUrl, connected } = useRobotStore()
  useVideoStream()

  return (
    <Card className="flex-1">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          {videoUrl ? <Video className="h-5 w-5" /> : <VideoOff className="h-5 w-5" />}
          Video Feed
        </CardTitle>
      </CardHeader>
      <CardContent className="p-2">
        <div className="relative aspect-[4/3] bg-muted rounded-md overflow-hidden flex items-center justify-center">
          {videoUrl ? (
            <img
              src={videoUrl}
              alt="Robot camera"
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="text-muted-foreground text-sm">
              {connected ? 'Waiting for video...' : 'Connect to robot to view video'}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
