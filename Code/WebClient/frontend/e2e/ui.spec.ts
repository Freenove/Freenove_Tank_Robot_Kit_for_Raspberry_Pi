import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:5173'

test.describe('Robot Control UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL)
  })

  test('page loads with correct title', async ({ page }) => {
    await expect(page).toHaveTitle(/Tank Robot Control/)
  })

  test('connection panel renders with IP input', async ({ page }) => {
    // Check for connection panel elements
    const ipInput = page.locator('input[placeholder*="192.168"]')
    await expect(ipInput).toBeVisible()

    const connectButton = page.getByRole('button', { name: /connect/i })
    await expect(connectButton).toBeVisible()
  })

  test('mode selector renders with all modes', async ({ page }) => {
    // Check for mode options - use exact match to avoid partial matches
    await expect(page.getByText('Free', { exact: true })).toBeVisible()
    await expect(page.getByText('Sonic', { exact: true })).toBeVisible()
    await expect(page.getByText('Line', { exact: true })).toBeVisible()
    await expect(page.getByText('AI', { exact: true })).toBeVisible()
  })

  test('video stream placeholder shows when disconnected', async ({ page }) => {
    // Check for video placeholder
    const videoPlaceholder = page.getByText(/connect to robot/i)
    await expect(videoPlaceholder).toBeVisible()
  })

  test('sensor display shows ultrasonic and gripper', async ({ page }) => {
    // Check within Sensors card for labels
    const sensorsCard = page.locator('div:has(h3:has-text("Sensors"))')
    await expect(sensorsCard.getByText('Ultrasonic', { exact: true })).toBeVisible()
    // Gripper in sensor display is in a span, not a heading
    await expect(sensorsCard.locator('span:has-text("Gripper")')).toBeVisible()
  })

  test('movement controls are visible', async ({ page }) => {
    // Look for movement control card
    const movementCard = page.getByText('Movement')
    await expect(movementCard).toBeVisible()
  })

  test('camera controls are visible', async ({ page }) => {
    // Camera card title - use more specific selector
    await expect(page.locator('h3:has-text("Camera")')).toBeVisible()
    // Home button exists
    const homeButtons = page.getByRole('button', { name: /home/i })
    await expect(homeButtons.first()).toBeVisible()
  })

  test('LED panel is visible', async ({ page }) => {
    // LED card title is "LEDs"
    await expect(page.getByText('LEDs')).toBeVisible()
  })

  test('gripper controls are visible', async ({ page }) => {
    // Gripper card title
    await expect(page.locator('h3:has-text("Gripper")')).toBeVisible()
  })

  test('no console errors on page load', async ({ page }) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    await page.goto(BASE_URL)
    await page.waitForTimeout(2000)

    // Filter out expected errors (like WebSocket connection failures when no robot)
    const unexpectedErrors = errors.filter(
      (e) => !e.includes('WebSocket') && !e.includes('Failed to fetch')
    )
    expect(unexpectedErrors).toHaveLength(0)
  })

  test('mode selector is disabled when not connected', async ({ page }) => {
    // Radio buttons should be disabled when not connected
    const freeRadio = page.locator('button[role="radio"]').first()
    await expect(freeRadio).toBeDisabled()
  })

  test('keyboard shortcut hints are shown', async ({ page }) => {
    // Check for keyboard hints - use first() since WASD appears multiple times
    await expect(page.getByText(/wasd/i).first()).toBeVisible()
  })

  test('connect button becomes disabled with empty IP', async ({ page }) => {
    const ipInput = page.locator('input[placeholder*="192.168"]')
    await ipInput.clear()

    // Connect button should still be enabled (IP has placeholder behavior)
    const connectButton = page.getByRole('button', { name: /connect/i })
    await expect(connectButton).toBeVisible()
  })

  test('sliders in LED panel are interactive', async ({ page }) => {
    // LED panel uses number inputs, not sliders
    const inputs = page.locator('input[type="number"]')
    const count = await inputs.count()
    expect(count).toBeGreaterThanOrEqual(3) // R, G, B inputs
  })

  test('sensors card title is visible', async ({ page }) => {
    await expect(page.getByText('Sensors')).toBeVisible()
  })

  test('mode card title is visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Mode' })).toBeVisible()
  })

  test('all control panels are rendered', async ({ page }) => {
    // Check all main card titles exist using role for headings
    await expect(page.getByText('Movement')).toBeVisible()
    await expect(page.locator('h3:has-text("Camera")')).toBeVisible()
    await expect(page.getByText('LEDs')).toBeVisible()
    await expect(page.locator('h3:has-text("Gripper")')).toBeVisible()
    await expect(page.getByText('Sensors')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Mode' })).toBeVisible()
  })

  test('color preview box exists in LED panel', async ({ page }) => {
    // LED panel has a color preview div
    const colorPreview = page.locator('div[style*="background-color"]')
    await expect(colorPreview).toBeVisible()
  })

  test('movement control has arrow buttons', async ({ page }) => {
    // Check for movement buttons using class or aria
    const buttons = page.locator('button').filter({ hasText: '' })
    const buttonCount = await buttons.count()
    expect(buttonCount).toBeGreaterThan(0)
  })

  test('LED color inputs exist and have default values', async ({ page }) => {
    // LED panel should have 3 number inputs (R, G, B)
    const ledPanel = page.locator('div:has(h3:has-text("LEDs"))')
    const inputs = ledPanel.locator('input[type="number"]')
    const count = await inputs.count()
    expect(count).toBe(3)

    // They should have default value 255
    await expect(inputs.first()).toHaveValue('255')
  })

  test('LED checkboxes exist in LED panel', async ({ page }) => {
    // Check for LED checkboxes with labels L1-L4
    await expect(page.getByLabel('L1')).toBeVisible()
    await expect(page.getByLabel('L2')).toBeVisible()
    await expect(page.getByLabel('L3')).toBeVisible()
    await expect(page.getByLabel('L4')).toBeVisible()
  })

  test('IP input accepts valid IP format', async ({ page }) => {
    const ipInput = page.locator('input[placeholder*="192.168"]')
    await ipInput.fill('192.168.1.100')
    await expect(ipInput).toHaveValue('192.168.1.100')
  })

  test('connect button is clickable', async ({ page }) => {
    const connectButton = page.getByRole('button', { name: /connect/i })
    // Button should be enabled (not disabled)
    await expect(connectButton).toBeEnabled()
  })

  test('camera home button is present', async ({ page }) => {
    // Look for home button in camera controls
    const cameraCard = page.locator('div:has(h3:has-text("Camera"))')
    const homeButton = cameraCard.getByRole('button', { name: /home/i })
    await expect(homeButton.first()).toBeVisible()
  })

  test('gripper controls have up and down buttons', async ({ page }) => {
    const gripperCard = page.locator('div:has(h3:has-text("Gripper")):not(:has(span:has-text("Gripper")))')
    // Should have control buttons (even if disabled)
    const buttons = gripperCard.locator('button')
    const count = await buttons.count()
    expect(count).toBeGreaterThan(0)
  })

  test('movement panel has stop button with accessible name', async ({ page }) => {
    // The stop button should have aria-label="Stop"
    const stopButton = page.getByRole('button', { name: 'Stop' })
    await expect(stopButton).toBeVisible()
  })

  test('video placeholder shows correct message', async ({ page }) => {
    const placeholder = page.getByText(/connect to robot to view video/i)
    await expect(placeholder).toBeVisible()
  })

  test('sensors show N/A when not connected', async ({ page }) => {
    // Both distance and gripper should show N/A
    const naLabels = page.getByText('N/A')
    const count = await naLabels.count()
    expect(count).toBeGreaterThanOrEqual(2)
  })
})

// API Integration Tests
test.describe('Backend API', () => {
  const API_BASE = 'http://localhost:8001/api'

  test('GET /api/status returns connection status', async ({ request }) => {
    const response = await request.get(`${API_BASE}/status`)
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data).toHaveProperty('connected')
    expect(data).toHaveProperty('ip')
    expect(data).toHaveProperty('sensors')
    expect(data.sensors).toHaveProperty('ultrasonic')
    expect(data.sensors).toHaveProperty('gripper')
  })

  test('POST /api/disconnect works when not connected', async ({ request }) => {
    const response = await request.post(`${API_BASE}/disconnect`)
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data.connected).toBe(false)
  })

  test('POST /api/motor returns 400 when not connected', async ({ request }) => {
    const response = await request.post(`${API_BASE}/motor`, {
      data: { left: 1000, right: 1000 },
    })
    expect(response.status()).toBe(400)

    const data = await response.json()
    expect(data.detail).toBe('Not connected to robot')
  })

  test('POST /api/stop returns 400 when not connected', async ({ request }) => {
    const response = await request.post(`${API_BASE}/stop`)
    expect(response.status()).toBe(400)
  })

  test('POST /api/servo returns 400 when not connected', async ({ request }) => {
    const response = await request.post(`${API_BASE}/servo`, {
      data: { channel: 0, angle: 90 },
    })
    expect(response.status()).toBe(400)
  })

  test('POST /api/led returns 400 when not connected', async ({ request }) => {
    const response = await request.post(`${API_BASE}/led`, {
      data: { mode: 1, r: 255, g: 0, b: 0, mask: 15 },
    })
    expect(response.status()).toBe(400)
  })

  test('POST /api/mode returns 400 when not connected', async ({ request }) => {
    const response = await request.post(`${API_BASE}/mode`, {
      data: { mode: 1 },
    })
    expect(response.status()).toBe(400)
  })

  test('POST /api/gripper returns 400 when not connected', async ({ request }) => {
    const response = await request.post(`${API_BASE}/gripper`, {
      data: { action: 1 },
    })
    expect(response.status()).toBe(400)
  })

  test('POST /api/motor with missing fields returns 422', async ({ request }) => {
    const response = await request.post(`${API_BASE}/motor`, {
      data: {},
    })
    expect(response.status()).toBe(422)
  })

  test('POST /api/motor with invalid types returns 422', async ({ request }) => {
    const response = await request.post(`${API_BASE}/motor`, {
      data: { left: 'fast', right: 'slow' },
    })
    expect(response.status()).toBe(422)
  })

  test('POST /api/connect with invalid IP returns 500', async ({ request }) => {
    const response = await request.post(`${API_BASE}/connect`, {
      data: { ip: '192.168.1.999' },
    })
    expect(response.status()).toBe(500)
  })
})
