"""Protocols for the hardware surface the mission depends on.

Both the real backend (`real_car.RealCar`) and the simulated backend
(`mock_car.MockCar`) implement these. The mission talks only through them.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class MotorBase(Protocol):
    def setMotorModel(self, left: int, right: int) -> None: ...
    def close(self) -> None: ...


@runtime_checkable
class SonicBase(Protocol):
    def get_distance(self) -> float: ...
    def close(self) -> None: ...


@runtime_checkable
class IRBase(Protocol):
    def read_all_infrared(self) -> int: ...
    def close(self) -> None: ...


@runtime_checkable
class ServoBase(Protocol):
    def setServoAngle(self, channel, angle: int) -> None: ...
    def setServoStop(self) -> None: ...


@runtime_checkable
class CameraBase(Protocol):
    def get_frame_bgr(self) -> np.ndarray | None: ...
    def close(self) -> None: ...


@runtime_checkable
class CarBase(Protocol):
    motor: MotorBase
    sonic: SonicBase
    infrared: IRBase
    servo: ServoBase
    camera: CameraBase
    infrared_run_stop: bool

    def set_mode_clamp(self, mode: int) -> None: ...
    def get_mode_clamp(self) -> int: ...
    def mode_clamp(self, mode: int | None = None) -> None: ...
    def close(self) -> None: ...
