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
            self.ser = serial.Serial(self.port, 115200, timeout=0.04)
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
        except Exception as e:
            # Log unique errors only (avoid spam)
            error_str = str(e)
            if not hasattr(self, '_last_read_error') or self._last_read_error != error_str:
                print(f"TFMiniS: Read error - {error_str}")
                self._last_read_error = error_str
        return -1

    def close(self):
        """Close serial connection."""
        if self.ser:
            try:
                self.ser.close()
            except Exception as e:
                print(f"TFMiniS: Close error - {e}")
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
