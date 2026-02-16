# feat: TF-Mini S LiDAR Integration for Obstacle Detection

## Overview

Integrate TF-Mini S laser distance sensor at the front of the Freenove Tank Robot for precision obstacle detection. Automatic speed reduction when approaching obstacles.

**Key Benefits:**
- 1cm accuracy (vs 3cm for ultrasonic)
- 100Hz update rate (vs ~40Hz)
- 2.3 narrow beam (vs 15 wide cone)
- 0.1-12m range (vs 0.02-4m)
- Works on angled/soft surfaces

## Problem Statement

The existing HC-SR04 ultrasonic sensor has reliability issues:
- Hanging during tests ("echo pin set high" warning)
- Wide beam angle detects irrelevant objects
- Poor accuracy at close range

## Proposed Solution

Add a front-facing TF-Mini S sensor via USB-UART. Implement 2-zone speed limiting:
- **STOP zone** (<10cm): Full stop for safety
- **SLOW zone** (10-40cm): Linear speed reduction
- **FULL zone** (>40cm): No limiting

Reverse motion is NOT limited (sensor faces forward only).

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Raspberry Pi                         │
│                                                          │
│  ┌──────────────┐         ┌─────────────────────────┐   │
│  │   main.py    │         │      tfminis.py         │   │
│  │              │         │                         │   │
│  │ _lidar_thread├────────►│ TFMiniS.read_distance() │   │
│  │   @ 20Hz     │         │                         │   │
│  └──────┬───────┘         └────────────┬────────────┘   │
│         │                              │                 │
│         │ _lidar_distance              │                 │
│         │ (with _lidar_lock)           │                 │
│         ▼                              │                 │
│  ┌──────────────┐                      │                 │
│  │ gamepad loop │                      │                 │
│  │ speed limit  │                      │                 │
│  └──────┬───────┘                      │                 │
│         │                              │                 │
│         ▼                              │                 │
│  ┌──────────────┐                      │                 │
│  │  Motor PWM   │                      │                 │
│  └──────────────┘                      │                 │
└────────────────────────────────────────┼─────────────────┘
                                         │
                               ┌─────────▼─────────┐
                               │ CP2102 USB-UART   │
                               │ /dev/ttyUSB0      │
                               └─────────┬─────────┘
                                         │
                               ┌─────────▼─────────┐
                               │   TF-Mini S       │
                               │   LiDAR Sensor    │
                               └───────────────────┘
```

## Technical Approach

### Data Frame Format

TF-Mini S outputs 9-byte frames at 100Hz (115200 baud):

| Byte | Content | Description |
|------|---------|-------------|
| 0-1 | 0x59 0x59 | Header |
| 2-3 | Dist_L/H | `distance_cm = byte2 + (byte3 << 8)` |
| 4-7 | Strength/Temp | (ignored) |
| 8 | Checksum | `sum(bytes 0-7) & 0xFF` |

### Speed Control (2 Zones)

| Distance | Speed | Behavior |
|----------|-------|----------|
| >= 40cm | 100% | Full speed |
| 10-40cm | Linear | `speed * (dist / 40)` |
| < 10cm | 0% | **STOP** |
| Invalid | 0% | **Fail-safe STOP** |

**Simple formula:**
```python
if dist < 10:
    scale = 0.0
elif dist < 40:
    scale = dist / 40.0
else:
    scale = 1.0
```

### Thread Safety

```python
# LiDAR thread writes:
with self._lidar_lock:
    self._lidar_distance = distance

# Gamepad thread reads:
with self._lidar_lock:
    dist = self._lidar_distance
```

## Implementation

### Phase 1: tfminis.py Driver

**Create:** `Code/Server/tfminis.py` (~45 lines)

```python
"""TF-Mini S LiDAR driver - minimal implementation."""

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not installed. Run: sudo pip3 install pyserial")


class TFMiniS:
    """TF-Mini S LiDAR sensor driver."""

    def __init__(self, port='/dev/ttyUSB0'):
        self.port = port
        self.ser = None

    def connect(self):
        """Open serial connection. Returns True on success."""
        if not SERIAL_AVAILABLE:
            print("TFMiniS: pyserial not available")
            return False
        try:
            self.ser = serial.Serial(self.port, 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            print(f"TFMiniS: Connected on {self.port}")
            return True
        except Exception as e:
            print(f"TFMiniS: {e}")
            return False

    def read_distance(self):
        """Returns distance in cm, or -1 if invalid."""
        if not self.ser:
            return -1
        try:
            self.ser.reset_input_buffer()  # Always read fresh
            data = self.ser.read(9)
            if len(data) == 9 and data[0] == 0x59 and data[1] == 0x59:
                if (sum(data[:8]) & 0xFF) == data[8]:  # Checksum
                    dist = data[2] + (data[3] << 8)
                    if 10 <= dist <= 1200:
                        return dist
        except Exception:
            pass
        return -1

    def close(self):
        """Close serial connection."""
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            print("TFMiniS: Disconnected")


# Standalone test
if __name__ == '__main__':
    import time
    print("TF-Mini S Test - Press Ctrl+C to exit")

    sensor = TFMiniS()
    if not sensor.connect():
        exit(1)

    try:
        while True:
            dist = sensor.read_distance()
            if dist >= 0:
                print(f"\rDistance: {dist:4d} cm", end="")
            else:
                print(f"\rNo reading       ", end="")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopping...")
        sensor.close()
```

**Deliverables:**
- [x] `TFMiniS` class with `connect()`, `read_distance()`, `close()`
- [x] Checksum validation
- [x] Range validation (10-1200cm)
- [x] Standalone test

### Phase 2: main.py Integration

**Modify:** `Code/Server/main.py` (~40 lines added)

```python
# === ADD IMPORT at top ===
from tfminis import TFMiniS

# === ADD TO config_task() after gamepad init ===
# LiDAR state (private, underscore prefix)
self._lidar = None
self._lidar_distance = 0
self._lidar_lock = threading.Lock()
self._lidar_available = False
self._lidar_thread = None
self._lidar_thread_is_running = False

# === ADD METHOD: set_threading_lidar ===
def set_threading_lidar(self, state, close_time=0.3):
    """Start or stop LiDAR thread."""
    if self._lidar_thread is None:
        buf_state = False
    else:
        buf_state = self._lidar_thread.is_alive()

    if state != buf_state:
        if state:
            self._lidar_thread_is_running = True
            self._lidar_thread = threading.Thread(target=self.threading_lidar, daemon=True)
            self._lidar_thread.start()
            print("LiDAR thread started")
        else:
            self._lidar_thread_is_running = False
            if self._lidar_thread is not None:
                self._lidar_thread.join(close_time)
                self._lidar_thread = None
            print("LiDAR thread stopped")

# === ADD METHOD: threading_lidar ===
def threading_lidar(self):
    """Read LiDAR at 20Hz, update shared distance variable."""
    # Initialize sensor
    self._lidar = TFMiniS()
    if not self._lidar.connect():
        print("LiDAR: Not available (continuing without)")
        return

    self._lidar_available = True
    fail_count = 0

    while self._lidar_thread_is_running:
        lidar_ref = self._lidar  # Local reference for thread safety
        if lidar_ref:
            distance = lidar_ref.read_distance()

            if distance >= 0:
                with self._lidar_lock:
                    self._lidar_distance = distance
                fail_count = 0
            else:
                fail_count += 1
                if fail_count >= 10:  # 500ms at 20Hz
                    with self._lidar_lock:
                        self._lidar_distance = 0  # Fail-safe stop
                    print("LiDAR: Fail-safe triggered")
                    fail_count = 0  # Reset to avoid spam

        time.sleep(0.05)  # 20Hz

    # Cleanup
    if self._lidar:
        self._lidar.close()
        self._lidar = None
    self._lidar_available = False

# === MODIFY on_pushButton_handle() - Server On branch ===
# After: self.set_threading_gamepad(True)
# Add:
self.set_threading_lidar(True)

# === MODIFY on_pushButton_handle() - Server Off branch ===
# After: self.set_threading_gamepad(False)
# Add:
self.set_threading_lidar(False)

# === MODIFY close_application() ===
# After: self.set_threading_gamepad(False)
# Add:
self.set_threading_lidar(False)
```

**Deliverables:**
- [x] LiDAR thread with 20Hz polling
- [x] Thread-safe distance updates with `_lidar_lock`
- [x] Fail-safe: distance=0 after 500ms of failures
- [x] Proper cleanup in `close_application()` and server off
- [x] Graceful degradation if sensor not found

### Phase 3: Speed Limiting in threading_gamepad

**Modify:** `Code/Server/main.py` threading_gamepad() (~15 lines)

```python
# === IN threading_gamepad(), after calculating left_speed/right_speed ===
# === BEFORE calling car.motor.setMotorModel() ===

# Apply obstacle speed limiting (forward only)
if forward > 0 and self._lidar_available:
    with self._lidar_lock:
        dist = self._lidar_distance

    if dist <= 0:          # Fail-safe or error
        left_speed = 0
        right_speed = 0
    elif dist < 10:        # STOP zone
        left_speed = 0
        right_speed = 0
    elif dist < 40:        # SLOW zone (linear)
        scale = dist / 40.0
        left_speed = int(left_speed * scale)
        right_speed = int(right_speed * scale)
    # else: dist >= 40, full speed (no change)
```

**Deliverables:**
- [x] 2-zone speed control (stop/slow/full)
- [x] Forward-only limiting
- [x] Fail-safe stop on invalid readings

### Phase 4: setup.py Dependency

**Modify:** `Code/setup.py` (~2 lines)

```python
# Add to install_status dict:
"pyserial": False,

# Add to package installation section:
install_status["pyserial"] = check_and_install("pyserial")
```

## Acceptance Criteria

### Functional
- [ ] Sensor detected and connected on startup
- [ ] Robot stops at <10cm from obstacle
- [ ] Robot slows proportionally at 10-40cm
- [ ] Full speed at >40cm
- [ ] Reverse/turning unaffected
- [ ] Works without sensor (graceful degradation)

### Safety
- [ ] Fail-safe stop within 500ms of sensor failure
- [ ] Thread-safe distance access

## Hardware Required

| Item | Purpose | Status |
|------|---------|--------|
| TF-Mini S sensor | Distance measurement | Have |
| CP2102 USB-UART | Connect to Pi | **Need** |
| Dupont wires (4x) | Wiring | Need |

### Wiring

```
TF-Mini S          CP2102 USB-UART
---------          ---------------
VCC (Red)    -->   5V
GND (Black)  -->   GND
TX (Green)   -->   RX
RX (White)   -->   TX (optional)

CP2102 USB --> Raspberry Pi USB port
```

## Pi Setup Prerequisites

Before connecting the sensor, ensure the Pi is configured:

### 1. Serial Port Permissions

Add user to `dialout` group (required for `/dev/ttyUSB*` access):

```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

### 2. Install pyserial

```bash
sudo pip3 install pyserial
```

### 3. Verify USB-UART Adapter

After plugging in CP2102:

```bash
# Check if device appears
ls /dev/ttyUSB*
# Should show: /dev/ttyUSB0

# Check kernel messages
dmesg | tail -10
# Should show: cp210x converter now attached to ttyUSB0

# Verify permissions
ls -la /dev/ttyUSB0
# Should show: crw-rw---- 1 root dialout ...
```

### 4. Test Serial Connection (Optional)

```bash
# Install screen if needed
sudo apt install screen

# Connect to sensor (Ctrl+A then K to exit)
screen /dev/ttyUSB0 115200
# Should see garbled binary data (sensor output)
```

## Testing Checklist

### Setup Verification
- [ ] User is in `dialout` group: `groups | grep dialout`
- [ ] pyserial installed: `python3 -c "import serial; print('OK')"`
- [ ] CP2102 recognized: `ls /dev/ttyUSB*`

### Standalone
- [ ] `python3 tfminis.py` shows distances
- [ ] `sudo python test.py Lidar` shows distances
- [ ] Hand approach shows decreasing values

### Integration
- [ ] Server starts with sensor
- [ ] Server starts without sensor
- [ ] Forward stops at <10cm
- [ ] Forward slows at 10-40cm
- [ ] Reverse unaffected
- [ ] Unplug sensor -> fail-safe stop

## File Summary

| File | Action | Lines |
|------|--------|-------|
| `Code/Server/tfminis.py` | CREATE | ~78 |
| `Code/Server/main.py` | MODIFY | ~60 |
| `Code/Server/test.py` | MODIFY | ~22 |
| `Code/setup.py` | MODIFY | ~2 |
| `PI_TEST_ALL.sh` | MODIFY | ~6 |
| `PI_SETUP_COMMANDS.sh` | MODIFY | ~1 |

## Rollback Plan

If issues arise:
1. Comment out `set_threading_lidar()` calls in `on_pushButton_handle()`
2. Comment out speed limiting block in `threading_gamepad()`
3. Robot operates exactly as before

## References

- [TF-Mini S Product Manual](https://cdn.sparkfun.com/assets/8/a/f/a/c/16977-TFMini-S_-_Micro_LiDAR_Module-Product_Manual.pdf)
- [pySerial Documentation](https://pyserial.readthedocs.io/en/latest/)

---

**Plan created:** 2025-12-26
**Plan revised:** 2025-12-26 (simplified after review)
**Implemented:** 2025-12-26 (commit 060c491)
**Status:** Software complete. Testing pending hardware (CP2102 USB-UART adapter)
