"""Software-only Car backed by a `SimWorld`.

Implements the same `CarBase` Protocol surface as `RealCar`, so the mission
code is identical whether running against the simulator or the real robot.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from challenge.sim.world import SimWorld


class _MockMotor:
    def __init__(self, world: SimWorld) -> None:
        self._world = world

    def setMotorModel(self, left: int, right: int) -> None:
        # Vendor clamps to [-4095, 4095].
        left = max(-4095, min(4095, int(left)))
        right = max(-4095, min(4095, int(right)))
        self._world.set_motor_cmd(left, right)

    def close(self) -> None:
        self._world.set_motor_cmd(0, 0)


class _MockSonic:
    def __init__(self, world: SimWorld) -> None:
        self._world = world

    def get_distance(self) -> float:
        return self._world.read_sonic_cm()

    def close(self) -> None:
        pass


class _MockIR:
    def __init__(self, world: SimWorld) -> None:
        self._world = world

    def read_all_infrared(self) -> int:
        return self._world.read_ir_code()

    def close(self) -> None:
        pass


class _MockServo:
    def __init__(self, world: SimWorld) -> None:
        self._world = world
        self._angles: dict[str, int] = {"0": 90, "1": 140, "2": 90}

    def setServoAngle(self, channel, angle: int) -> None:
        self._angles[str(channel)] = int(angle)
        self._world.set_servo_angle(channel, angle)

    def setServoStop(self) -> None:
        pass


class _MockCamera:
    def __init__(self, world: SimWorld) -> None:
        self._world = world

    def get_frame_bgr(self) -> Optional[np.ndarray]:
        return self._world.render_camera_bgr()

    def close(self) -> None:
        pass


class MockCar:
    """In-memory CarBase. The mission can't tell the difference."""

    def __init__(self, world: SimWorld) -> None:
        self.world = world
        self.motor = _MockMotor(world)
        self.sonic = _MockSonic(world)
        self.infrared = _MockIR(world)
        self.servo = _MockServo(world)
        self.camera = _MockCamera(world)
        self.infrared_run_stop = False

    def set_mode_clamp(self, mode: int) -> None:
        self.world.set_clamp_mode(mode)

    def get_mode_clamp(self) -> int:
        return self.world.get_clamp_mode()

    def mode_clamp(self, mode: int | None = None) -> None:
        if mode is not None:
            self.world.set_clamp_mode(mode)
        # The mission blocks while polling clamp mode, so advance the simulated
        # servo lifecycle here instead of waiting for the outer runner loop.
        self.world.tick(self.world.config.dt_s)

    def close(self) -> None:
        self.motor.close()
