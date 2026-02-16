# Freenove Tank Robot Kit (FNK0077) - Complete Setup Plan

## Hardware: Raspberry Pi 3B | PCB Version: V1.0

---

## Phase 1: Hardware Assembly (Physical Build)

### 1.1 PCB Version (CONFIRMED: V1.0)
Your board uses:
- GPIO7/8 for servos
- GPIO18 for LEDs
- Requires `pigpiod` daemon running before server start

### 1.2 Chassis Assembly (Steps 1-9 in manual)
- [ ] Attach line tracking sensor to acrylic (2x M3X12 screws, 2x M3 nuts)
- [ ] Install four support frames (4x M3X12 screws, 4x M3 nuts)
- [ ] Assemble drive wheels (M4x50 half-tooth screws, M4 nuts)
- [ ] Mount motor brackets (2x M3x30 screws, 2x M3 nuts per side)
- [ ] Connect couplings to motors (M3x8 screws)
- [ ] Attach track drivers (M3x8 screws)
- [ ] Install tracks on both sides

### 1.3 Sensor & Camera Mount (Steps 10-11, 20)
- [ ] Mount ultrasonic sensor on acrylic (8x M1.4x5 screws)
- [ ] Attach camera to mount (1x M3x12 screw, 1x M3 nut)
- [ ] **IMPORTANT:** Connect CSI camera cable to Pi (power OFF!)
  - Blue side of cable faces Ethernet port on Pi 3B
  - Lift connector tab, insert cable, press tab down

### 1.4 Upper Structure (Steps 12-19)
- [ ] Install four standoffs (4x M3x8 screws)
- [ ] Secure battery case (4x M3x10 screws, 4x M3 nuts)
- [ ] Mount servo for camera pan (2x M2x20 screws, 2x M2 nuts)
- [ ] Install Raspberry Pi with standoffs
- [ ] Connect all wiring per diagram
- [ ] Assemble upper/lower chassis (4x M3x8 screws)

### 1.5 Grabber Arm Assembly (Steps 24-37)
**CRITICAL: Run servo calibration BEFORE mounting arm parts!**

```bash
# SSH into Pi first, then:
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server
sudo python test.py Servo
# This rotates servos to 90° - install arm parts at this position!
# Press Ctrl+C when done
```

- [ ] Install servo mounting hardware at 90° position
- [ ] Mount acrylic lever (2x M4x10 rivets)
- [ ] Secure structural components (2x M3x12 screws, 2x M3 nuts)
- [ ] Install steering servo per servo package instructions
- [ ] Complete final arm structure with remaining standoffs/rivets

---

## Phase 2: Software Installation (On Raspberry Pi)

### 2.1 Prerequisites
```bash
# Ensure Pi is connected to WiFi
# SSH into Pi:
ssh pi@<your-pi-ip>
# Default password: raspberry
```

### 2.2 Clone Repository (if not done)
```bash
cd ~
git clone --depth 1 https://github.com/Freenove/Freenove_Tank_Robot_Kit_for_Raspberry_Pi.git
```

### 2.3 Set Permissions
```bash
sudo chmod 755 -R ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi
```

### 2.4 Run Setup Script
```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code
sudo python setup.py
```

**Prompts you'll see:**
1. Camera type: Select **OV5647** (included in kit)
2. This enables I2C, Camera interface, and installs all dependencies

### 2.5 Reboot
```bash
sudo reboot
```

---

## Phase 3: Module Testing

**Run all tests from:** `~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server`

```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server
```

### For Pi 3B with PCB V1.0 - Run This First:
```bash
sudo pigpiod
```

### Test Commands (Ctrl+C to exit each):

| Component | Command | Expected Result |
|-----------|---------|-----------------|
| Motors | `sudo python test.py Motor` | Forward 1s, back 1s, left 1s, right 1s, stop |
| IR Sensors | `sudo python test.py Infrared` | Shows Left/Middle/Right based on tape |
| LEDs | `sudo python test.py Led` | Color patterns cycle |
| Servos | `sudo python test.py Servo` | Arm opens/closes, moves up/down |
| Ultrasonic | `sudo python test.py Ultrasonic` | Distance readings every 0.3s |
| Camera | `sudo python test.py camera` | Saves image.jpg after 5s |

**Note:** Enable S1 and S2 switches on PCB for motor test!

---

## Phase 4: Server & Client Setup

### 4.1 Start Server (on Pi)
```bash
cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server

# For Pi 3B with V1.0 PCB:
sudo pigpiod
sudo python main.py
```

### 4.2 Start Client (on Mac)
```bash
cd ~/Documents/GitHub/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code
python3 setup_macos.py

cd Client
python3 Main.py
```

### 4.3 Connect
1. Enter Pi's IP address in client
2. Click Connect (or press C)
3. Click Video (or press V) for camera feed

### Keyboard Controls:
| Key | Action |
|-----|--------|
| W/S | Forward/Backward |
| A/D | Turn Left/Right |
| Arrow Keys | Pan camera |
| Home | Reset camera |
| L | Cycle LED modes |
| Q | Change mode |

---

## Phase 5: Speedlink RAIT Controller Setup

**The Freenove client does NOT have built-in gamepad support.**
We need to add it using pygame.

### 5.1 Install pygame on Mac
```bash
pip3 install pygame
```

### 5.2 Test Controller Detection
```bash
python3 << 'EOF'
import pygame
pygame.init()
pygame.joystick.init()

count = pygame.joystick.get_count()
print(f"Found {count} joystick(s)")

for i in range(count):
    js = pygame.joystick.Joystick(i)
    js.init()
    print(f"  {i}: {js.get_name()}")
    print(f"     Axes: {js.get_numaxes()}")
    print(f"     Buttons: {js.get_numbuttons()}")
EOF
```

### 5.3 Controller Integration Options

**Option A:** Modify the Freenove Client (recommended)
- Add pygame joystick input to `Client/Main.py`
- Map analog sticks to motor control
- Map buttons to functions

**Option B:** Use pygame-controller library
```bash
pip3 install pygame-controller
```

**Option C:** Create a separate controller bridge script
- Reads gamepad input
- Sends commands to Pi server via TCP

---

## Troubleshooting

### Camera not working
```bash
# Check camera is detected:
vcgencmd get_camera
# Should show: supported=1 detected=1

# For Pi 3B, also check:
sudo raspi-config
# Interface Options > Camera > Enable
```

### Motors not moving
- Check S1 and S2 switches are ON
- Check battery voltage (needs charged 18650s)
- Verify wiring connections

### LEDs not working
- V1.0 PCB: rpi_ws281x issues on Pi 5 (not Pi 3B)
- Check LED ribbon cable connection

### Server won't start
```bash
# Kill any existing processes:
sudo killall python
sudo killall pigpiod

# Restart:
sudo pigpiod
sudo python main.py
```

---

## Quick Reference

| Item | Value |
|------|-------|
| Pi Model | Raspberry Pi 3B |
| PCB Version | V1.0 |
| Camera | OV5647 |
| Server Port | 5000 (default) |
| Video Port | 8000 (default) |
| Repository | `~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi` |

---

## Sources
- [Freenove FNK0077 Online Docs](https://docs.freenove.com/projects/fnk0077/en/latest/)
- [GitHub Repository](https://github.com/Freenove/Freenove_Tank_Robot_Kit_for_Raspberry_Pi)
- [pygame-controller](https://github.com/Footleg/pygame-controller)
