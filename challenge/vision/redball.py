"""Red-ball detector lifted from `Code/Client/Main.py:block_detect`.

Pure function: takes a BGR ndarray, returns an optional detection. Two HSV
ranges cover red wrap-around at 0° and 180°. No GUI side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np


@dataclass
class RedBallDetection:
    center_xy: Tuple[int, int]
    radius_px: float
    distance_cm: float       # 1660 / (2 * radius_px), same heuristic as vendor
    image_size: Tuple[int, int]


_DEFAULT_LOW_A = (0, 120, 70)
_DEFAULT_HIGH_A = (10, 255, 255)
_DEFAULT_LOW_B = (170, 120, 70)
_DEFAULT_HIGH_B = (180, 255, 255)


def detect_red_ball(
    frame_bgr: np.ndarray,
    *,
    hsv_low_a: Tuple[int, int, int] = _DEFAULT_LOW_A,
    hsv_high_a: Tuple[int, int, int] = _DEFAULT_HIGH_A,
    hsv_low_b: Tuple[int, int, int] = _DEFAULT_LOW_B,
    hsv_high_b: Tuple[int, int, int] = _DEFAULT_HIGH_B,
    min_radius_px: float = 6.0,
) -> Optional[RedBallDetection]:
    if frame_bgr is None or frame_bgr.size == 0:
        return None

    h, w = frame_bgr.shape[:2]
    blurred = cv2.GaussianBlur(frame_bgr, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    mask_a = cv2.inRange(hsv, np.array(hsv_low_a), np.array(hsv_high_a))
    mask_b = cv2.inRange(hsv, np.array(hsv_low_b), np.array(hsv_high_b))
    mask = cv2.bitwise_or(mask_a, mask_b)

    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) <= 0:
        return None

    (cx, cy), radius = cv2.minEnclosingCircle(largest)
    if radius < min_radius_px:
        return None

    distance_cm = 1660.0 / max(2.0 * radius, 1.0)
    return RedBallDetection(
        center_xy=(int(round(cx)), int(round(cy))),
        radius_px=float(radius),
        distance_cm=float(distance_cm),
        image_size=(w, h),
    )


__all__ = ["RedBallDetection", "detect_red_ball"]
