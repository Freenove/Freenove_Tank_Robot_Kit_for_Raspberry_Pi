"""Hardware backend factory.

`make_car` returns either the real Freenove `Car` (wrapped) or a simulated
`MockCar` backed by a `SimWorld`. The mission code is identical in both
cases — same `CarBase` Protocol surface.
"""

from __future__ import annotations

import sys
from typing import Literal

from .base import CarBase

Mode = Literal["sim", "real", "auto"]


def make_car(mode: Mode = "auto", world=None) -> CarBase:
    if mode == "auto":
        mode = "real" if sys.platform.startswith("linux") else "sim"

    if mode == "sim":
        from challenge.sim.world import SimWorld
        from .mock_car import MockCar

        if world is None:
            world = SimWorld()
        return MockCar(world)

    if mode == "real":
        if not sys.platform.startswith("linux"):
            raise RuntimeError(
                "real mode requires Raspberry Pi/Linux hardware; use --mode sim on this platform"
            )
        from .real_car import RealCar

        return RealCar()

    raise ValueError(f"unknown mode: {mode!r}")


__all__ = ["make_car", "CarBase"]
