import { useState } from 'react'
import { Wifi, WifiOff } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useRobotStore } from '@/stores/robotStore'
import { api } from '@/lib/api'

export function ConnectionPanel() {
  const { ip, setIp, connected, setConnected } = useRobotStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConnect = async () => {
    if (connected) {
      setLoading(true)
      try {
        await api.disconnect()
        setConnected(false)
      } catch (e) {
        console.error('Disconnect error:', e)
      } finally {
        setLoading(false)
      }
    } else {
      setLoading(true)
      setError(null)
      try {
        await api.connect(ip)
        setConnected(true)
      } catch (e) {
        setError('Failed to connect')
        console.error('Connect error:', e)
      } finally {
        setLoading(false)
      }
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            {connected ? <Wifi className="h-5 w-5" /> : <WifiOff className="h-5 w-5" />}
            Connection
          </CardTitle>
          <Badge variant={connected ? 'success' : 'destructive'}>
            {connected ? 'Connected' : 'Disconnected'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            placeholder="192.168.4.1"
            value={ip}
            onChange={(e) => setIp(e.target.value)}
            disabled={connected || loading}
          />
          <Button
            onClick={handleConnect}
            disabled={loading}
            variant={connected ? 'destructive' : 'default'}
          >
            {loading ? '...' : connected ? 'Disconnect' : 'Connect'}
          </Button>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  )
}
