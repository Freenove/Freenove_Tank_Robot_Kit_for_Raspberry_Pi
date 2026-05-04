"""Tank kinematics: motor lag, slip noise, differential-drive integration."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple

import numpy as np

if TYPE_CHECKING:
    from .arena import Arena
    from .world import Pose2D, SimConfig


class RobotPhysics:
    def __init__(self, config: "SimConfig", rng: random.Random,
                 np_rng: np.random.Generator) -> None:
        self.config = config
        self.rng = rng
        self.np_rng = np_rng

    def update_wheels(
        self,
        cmd_left_duty: int,
        cmd_right_duty: int,
        actual_left_mps: float,
        actual_right_mps: float,
        dt: float,
    ) -> Tuple[float, float]:
        cfg = self.config

        def cmd_to_target(cmd: int) -> float:
            if abs(cmd) < cfg.motor_dead_zone_duty:
                return 0.0
            return cmd * cfg.duty_to_mps

        target_l = cmd_to_target(cmd_left_duty)
        target_r = cmd_to_target(cmd_right_duty)

        tau = max(cfg.motor_tau_s, 1e-3)
        alpha = min(1.0, dt / tau)
        new_l = actual_left_mps + alpha * (target_l - actual_left_mps)
        new_r = actual_right_mps + alpha * (target_r - actual_right_mps)

        if cfg.slip_sigma_per_duty > 0.0:
            sigma_l = abs(cmd_left_duty) * cfg.slip_sigma_per_duty * cfg.duty_to_mps
            sigma_r = abs(cmd_right_duty) * cfg.slip_sigma_per_duty * cfg.duty_to_mps
            new_l += self.np_rng.normal(0.0, sigma_l)
            new_r += self.np_rng.normal(0.0, sigma_r)

        return float(new_l), float(new_r)

    def integrate_pose(
        self,
        pose: "Pose2D",
        left_mps: float,
        right_mps: float,
        dt: float,
        arena: "Arena",
    ) -> "Pose2D":
        from .world import Pose2D

        v = 0.5 * (left_mps + right_mps)
        omega = (right_mps - left_mps) / max(self.config.wheel_base_m, 1e-3)

        new_heading = _normalize(pose.heading_rad + omega * dt)
        if self.config.heading_slip_sigma_rad > 0.0:
            new_heading = _normalize(
                new_heading + self.np_rng.normal(0.0, self.config.heading_slip_sigma_rad) * dt
            )

        new_x = pose.x_m + v * math.cos(new_heading) * dt
        new_y = pose.y_m + v * math.sin(new_heading) * dt

        # Hard collision check; if next pose is in obstacle/out of bounds, hold.
        if not arena.point_in_bounds(new_x, new_y, margin=0.02):
            new_x, new_y = pose.x_m, pose.y_m
        if arena.point_in_obstacle(new_x, new_y):
            new_x, new_y = pose.x_m, pose.y_m

        return Pose2D(x_m=new_x, y_m=new_y, heading_rad=new_heading)


def _normalize(theta: float) -> float:
    while theta > math.pi:
        theta -= 2.0 * math.pi
    while theta < -math.pi:
        theta += 2.0 * math.pi
    return theta
