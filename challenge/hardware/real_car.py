"""Adapter over the vendor `Code/Server/car.py:Car`.

This is the ONLY module allowed to import from `Code/Server/*`. It loads the
vendor `Car` class via importlib (the same dance `challenge/main.py` used to
do inline) and wraps it so the camera exposes `get_frame_bgr()` for parity
with `MockCar`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SERVER_DIR = _REPO_ROOT / "Code" / "Server"


def _load_vendor_car_class():
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    if str(_SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(_SERVER_DIR))

    car_path = _SERVER_DIR / "car.py"
    spec = importlib.util.spec_from_file_location("vendor_car", car_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load vendor car module from {car_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Car


class _CameraAdapter:
    """Wraps `Code/Server/camera.py:Camera` and decodes JPEG → BGR ndarray."""

    def __init__(self) -> None:
        from camera import Camera  # type: ignore[import-not-found]

        self._camera = Camera(stream_size=(400, 300))
        self._streaming = False

    def _ensure_stream(self) -> None:
        if not self._streaming:
            self._camera.start_stream()
            self._streaming = True

    def get_frame_bgr(self) -> np.ndarray | None:
        import cv2

        self._ensure_stream()
        jpeg = self._camera.get_frame()
        if jpeg is None:
            return None
        arr = np.frombuffer(jpeg, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    def close(self) -> None:
        try:
            if self._streaming:
                self._camera.stop_stream()
        finally:
            self._camera.close()


class RealCar:
    """Real-hardware backend. Only constructible on a Raspberry Pi."""

    def __init__(self) -> None:
        Car = _load_vendor_car_class()
        self._car = Car()

        self.motor = self._car.motor
        self.sonic = self._car.sonic
        self.infrared = self._car.infrared
        self.servo = self._car.servo

        self.camera: _CameraAdapter | None = None
        try:
            self.camera = _CameraAdapter()
        except Exception as exc:  # camera is optional for non-vision missions
            print(f"[real_car] camera unavailable: {exc}")
            self.camera = _NullCamera()

    @property
    def infrared_run_stop(self) -> bool:
        return getattr(self._car, "infrared_run_stop", False)

    @infrared_run_stop.setter
    def infrared_run_stop(self, value: bool) -> None:
        self._car.infrared_run_stop = bool(value)

    def set_mode_clamp(self, mode: int) -> None:
        self._car.set_mode_clamp(mode)

    def get_mode_clamp(self) -> int:
        return self._car.get_mode_clamp()

    def mode_clamp(self, mode: int | None = None) -> None:
        self._car.mode_clamp(mode) if mode is not None else self._car.mode_clamp()

    def close(self) -> None:
        try:
            if self.camera is not None:
                self.camera.close()
        finally:
            self._car.close()


class _NullCamera:
    def get_frame_bgr(self) -> np.ndarray | None:
        return None

    def close(self) -> None:
        pass
