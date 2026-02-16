const API_BASE = '/api'

async function post(endpoint: string, data: Record<string, unknown> = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }
  return response.json()
}

export const api = {
  connect: (ip: string) => post('/connect', { ip }),
  disconnect: () => post('/disconnect'),
  motor: (left: number, right: number) => post('/motor', { left, right }),
  stop: () => post('/stop'),
  servo: (channel: number, angle: number) => post('/servo', { channel, angle }),
  led: (mode: number, r: number, g: number, b: number, mask: number) =>
    post('/led', { mode, r, g, b, mask }),
  setMode: (mode: number) => post('/mode', { mode }),
  gripper: (action: number) => post('/gripper', { action }),
}
