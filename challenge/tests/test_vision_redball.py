import cv2
import numpy as np

from challenge.vision.redball import detect_red_ball


def test_detect_red_ball_from_synthetic_frame():
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    cv2.circle(frame, (90, 55), 18, (0, 0, 255), thickness=-1)

    detection = detect_red_ball(frame, min_radius_px=8)

    assert detection is not None
    assert detection.center_xy[0] == 90
    assert detection.center_xy[1] == 55
    assert 16 <= detection.radius_px <= 20
    assert detection.image_size == (160, 120)


def test_detect_red_ball_ignores_green_disk():
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    cv2.circle(frame, (80, 60), 22, (0, 255, 0), thickness=-1)

    assert detect_red_ball(frame) is None
