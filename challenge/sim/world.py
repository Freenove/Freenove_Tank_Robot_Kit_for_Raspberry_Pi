"""SimWorld — owns arena, robot pose, and tick advancement.

Skeleton in step 2; physics, sensors, and arena get filled in step 4+.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .arena import Arena
from .physics import RobotPhysics


@dataclass
class Pose2D:
    x_m: float = 0.0
    y_m: float = 0.0
    heading_rad: float = 0.0


@dataclass
class ClampState:
    """Mock clamp lifecycle. real robot uses servos + ultrasonic alignment;
    here we model just enough for the mission to observe pickup/drop timing.
    """

    mode: int = 0  # 0 stop, 1 picking-up, 2 dropping
    progress: float = 0.0  # 0..1 within the current mode


@dataclass
class SimConfig:
    dt_s: float = 0.02
    duty_to_mps: float = 0.00022
    wheel_base_m: float = 0.16
    motor_tau_s: float = 0.08
    motor_dead_zone_duty: int = 80
    slip_sigma_per_duty: float = 0.0  # set non-zero for noise scenarios
    heading_slip_sigma_rad: float = 0.0
    ultrasonic_noise_cm: float = 0.0
    ultrasonic_miss_prob: float = 0.0
    ir_flicker_prob: float = 0.0
    pickup_radius_m: float = 0.10
    clamp_phase_s: float = 0.5
    seed: int | None = None


class SimWorld:
    """Lightweight world container; tick(dt) advances physics + clamp state."""

    def __init__(
        self,
        arena: Optional[Arena] = None,
        config: Optional[SimConfig] = None,
    ) -> None:
        self.config = config or SimConfig()
        self.arena = arena or Arena.empty()
        self.arena.world = self
        self.rng = random.Random(self.config.seed)
        self.np_rng = np.random.default_rng(self.config.seed)
        self.physics = RobotPhysics(self.config, self.rng, self.np_rng)

        self.pose = Pose2D(*self.arena.robot_start)
        self.cmd_left_duty = 0
        self.cmd_right_duty = 0
        self.actual_left_mps = 0.0
        self.actual_right_mps = 0.0

        self.clamp = ClampState()
        self.carrying_ball = False
        self.elapsed_s = 0.0
        self.tick_count = 0
        self.servo_angles: dict[str, int] = {"0": 90, "1": 140, "2": 90}

        # Last sensor readings (refreshed on tick)
        self.last_ir_code: int = 0
        self.last_sonic_cm: float = -1.0

    # -- command surface (called by MockCar)

    def set_motor_cmd(self, left: int, right: int) -> None:
        self.cmd_left_duty = int(left)
        self.cmd_right_duty = int(right)

    def set_clamp_mode(self, mode: int) -> None:
        if mode != self.clamp.mode:
            self.clamp.mode = int(mode)
            self.clamp.progress = 0.0

    def get_clamp_mode(self) -> int:
        return self.clamp.mode

    def set_servo_angle(self, channel, angle: int) -> None:
        self.servo_angles[str(channel)] = int(angle)

    def get_servo_angle(self, channel, default: int | None = None) -> int | None:
        return self.servo_angles.get(str(channel), default)

    def carry_pose_is_raised(self) -> bool:
        return self.servo_angles.get("0", 0) >= 145 and self.servo_angles.get("1", 0) >= 135

    # -- queries (called by MockCar sensors)

    def read_ir_code(self) -> int:
        from .sensors import read_ir_code

        code = read_ir_code(self.arena, self.pose, self.np_rng, self.config)
        self.last_ir_code = code
        return code

    def read_sonic_cm(self) -> float:
        from .sensors import read_sonic_cm

        cm = read_sonic_cm(self.arena, self.pose, self.np_rng, self.config)
        self.last_sonic_cm = cm
        return cm

    def render_camera_bgr(self) -> Optional[np.ndarray]:
        from .camera_render import render_camera_bgr

        return render_camera_bgr(self.arena, self.pose, self.config)

    # -- simulation tick

    def tick(self, dt: Optional[float] = None) -> None:
        dt = dt if dt is not None else self.config.dt_s

        self.actual_left_mps, self.actual_right_mps = self.physics.update_wheels(
            self.cmd_left_duty,
            self.cmd_right_duty,
            self.actual_left_mps,
            self.actual_right_mps,
            dt,
        )

        self.pose = self.physics.integrate_pose(
            self.pose,
            self.actual_left_mps,
            self.actual_right_mps,
            dt,
            self.arena,
        )

        self._advance_clamp(dt)

        self.elapsed_s += dt
        self.tick_count += 1

    def _advance_clamp(self, dt: float) -> None:
        if self.clamp.mode == 0:
            return

        self.clamp.progress = min(1.0, self.clamp.progress + dt / self.config.clamp_phase_s)
        if self.clamp.progress < 1.0:
            return

        if self.clamp.mode == 1 and not self.carrying_ball:
            ball = self.arena.find_ball_within(
                self.pose.x_m, self.pose.y_m, self.config.pickup_radius_m
            )
            if ball is not None:
                self.arena.remove_ball(ball)
                self.carrying_ball = True
        elif self.clamp.mode == 2 and self.carrying_ball:
            self.carrying_ball = False
            # Drop the ball where the robot stands so visualizers can show it.
            self.arena.add_ball(self.pose.x_m, self.pose.y_m, ball_radius_m=0.04)

        self.clamp.mode = 0
        self.clamp.progress = 0.0
