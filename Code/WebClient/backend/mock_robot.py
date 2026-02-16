"""Mock Robot Client for testing AI agent without hardware.

Drop-in replacement for RobotClient that logs commands to console.
Includes mock vision for testing perception-based navigation.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SensorData:
    ultrasonic: Optional[float] = None
    gripper_status: Optional[str] = None


@dataclass
class MockObject:
    """An object in the mock environment."""
    name: str
    direction: str  # "ahead", "left", "right", "behind"
    distance_cm: float
    description: str = ""


class MockRobotClient:
    """Mock robot for testing AI agent without hardware.

    Includes mock vision that simulates camera perception for testing
    navigation and object-finding capabilities.
    """

    def __init__(self, ultrasonic: float = 50.0, gripper: str = "stopped"):
        self._connected = True
        self._ip = "mock://test"
        self._sensors = SensorData(ultrasonic=ultrasonic, gripper_status=gripper)
        self._command_log: list[str] = []

        # Mock vision state
        self._mock_scene = "A room with wooden floor and white walls."
        self._mock_objects: list[MockObject] = []
        self._current_heading = 0  # 0=forward, 90=left, 180=behind, 270=right

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def ip(self) -> Optional[str]:
        return self._ip

    @property
    def sensors(self) -> SensorData:
        return self._sensors

    def set_ultrasonic(self, distance: float):
        """Test helper: set ultrasonic reading."""
        self._sensors.ultrasonic = distance

    def set_gripper(self, status: str):
        """Test helper: set gripper status."""
        self._sensors.gripper_status = status

    def set_connected(self, connected: bool):
        """Test helper: set connection state."""
        self._connected = connected

    def _log(self, cmd: str):
        self._command_log.append(cmd)
        print(f"  [MOCK] {cmd}")

    def get_command_log(self) -> list[str]:
        """Get all commands sent during this session."""
        return self._command_log.copy()

    def clear_log(self):
        """Clear command log."""
        self._command_log.clear()

    # Robot interface methods (match RobotClient exactly)
    def motor(self, left: int, right: int):
        """Set motor speeds. Range: -4095 to 4095"""
        left = max(-4095, min(4095, left))
        right = max(-4095, min(4095, right))
        self._log(f"CMD_MOTOR#{left}#{right}")

    def stop(self):
        """Stop all motors."""
        self._log("CMD_MOTOR#0#0")

    def servo(self, channel: int, angle: int):
        """Set servo angle. Channel: 0=pan, 1=tilt. Angle: 90-150"""
        angle = max(90, min(150, angle))
        self._log(f"CMD_SERVO#{channel}#{angle}")

    def led(self, mode: int, r: int, g: int, b: int, mask: int = 15):
        """Set LED color. Mode: 0=off, 1=on, 2-5=animations."""
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        self._log(f"CMD_LED#{mode}#{r}#{g}#{b}#{mask}")

    def led_mode(self, mode: int):
        """Set LED animation mode."""
        self._log(f"CMD_LED_MOD#{mode}")

    def set_mode(self, mode: int):
        """Set robot mode. 0=free, 1=sonic, 2=line"""
        self._log(f"CMD_MODE#{mode}")

    def gripper(self, action: int):
        """Control gripper. 0=stop, 1=up, 2=down"""
        self._log(f"CMD_ACTION#{action}")

    def request_ultrasonic(self):
        """Request ultrasonic distance reading."""
        self._log("CMD_SONIC#")

    # === Mock Vision Support ===

    def set_mock_scene(self, scene: str):
        """Set the base scene description for mock vision."""
        self._mock_scene = scene

    def add_mock_object(self, name: str, direction: str, distance_cm: float, description: str = ""):
        """Add an object to the mock environment.

        Args:
            name: Object name (e.g., "red ball", "wooden chair")
            direction: Where it is relative to robot ("ahead", "left", "right", "behind")
            distance_cm: How far away
            description: Optional extra description
        """
        self._mock_objects.append(MockObject(name, direction, distance_cm, description))

    def clear_mock_objects(self):
        """Remove all mock objects."""
        self._mock_objects.clear()

    def get_mock_vision(self, question: str = None) -> str:
        """Simulate camera vision response.

        Args:
            question: Optional specific question about the scene.

        Returns:
            Simulated vision description.
        """
        # Build description of visible objects (based on current heading)
        visible_objects = []
        for obj in self._mock_objects:
            # Calculate if object is visible from current heading
            obj_angle = {"ahead": 0, "left": 90, "right": 270, "behind": 180}.get(obj.direction, 0)
            relative_angle = (obj_angle - self._current_heading) % 360

            # Objects within ~60 degrees of forward are visible
            if relative_angle <= 60 or relative_angle >= 300:
                if relative_angle <= 30 or relative_angle >= 330:
                    pos = "directly ahead"
                elif relative_angle < 180:
                    pos = "slightly to the left"
                else:
                    pos = "slightly to the right"
                visible_objects.append(f"{obj.name} {pos}, about {obj.distance_cm:.0f}cm away")

        # Handle specific questions
        if question:
            question_lower = question.lower()

            # Check if asking about a specific object
            for obj in self._mock_objects:
                if obj.name.lower() in question_lower:
                    # Check if visible
                    obj_angle = {"ahead": 0, "left": 90, "right": 270, "behind": 180}.get(obj.direction, 0)
                    relative_angle = (obj_angle - self._current_heading) % 360

                    if relative_angle <= 60 or relative_angle >= 300:
                        return f"Yes, I see the {obj.name} {obj.direction}, about {obj.distance_cm:.0f}cm away. {obj.description}"
                    else:
                        return f"I don't see the {obj.name} in my current view. It might be {obj.direction}."

            # Generic question response
            if visible_objects:
                return f"I see: {', '.join(visible_objects)}. {self._mock_scene}"
            else:
                return f"I don't see that. {self._mock_scene}"

        # No question - general scene description
        if visible_objects:
            return f"{self._mock_scene} I see: {', '.join(visible_objects)}."
        else:
            return self._mock_scene

    def simulate_turn(self, degrees: int):
        """Update mock heading after a turn (for vision simulation).

        Args:
            degrees: Rotation amount. Positive=left, negative=right.
        """
        self._current_heading = (self._current_heading + degrees) % 360

    def simulate_move_toward(self, distance_cm: float):
        """Update mock object distances after moving forward.

        Args:
            distance_cm: How far the robot moved forward.
        """
        for obj in self._mock_objects:
            if obj.direction == "ahead":
                obj.distance_cm = max(0, obj.distance_cm - distance_cm)
        # Also update ultrasonic
        if self._sensors.ultrasonic is not None:
            self._sensors.ultrasonic = max(0, self._sensors.ultrasonic - distance_cm)
