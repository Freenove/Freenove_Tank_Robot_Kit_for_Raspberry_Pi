"""Sensor models: 3-IR array (footprint sample), ultrasonic cone raycast."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .arena import Arena
    from .world import Pose2D, SimConfig


# IR offsets in robot body frame (forward, lateral) — left, center, right.
# `forward` is along +heading, `lateral` is left-positive.
IR_OFFSETS_M = (
    (0.10, +0.04),  # IR01 (left)
    (0.10, 0.00),   # IR02 (center)
    (0.10, -0.04),  # IR03 (right)
)


def read_ir_code(arena: "Arena", pose: "Pose2D",
                 np_rng: np.random.Generator, config: "SimConfig") -> int:
    """Return the 3-bit IR code matching the vendor convention.

    Bit layout matches `Code/Server/infrared.py:read_all_infrared`:
        (IR01 << 2) | (IR02 << 1) | IR03
    Each bit is 1 when the sensor is over the black line.
    """
    cos_h = math.cos(pose.heading_rad)
    sin_h = math.sin(pose.heading_rad)

    code = 0
    for i, (forward, lateral) in enumerate(IR_OFFSETS_M):
        x = pose.x_m + forward * cos_h - lateral * sin_h
        y = pose.y_m + forward * sin_h + lateral * cos_h
        on = arena.is_on_line(x, y)
        if config.ir_flicker_prob > 0.0 and np_rng.random() < config.ir_flicker_prob:
            on = not on
        bit = 1 if on else 0
        if i == 0:
            code |= bit << 2
        elif i == 1:
            code |= bit << 1
        else:
            code |= bit
    return code


def read_sonic_cm(arena: "Arena", pose: "Pose2D",
                  np_rng: np.random.Generator, config: "SimConfig") -> float:
    """HC-SR04 cone modeled as 7 rays across ~15°; report min hit in cm."""
    if config.ultrasonic_miss_prob > 0.0 and np_rng.random() < config.ultrasonic_miss_prob:
        return -1.0

    fan_deg = (-7.5, -5.0, -2.5, 0.0, 2.5, 5.0, 7.5)
    forward_offset = 0.10  # sensor mounted ~10 cm in front of pose

    sx = pose.x_m + forward_offset * math.cos(pose.heading_rad)
    sy = pose.y_m + forward_offset * math.sin(pose.heading_rad)

    best_m = float("inf")
    for d_deg in fan_deg:
        theta = pose.heading_rad + math.radians(d_deg)
        d = arena.raycast(sx, sy, theta, max_range_m=3.0, step_m=0.005)
        if d < best_m:
            best_m = d
    cm = best_m * 100.0
    if config.ultrasonic_noise_cm > 0.0:
        cm += float(np_rng.normal(0.0, config.ultrasonic_noise_cm))
    return round(max(0.0, cm), 1)
