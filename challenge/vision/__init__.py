"""Vision pipelines used by the mission."""

from .redball import RedBallDetection, detect_red_ball

__all__ = ["RedBallDetection", "detect_red_ball"]
