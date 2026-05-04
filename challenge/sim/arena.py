"""Arena geometry: bounded field, black line polylines, obstacles, balls.

The line is rasterized into a binary mask that IR sensors sample. Obstacles
are circles or axis-aligned rectangles. Balls are circles with a colour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class Polyline:
    points_m: List[Tuple[float, float]]
    width_m: float = 0.03


@dataclass
class CircleObstacle:
    cx: float
    cy: float
    r: float


@dataclass
class RectObstacle:
    cx: float
    cy: float
    half_w: float
    half_h: float


@dataclass
class Ball:
    cx: float
    cy: float
    r: float
    color_bgr: Tuple[int, int, int] = (40, 40, 200)  # red in BGR


@dataclass
class Arena:
    width_m: float = 4.0
    height_m: float = 4.0
    line_polylines: List[Polyline] = field(default_factory=list)
    circle_obstacles: List[CircleObstacle] = field(default_factory=list)
    rect_obstacles: List[RectObstacle] = field(default_factory=list)
    balls: List[Ball] = field(default_factory=list)
    robot_start: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (x, y, theta)

    # Line mask cache (lazy)
    _line_mask: Optional[np.ndarray] = None
    _line_mask_resolution: float = 0.01  # metres per pixel

    @classmethod
    def empty(cls) -> "Arena":
        return cls()

    def add_ball(self, cx: float, cy: float, ball_radius_m: float = 0.04,
                 color_bgr: Tuple[int, int, int] = (40, 40, 200)) -> Ball:
        ball = Ball(cx=cx, cy=cy, r=ball_radius_m, color_bgr=color_bgr)
        self.balls.append(ball)
        return ball

    def remove_ball(self, ball: Ball) -> None:
        try:
            self.balls.remove(ball)
        except ValueError:
            pass

    def find_ball_within(self, x: float, y: float, radius_m: float) -> Optional[Ball]:
        best: Optional[Ball] = None
        best_d = radius_m
        for ball in self.balls:
            d = math.hypot(ball.cx - x, ball.cy - y)
            if d <= best_d:
                best_d = d
                best = ball
        return best

    # -- line mask (binary, 1 where black tape exists)

    def line_mask(self) -> np.ndarray:
        if self._line_mask is not None:
            return self._line_mask

        cell = self._line_mask_resolution
        rows = max(1, int(round(self.height_m / cell)))
        cols = max(1, int(round(self.width_m / cell)))
        mask = np.zeros((rows, cols), dtype=np.uint8)

        for line in self.line_polylines:
            half_w_px = max(1, int(round(line.width_m / cell / 2.0)))
            for (x0, y0), (x1, y1) in zip(line.points_m, line.points_m[1:]):
                self._rasterize_segment(mask, x0, y0, x1, y1, half_w_px, cell)

        self._line_mask = mask
        return mask

    def _rasterize_segment(
        self,
        mask: np.ndarray,
        x0: float, y0: float, x1: float, y1: float,
        half_w_px: int, cell: float,
    ) -> None:
        # Sample the segment finely; stamp a square footprint at each step.
        rows, cols = mask.shape
        length = math.hypot(x1 - x0, y1 - y0)
        steps = max(2, int(length / (cell * 0.5)))
        for i in range(steps + 1):
            t = i / steps
            x = x0 + t * (x1 - x0)
            y = y0 + t * (y1 - y0)
            j = int(round(x / cell))
            r = int(round(y / cell))
            j_lo = max(0, j - half_w_px); j_hi = min(cols, j + half_w_px + 1)
            r_lo = max(0, r - half_w_px); r_hi = min(rows, r + half_w_px + 1)
            if j_hi > j_lo and r_hi > r_lo:
                mask[r_lo:r_hi, j_lo:j_hi] = 1

    def world_xy_to_mask_idx(self, x: float, y: float) -> Tuple[int, int]:
        cell = self._line_mask_resolution
        j = int(round(x / cell))
        r = int(round(y / cell))
        return r, j

    def is_on_line(self, x: float, y: float) -> bool:
        rows, cols = self.line_mask().shape
        r, j = self.world_xy_to_mask_idx(x, y)
        if r < 0 or r >= rows or j < 0 or j >= cols:
            return False
        return bool(self.line_mask()[r, j])

    # -- collisions / raycast

    def point_in_obstacle(self, x: float, y: float) -> bool:
        for c in self.circle_obstacles:
            if (x - c.cx) ** 2 + (y - c.cy) ** 2 <= c.r ** 2:
                return True
        for r in self.rect_obstacles:
            if abs(x - r.cx) <= r.half_w and abs(y - r.cy) <= r.half_h:
                return True
        return False

    def point_in_bounds(self, x: float, y: float, margin: float = 0.0) -> bool:
        return (
            margin <= x <= self.width_m - margin
            and margin <= y <= self.height_m - margin
        )

    def raycast(self, x0: float, y0: float, theta: float,
                max_range_m: float = 3.0,
                step_m: float = 0.005) -> float:
        """March a ray; return first hit distance in metres or max_range_m if clear."""
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        steps = int(max_range_m / step_m)
        for i in range(1, steps + 1):
            d = i * step_m
            x = x0 + d * cos_t
            y = y0 + d * sin_t
            if not self.point_in_bounds(x, y):
                return d
            if self.point_in_obstacle(x, y):
                return d
            for ball in self.balls:
                if (x - ball.cx) ** 2 + (y - ball.cy) ** 2 <= ball.r ** 2:
                    return d
        return max_range_m
