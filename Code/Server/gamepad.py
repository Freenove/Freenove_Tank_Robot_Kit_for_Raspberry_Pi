#!/usr/bin/env python3
"""
Gamepad controller support for Freenove Tank Robot.
Uses evdev to read USB gamepad input on Raspberry Pi.

Designed for Speedlink RAIT controller (Xbox-style layout).
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    print("Warning: evdev not installed. Run: sudo pip3 install evdev")


@dataclass
class GamepadState:
    """Current state of all gamepad inputs."""
    # Axes (-1.0 to 1.0)
    left_stick_x: float = 0.0   # Left/Right
    left_stick_y: float = 0.0   # Up/Down (inverted: up = negative)
    right_stick_x: float = 0.0  # Camera pan
    right_stick_y: float = 0.0  # Camera tilt
    left_trigger: float = 0.0   # LT (0.0 to 1.0)
    right_trigger: float = 0.0  # RT (0.0 to 1.0)

    # Buttons (True = pressed)
    button_a: bool = False      # Emergency stop
    button_b: bool = False      #
    button_x: bool = False      #
    button_y: bool = False      # LED mode
    button_lb: bool = False     # Left bumper
    button_rb: bool = False     # Right bumper
    button_start: bool = False  #
    button_select: bool = False #
    button_home: bool = False   # Center home/guide button

    # D-Pad
    dpad_x: int = 0  # -1 = left, 0 = center, 1 = right
    dpad_y: int = 0  # -1 = up, 0 = center, 1 = down

    # Connection status
    connected: bool = False


class Gamepad:
    """
    Gamepad controller reader for Raspberry Pi.

    Usage:
        gamepad = Gamepad()
        gamepad.start()

        while True:
            state = gamepad.get_state()
            if state.connected:
                # Use state.left_stick_x, state.button_a, etc.
            time.sleep(0.02)

        gamepad.stop()
    """

    # Axis codes for Xbox-style controllers
    AXIS_LEFT_X = ecodes.ABS_X if EVDEV_AVAILABLE else 0
    AXIS_LEFT_Y = ecodes.ABS_Y if EVDEV_AVAILABLE else 1
    AXIS_RIGHT_X = ecodes.ABS_RX if EVDEV_AVAILABLE else 3
    AXIS_RIGHT_Y = ecodes.ABS_RY if EVDEV_AVAILABLE else 4
    AXIS_LEFT_TRIGGER = ecodes.ABS_Z if EVDEV_AVAILABLE else 2
    AXIS_RIGHT_TRIGGER = ecodes.ABS_RZ if EVDEV_AVAILABLE else 5
    AXIS_DPAD_X = ecodes.ABS_HAT0X if EVDEV_AVAILABLE else 16
    AXIS_DPAD_Y = ecodes.ABS_HAT0Y if EVDEV_AVAILABLE else 17

    # Button codes
    BTN_A = ecodes.BTN_SOUTH if EVDEV_AVAILABLE else 304
    BTN_B = ecodes.BTN_EAST if EVDEV_AVAILABLE else 305
    BTN_X = ecodes.BTN_NORTH if EVDEV_AVAILABLE else 307
    BTN_Y = ecodes.BTN_WEST if EVDEV_AVAILABLE else 308
    BTN_LB = ecodes.BTN_TL if EVDEV_AVAILABLE else 310
    BTN_RB = ecodes.BTN_TR if EVDEV_AVAILABLE else 311
    BTN_SELECT = ecodes.BTN_SELECT if EVDEV_AVAILABLE else 314
    BTN_START = ecodes.BTN_START if EVDEV_AVAILABLE else 315
    BTN_HOME = ecodes.BTN_MODE if EVDEV_AVAILABLE else 316

    def __init__(self, deadzone: float = 0.1):
        """
        Initialize gamepad reader.

        Args:
            deadzone: Ignore stick values below this threshold (0.0-1.0)
        """
        self.deadzone = deadzone
        self._state = GamepadState()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._device: Optional[InputDevice] = None

        # Axis calibration (will be set from device capabilities)
        self._axis_min = {}
        self._axis_max = {}

    def _find_gamepad(self) -> Optional[InputDevice]:
        """Find a connected gamepad device."""
        if not EVDEV_AVAILABLE:
            return None

        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            capabilities = device.capabilities()
            # Look for devices with absolute axes (joysticks)
            if ecodes.EV_ABS in capabilities:
                abs_caps = capabilities[ecodes.EV_ABS]
                # Check if it has typical gamepad axes
                axis_codes = [cap[0] if isinstance(cap, tuple) else cap for cap in abs_caps]
                if ecodes.ABS_X in axis_codes and ecodes.ABS_Y in axis_codes:
                    print(f"Found gamepad: {device.name} at {device.path}")
                    return device
        return None

    def _calibrate_axes(self, device: InputDevice):
        """Read axis min/max values from device capabilities."""
        capabilities = device.capabilities()
        if ecodes.EV_ABS in capabilities:
            for cap in capabilities[ecodes.EV_ABS]:
                if isinstance(cap, tuple):
                    axis_code, axis_info = cap
                    self._axis_min[axis_code] = axis_info.min
                    self._axis_max[axis_code] = axis_info.max

    def _normalize_axis(self, code: int, value: int) -> float:
        """Convert raw axis value to -1.0 to 1.0 range."""
        min_val = self._axis_min.get(code, 0)
        max_val = self._axis_max.get(code, 255)

        # Normalize to -1.0 to 1.0
        center = (min_val + max_val) / 2
        half_range = (max_val - min_val) / 2

        if half_range == 0:
            return 0.0

        normalized = (value - center) / half_range

        # Apply deadzone
        if abs(normalized) < self.deadzone:
            return 0.0

        return max(-1.0, min(1.0, normalized))

    def _normalize_trigger(self, code: int, value: int) -> float:
        """Convert trigger value to 0.0 to 1.0 range."""
        min_val = self._axis_min.get(code, 0)
        max_val = self._axis_max.get(code, 255)

        if max_val == min_val:
            return 0.0

        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))

    def _reader_loop(self):
        """Main loop that reads gamepad events."""
        reconnect_delay = 1.0

        while self._running:
            # Try to find/reconnect gamepad
            if self._device is None:
                self._device = self._find_gamepad()
                if self._device is None:
                    with self._lock:
                        self._state.connected = False
                    time.sleep(reconnect_delay)
                    continue
                else:
                    self._calibrate_axes(self._device)
                    with self._lock:
                        self._state.connected = True

            # Read events
            try:
                for event in self._device.read_loop():
                    if not self._running:
                        break

                    with self._lock:
                        if event.type == ecodes.EV_ABS:
                            # Axis event
                            if event.code == self.AXIS_LEFT_X:
                                self._state.left_stick_x = self._normalize_axis(event.code, event.value)
                            elif event.code == self.AXIS_LEFT_Y:
                                self._state.left_stick_y = self._normalize_axis(event.code, event.value)
                            elif event.code == self.AXIS_RIGHT_X:
                                self._state.right_stick_x = self._normalize_axis(event.code, event.value)
                            elif event.code == self.AXIS_RIGHT_Y:
                                self._state.right_stick_y = self._normalize_axis(event.code, event.value)
                            elif event.code == self.AXIS_LEFT_TRIGGER:
                                self._state.left_trigger = self._normalize_trigger(event.code, event.value)
                            elif event.code == self.AXIS_RIGHT_TRIGGER:
                                self._state.right_trigger = self._normalize_trigger(event.code, event.value)
                            elif event.code == self.AXIS_DPAD_X:
                                self._state.dpad_x = event.value
                            elif event.code == self.AXIS_DPAD_Y:
                                self._state.dpad_y = event.value

                        elif event.type == ecodes.EV_KEY:
                            # Button event
                            pressed = event.value == 1
                            if event.code == self.BTN_A:
                                self._state.button_a = pressed
                            elif event.code == self.BTN_B:
                                self._state.button_b = pressed
                            elif event.code == self.BTN_X:
                                self._state.button_x = pressed
                            elif event.code == self.BTN_Y:
                                self._state.button_y = pressed
                            elif event.code == self.BTN_LB:
                                self._state.button_lb = pressed
                            elif event.code == self.BTN_RB:
                                self._state.button_rb = pressed
                            elif event.code == self.BTN_START:
                                self._state.button_start = pressed
                            elif event.code == self.BTN_SELECT:
                                self._state.button_select = pressed
                            elif event.code == self.BTN_HOME:
                                self._state.button_home = pressed

            except OSError:
                # Device disconnected
                print("Gamepad disconnected")
                self._device = None
                with self._lock:
                    self._state = GamepadState()  # Reset state

    def start(self):
        """Start reading gamepad input in background thread."""
        if self._running:
            return

        if not EVDEV_AVAILABLE:
            print("Cannot start gamepad: evdev not installed")
            return

        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        print("Gamepad reader started")

    def stop(self):
        """Stop reading gamepad input."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._device is not None:
            self._device = None
        print("Gamepad reader stopped")

    def get_state(self) -> GamepadState:
        """Get current gamepad state (thread-safe copy)."""
        with self._lock:
            return GamepadState(
                left_stick_x=self._state.left_stick_x,
                left_stick_y=self._state.left_stick_y,
                right_stick_x=self._state.right_stick_x,
                right_stick_y=self._state.right_stick_y,
                left_trigger=self._state.left_trigger,
                right_trigger=self._state.right_trigger,
                button_a=self._state.button_a,
                button_b=self._state.button_b,
                button_x=self._state.button_x,
                button_y=self._state.button_y,
                button_lb=self._state.button_lb,
                button_rb=self._state.button_rb,
                button_start=self._state.button_start,
                button_select=self._state.button_select,
                button_home=self._state.button_home,
                dpad_x=self._state.dpad_x,
                dpad_y=self._state.dpad_y,
                connected=self._state.connected
            )

    def is_connected(self) -> bool:
        """Check if gamepad is connected."""
        with self._lock:
            return self._state.connected


# Standalone test
if __name__ == '__main__':
    print("Gamepad Test - Press Ctrl+C to exit")
    print("=" * 50)

    if not EVDEV_AVAILABLE:
        print("ERROR: evdev not installed!")
        print("Run: sudo pip3 install evdev")
        exit(1)

    gamepad = Gamepad(deadzone=0.15)
    gamepad.start()

    try:
        last_state = None
        while True:
            state = gamepad.get_state()

            # Only print when state changes significantly
            if state.connected:
                print(f"\rL:({state.left_stick_x:+.2f},{state.left_stick_y:+.2f}) "
                      f"R:({state.right_stick_x:+.2f},{state.right_stick_y:+.2f}) "
                      f"LT:{state.left_trigger:.2f} RT:{state.right_trigger:.2f} "
                      f"A:{int(state.button_a)} B:{int(state.button_b)} "
                      f"X:{int(state.button_x)} Y:{int(state.button_y)}", end="")
            else:
                print("\rWaiting for gamepad...", end="")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\nStopping...")
        gamepad.stop()
        print("Done")
