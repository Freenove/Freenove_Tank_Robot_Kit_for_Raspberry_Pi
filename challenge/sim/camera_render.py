"""Render the simulated first-person camera frame as a BGR ndarray.

Pseudo-3D pinhole projection. Uses numpy + OpenCV draw primitives only —
this module does not depend on pygame, so it works in headless tests too.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    from .arena import Arena
    from .world import Pose2D, SimConfig


# Camera intrinsics (Freenove camera ≈ 62° HFOV at 320x240).
IMG_W = 320
IMG_H = 240
HFOV_DEG = 62.0
CAM_HEIGHT_M = 0.07            # camera height above ground
CAM_FORWARD_OFFSET_M = 0.10    # camera mounted ahead of robot pose

_FOCAL_PX = (IMG_W / 2.0) / math.tan(math.radians(HFOV_DEG / 2.0))


def render_camera_bgr(arena: "Arena", pose: "Pose2D",
                      config: "SimConfig") -> np.ndarray:
    img = _draw_ground_and_horizon()
    cos_h = math.cos(pose.heading_rad)
    sin_h = math.sin(pose.heading_rad)

    cam_x = pose.x_m + CAM_FORWARD_OFFSET_M * cos_h
    cam_y = pose.y_m + CAM_FORWARD_OFFSET_M * sin_h

    # Render obstacles first (so balls draw on top if closer).
    drawables: list[tuple[float, callable]] = []

    for c in arena.circle_obstacles:
        d = _hypot(c.cx - cam_x, c.cy - cam_y)
        drawables.append((d, lambda im, c=c: _draw_cone(
            im, cam_x, cam_y, pose.heading_rad, c.cx, c.cy, c.r,
            color=(40, 90, 220),  # orange-ish
        )))

    for r in arena.rect_obstacles:
        d = _hypot(r.cx - cam_x, r.cy - cam_y)
        drawables.append((d, lambda im, r=r: _draw_box(
            im, cam_x, cam_y, pose.heading_rad, r.cx, r.cy, r.half_w, r.half_h,
            color=(120, 120, 120),
        )))

    for ball in arena.balls:
        d = _hypot(ball.cx - cam_x, ball.cy - cam_y)
        drawables.append((d, lambda im, ball=ball: _draw_ball(
            im, cam_x, cam_y, pose.heading_rad, ball.cx, ball.cy, ball.r,
            ball.color_bgr,
        )))

    # Sort far-to-near so closer things draw on top.
    drawables.sort(key=lambda t: -t[0])
    for _, fn in drawables:
        fn(img)

    if getattr(arena, "world", None) is not None:
        world = arena.world
        if world.carrying_ball and not world.carry_pose_is_raised():
            _draw_arm_occlusion(img)

    return img


def _draw_ground_and_horizon() -> np.ndarray:
    img = np.zeros((IMG_H, IMG_W, 3), dtype=np.uint8)
    # Sky-ish top band, ground gradient bottom.
    horizon_y = IMG_H // 2
    img[:horizon_y] = (180, 180, 180)            # neutral grey "wall"
    for y in range(horizon_y, IMG_H):
        t = (y - horizon_y) / max(1, IMG_H - horizon_y - 1)
        shade = int(110 + 60 * t)                # darker far → lighter near
        img[y] = (shade, shade, shade)
    return img


def _project(cam_x: float, cam_y: float, heading: float,
             world_x: float, world_y: float, height_m: float) -> Optional[Tuple[float, float, float]]:
    """Project a world point at (world_x, world_y, height_m) into image coords.

    Returns (u_px, v_px, depth_m) or None if behind the camera.
    """
    dx = world_x - cam_x
    dy = world_y - cam_y
    cos_h = math.cos(-heading)
    sin_h = math.sin(-heading)
    forward = dx * math.cos(heading) + dy * math.sin(heading)
    right = -dx * math.sin(heading) + dy * math.cos(heading)

    if forward <= 0.05:
        return None

    u = IMG_W / 2.0 - (right * _FOCAL_PX / forward)
    v = IMG_H / 2.0 - ((height_m - CAM_HEIGHT_M) * _FOCAL_PX / forward)
    return u, v, forward


def _draw_ball(img: np.ndarray, cam_x: float, cam_y: float, heading: float,
               wx: float, wy: float, r_m: float,
               color_bgr: Tuple[int, int, int]) -> None:
    proj = _project(cam_x, cam_y, heading, wx, wy, height_m=r_m)
    if proj is None:
        return
    u, v, depth = proj
    radius_px = max(2.0, r_m * _FOCAL_PX / depth)
    _filled_circle(img, int(round(u)), int(round(v)), int(round(radius_px)), color_bgr)


def _draw_cone(img: np.ndarray, cam_x: float, cam_y: float, heading: float,
               wx: float, wy: float, r_m: float, color: Tuple[int, int, int]) -> None:
    base = _project(cam_x, cam_y, heading, wx, wy, height_m=0.0)
    apex = _project(cam_x, cam_y, heading, wx, wy, height_m=0.18)
    if base is None or apex is None:
        return
    bu, bv, depth = base
    au, av, _ = apex
    width_px = max(2.0, r_m * _FOCAL_PX / depth)
    pts = np.array([
        [bu - width_px, bv],
        [bu + width_px, bv],
        [au, av],
    ], dtype=np.int32)
    try:
        import cv2

        cv2.fillPoly(img, [pts], color)
    except Exception:
        pass


def _draw_box(img: np.ndarray, cam_x: float, cam_y: float, heading: float,
              wx: float, wy: float, hw: float, hh: float,
              color: Tuple[int, int, int]) -> None:
    corners = [
        (wx - hw, wy - hh),
        (wx + hw, wy - hh),
        (wx + hw, wy + hh),
        (wx - hw, wy + hh),
    ]
    projected = []
    for cx, cy in corners:
        bot = _project(cam_x, cam_y, heading, cx, cy, height_m=0.0)
        top = _project(cam_x, cam_y, heading, cx, cy, height_m=0.15)
        if bot is None or top is None:
            return
        projected.append((bot, top))
    try:
        import cv2

        for (bu, bv, _), (tu, tv, _) in projected:
            cv2.line(img, (int(bu), int(bv)), (int(tu), int(tv)), color, 1)
        # Connect tops front-to-back
        for i in range(4):
            (tu0, tv0), (tu1, tv1) = projected[i][1], projected[(i + 1) % 4][1]
            cv2.line(img, (int(tu0[0]), int(tu0[1])), (int(tu1[0]), int(tu1[1])), color, 1)
    except Exception:
        pass


def _filled_circle(img: np.ndarray, cx: int, cy: int, r: int,
                   color_bgr: Tuple[int, int, int]) -> None:
    try:
        import cv2

        cv2.circle(img, (cx, cy), r, color_bgr, thickness=-1)
        cv2.circle(img, (cx, cy), r, (255, 255, 255), thickness=1)
    except Exception:
        h, w = img.shape[:2]
        for y in range(max(0, cy - r), min(h, cy + r + 1)):
            for x in range(max(0, cx - r), min(w, cx + r + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img[y, x] = color_bgr


def _draw_arm_occlusion(img: np.ndarray) -> None:
    try:
        import cv2

        overlay = img.copy()
        cv2.rectangle(overlay, (90, 110), (230, IMG_H - 4), (20, 20, 20), thickness=-1)
        cv2.addWeighted(overlay, 0.35, img, 0.65, 0, dst=img)
    except Exception:
        img[110:IMG_H, 90:230] = (24, 24, 24)


def _hypot(a: float, b: float) -> float:
    return math.hypot(a, b)
