"""
Robot TCP Client - Handles communication with the tank robot.

Port 5003: Command channel (bidirectional text commands)
Port 8003: Video channel (length-prefixed JPEG stream)
"""

import socket
import struct
import threading
import asyncio
from typing import Optional, Callable, AsyncGenerator
from dataclasses import dataclass


@dataclass
class SensorData:
    ultrasonic: Optional[float] = None
    gripper_status: Optional[str] = None  # "stopped", "up_complete", "down_complete"


class RobotClient:
    """Manages TCP connections to the robot."""

    CMD_PORT = 5003
    VIDEO_PORT = 8003

    def __init__(self):
        self._cmd_socket: Optional[socket.socket] = None
        self._video_socket: Optional[socket.socket] = None
        self._connected = False
        self._video_running = False
        self._ip: Optional[str] = None
        self._recv_thread: Optional[threading.Thread] = None
        self._sensors = SensorData()
        self._sensor_callbacks: list[Callable[[str, any], None]] = []
        self._lock = threading.Lock()
        self._latest_frame: Optional[bytes] = None  # Cache latest video frame

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def ip(self) -> Optional[str]:
        return self._ip

    @property
    def sensors(self) -> SensorData:
        return self._sensors

    def add_sensor_callback(self, callback: Callable[[str, any], None]):
        """Register callback for sensor updates: callback(sensor_type, value)"""
        self._sensor_callbacks.append(callback)

    def connect(self, ip: str) -> bool:
        """Connect to robot command channel."""
        if self._connected:
            self.disconnect()

        try:
            self._cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._cmd_socket.settimeout(5.0)
            self._cmd_socket.connect((ip, self.CMD_PORT))
            self._cmd_socket.settimeout(None)
            self._connected = True
            self._ip = ip

            # Start receive thread for sensor data
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()

            print(f"Connected to robot at {ip}")
            return True
        except Exception as e:
            print(f"Failed to connect to {ip}: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from robot."""
        self._connected = False
        self._video_running = False

        if self._cmd_socket:
            try:
                self._cmd_socket.shutdown(socket.SHUT_RDWR)
                self._cmd_socket.close()
            except:
                pass
            self._cmd_socket = None

        if self._video_socket:
            try:
                self._video_socket.shutdown(socket.SHUT_RDWR)
                self._video_socket.close()
            except:
                pass
            self._video_socket = None

        self._ip = None
        print("Disconnected from robot")

    def send_command(self, cmd: str):
        """Send command to robot. Format: CMD_TYPE#param1#param2#...\n"""
        if not self._connected or not self._cmd_socket:
            return

        if not cmd.endswith('\n'):
            cmd += '\n'

        with self._lock:
            try:
                self._cmd_socket.send(cmd.encode('utf-8'))
            except Exception as e:
                print(f"Error sending command: {e}")

    def _recv_loop(self):
        """Background thread to receive sensor data."""
        buffer = ""
        while self._connected and self._cmd_socket:
            try:
                data = self._cmd_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self._parse_response(line.strip())
            except Exception as e:
                if self._connected:
                    print(f"Receive error: {e}")
                break

    def _parse_response(self, line: str):
        """Parse response from robot."""
        if not line:
            return

        parts = line.split('#')
        cmd = parts[0]

        if cmd == "CMD_SONIC" and len(parts) > 1:
            try:
                distance = float(parts[1])
                self._sensors.ultrasonic = distance
                for cb in self._sensor_callbacks:
                    cb("ultrasonic", distance)
            except ValueError:
                pass

        elif cmd == "CMD_ACTION" and len(parts) > 1:
            status_map = {"0": "stopped", "10": "up_complete", "20": "down_complete"}
            status = status_map.get(parts[1], "unknown")
            self._sensors.gripper_status = status
            for cb in self._sensor_callbacks:
                cb("gripper", status)

    # === Video Streaming ===

    def start_video(self) -> bool:
        """Start video connection."""
        if not self._ip:
            return False

        try:
            self._video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._video_socket.settimeout(5.0)
            self._video_socket.connect((self._ip, self.VIDEO_PORT))
            self._video_socket.settimeout(None)
            self._video_running = True
            print("Video stream started")
            return True
        except Exception as e:
            print(f"Failed to start video: {e}")
            return False

    def stop_video(self):
        """Stop video connection."""
        self._video_running = False
        if self._video_socket:
            try:
                self._video_socket.shutdown(socket.SHUT_RDWR)
                self._video_socket.close()
            except:
                pass
            self._video_socket = None

    async def video_frames(self) -> AsyncGenerator[bytes, None]:
        """Async generator yielding JPEG frames."""
        if not self._video_socket:
            return

        loop = asyncio.get_event_loop()

        try:
            # Use makefile for easier reading
            connection = self._video_socket.makefile('rb')

            def read_frame():
                """Blocking read of one frame - runs in thread pool."""
                try:
                    length_bytes = connection.read(4)
                    if len(length_bytes) < 4:
                        return None

                    length = struct.unpack('<L', length_bytes)[0]
                    if length == 0 or length > 1_000_000:
                        return b''  # Empty = skip this frame

                    jpeg_data = connection.read(length)
                    if len(jpeg_data) < length:
                        return None

                    return jpeg_data
                except Exception:
                    return None

            while self._video_running:
                # Run blocking read in thread pool to avoid blocking event loop
                jpeg_data = await loop.run_in_executor(None, read_frame)

                if jpeg_data is None:
                    break
                if jpeg_data == b'':
                    continue  # Skip invalid frame

                # Validate JPEG (basic check)
                if self._is_valid_jpeg(jpeg_data):
                    # Cache the latest frame for get_camera_frame()
                    self._latest_frame = jpeg_data
                    yield jpeg_data

        except Exception as e:
            print(f"Video stream error: {e}")
        finally:
            self.stop_video()

    def _is_valid_jpeg(self, data: bytes) -> bool:
        """Basic JPEG validation."""
        if len(data) < 10:
            return False
        # Check for JFIF or Exif marker
        if data[6:10] in (b'JFIF', b'Exif'):
            # Check for JPEG end marker
            return data.rstrip(b'\0\r\n').endswith(b'\xff\xd9')
        return True  # Allow other valid formats

    def get_camera_frame(self) -> Optional[bytes]:
        """Get the latest camera frame (JPEG) for AI vision.

        Returns the most recent frame from the video stream, or None if
        video isn't running or no frames have been received yet.
        """
        return self._latest_frame

    # === Convenience Methods ===

    def motor(self, left: int, right: int):
        """Set motor speeds. Range: -4095 to 4095"""
        left = max(-4095, min(4095, left))
        right = max(-4095, min(4095, right))
        self.send_command(f"CMD_MOTOR#{left}#{right}")

    def stop(self):
        """Stop all motors."""
        self.motor(0, 0)

    def servo(self, channel: int, angle: int):
        """Set servo angle. Channel: 0=pan, 1=tilt. Angle: 90-150"""
        angle = max(90, min(150, angle))
        self.send_command(f"CMD_SERVO#{channel}#{angle}")

    def led(self, mode: int, r: int, g: int, b: int, mask: int = 15):
        """Set LED color. Mode: 0=off, 1=on, 2-5=animations. Mask: bitmask for LEDs 1-4"""
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        self.send_command(f"CMD_LED#{mode}#{r}#{g}#{b}#{mask}")

    def led_mode(self, mode: int):
        """Set LED animation mode."""
        self.send_command(f"CMD_LED_MOD#{mode}")

    def set_mode(self, mode: int):
        """Set robot mode. 0=free, 1=sonic, 2=line"""
        self.send_command(f"CMD_MODE#{mode}")

    def gripper(self, action: int):
        """Control gripper. 0=stop, 1=up, 2=down"""
        self.send_command(f"CMD_ACTION#{action}")

    def request_ultrasonic(self):
        """Request ultrasonic distance reading."""
        self.send_command("CMD_SONIC#")


# Global singleton instance
robot = RobotClient()
