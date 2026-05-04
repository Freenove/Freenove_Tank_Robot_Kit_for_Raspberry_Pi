"""Mission parameter tuning helpers and deterministic simulator evaluation."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from challenge.mission import MissionConfig
from challenge.sim.arena import CircleObstacle
from challenge.sim.runner import SimRunner


@dataclass(frozen=True)
class ParamSpec:
    name: str
    low: float
    high: float
    kind: str = "float"


PARAM_SPECS: tuple[ParamSpec, ...] = (
    ParamSpec("obstacle_distance_cm", 10.0, 30.0),
    ParamSpec("pickup_distance_cm", 6.0, 24.0),
    ParamSpec("line_crawl_speed", 160.0, 700.0, "int"),
    ParamSpec("avoid_backup_speed", -1800.0, -700.0, "int"),
    ParamSpec("avoid_backup_s", 0.12, 0.65),
    ParamSpec("avoid_turn_left_speed", -1700.0, -500.0, "int"),
    ParamSpec("avoid_turn_right_speed", 500.0, 1700.0, "int"),
    ParamSpec("avoid_turn_s", 0.15, 0.80),
    ParamSpec("avoid_bypass_speed", 500.0, 1400.0, "int"),
    ParamSpec("avoid_bypass_s", 0.18, 0.95),
    ParamSpec("avoid_return_turn_s", 0.12, 0.70),
    ParamSpec("heading_tolerance_rad", 0.15, 0.55),
    ParamSpec("seek_lock_frames", 2.0, 6.0, "int"),
    ParamSpec("seek_lost_frames", 4.0, 14.0, "int"),
    ParamSpec("seek_approach_radius_px", 18.0, 70.0, "int"),
    ParamSpec("seek_forward_duty", 450.0, 1300.0, "int"),
    ParamSpec("seek_steer_kp", 0.35, 2.2),
    ParamSpec("seek_commit_center_px", 45.0, 150.0, "int"),
    ParamSpec("seek_commit_min_radius_px", 5.0, 24.0, "int"),
    ParamSpec("seek_commit_max_distance_cm", 35.0, 130.0),
    ParamSpec("seek_distance_agree_ratio", 0.25, 1.2),
    ParamSpec("seek_max_s", 2.0, 9.0),
    ParamSpec("seek_failed_cooldown_s", 0.5, 5.0),
    ParamSpec("avoid_cooldown_s", 0.2, 3.0),
    ParamSpec("line_recovery_cooldown_s", 0.2, 3.0),
    ParamSpec("spiral_search_budget_s", 1.0, 7.0),
)


def default_param_vector(config: MissionConfig | None = None) -> np.ndarray:
    config = config or MissionConfig()
    values = []
    for spec in PARAM_SPECS:
        value = float(getattr(config, spec.name))
        values.append(_to_unit(value, spec.low, spec.high))
    return np.asarray(values, dtype=np.float64)


def vector_to_params(vector: np.ndarray) -> dict[str, float | int]:
    clipped = np.clip(np.asarray(vector, dtype=np.float64), -1.0, 1.0)
    params: dict[str, float | int] = {}
    for value, spec in zip(clipped, PARAM_SPECS):
        raw = _from_unit(float(value), spec.low, spec.high)
        if spec.kind == "int":
            params[spec.name] = int(round(raw))
        else:
            params[spec.name] = round(float(raw), 6)
    return params


def apply_params(config: MissionConfig, params: dict[str, Any]) -> MissionConfig:
    for spec in PARAM_SPECS:
        if spec.name not in params:
            continue
        value = params[spec.name]
        if spec.kind == "int":
            value = int(value)
        else:
            value = float(value)
        setattr(config, spec.name, value)
    return config


def load_params(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if "params" in payload and isinstance(payload["params"], dict):
        return payload["params"]
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"invalid params file: {path}")


def save_params(path: str | Path, params: dict[str, Any], metadata: dict[str, Any] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "params": params,
        "metadata": metadata or {},
        "specs": [asdict(spec) for spec in PARAM_SPECS],
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


@dataclass
class EvalResult:
    scenario: str
    seed: int
    score: float
    outcome: str
    failure_reason: str
    ticks: int
    state: str
    carrying: int
    balls_remaining: int
    home_m: float
    watchdog_resets: int
    state_switches: int
    line_lost_ticks: int
    false_seek_exits: int
    line_points: int
    obstacle_points: int
    ball_points: int


def evaluate_params(
    params: dict[str, Any],
    *,
    scenarios: list[str] | tuple[str, ...],
    seeds: list[int] | tuple[int, ...],
    max_ticks: int = 500,
    domain_randomization: bool = True,
) -> tuple[float, list[EvalResult]]:
    results: list[EvalResult] = []
    for scenario in scenarios:
        for seed in seeds:
            result = evaluate_one(
                params,
                scenario=scenario,
                seed=int(seed),
                max_ticks=max_ticks,
                domain_randomization=domain_randomization,
            )
            results.append(result)
    if not results:
        return -1e9, []
    return float(sum(item.score for item in results) / len(results)), results


def evaluate_one(
    params: dict[str, Any],
    *,
    scenario: str,
    seed: int,
    max_ticks: int = 500,
    domain_randomization: bool = True,
) -> EvalResult:
    config = apply_params(MissionConfig(use_vision=True), params)
    config.vision_every_n_ticks = 1
    runner = SimRunner(scenario, seed=seed, config=config, use_vision=True)
    try:
        if domain_randomization:
            _randomize_world(runner, seed)

        for _ in range(max_ticks):
            runner.tick()
            status = _fast_status(runner)
            if _is_terminal_success(runner, status):
                break

        status = _fast_status(runner)
        balls_remaining = len(runner.world.arena.balls)
        score = _score_rollout(runner, status, max_ticks=max_ticks)
        outcome, failure_reason = _diagnose_rollout(runner, status)
        return EvalResult(
            scenario=scenario,
            seed=seed,
            score=score,
            outcome=outcome,
            failure_reason=failure_reason,
            ticks=runner.world.tick_count,
            state=str(status["state"]),
            carrying=int(status["carrying"]),
            balls_remaining=balls_remaining,
            home_m=float(status["home_m"]),
            watchdog_resets=int(status["watchdog_resets"]),
            state_switches=int(status["state_switches"]),
            line_lost_ticks=int(status["line_lost_ticks"]),
            false_seek_exits=int(status["false_seek_exits"]),
            line_points=len(runner.mission.line_memory),
            obstacle_points=len(runner.mission.obstacle_memory),
            ball_points=len(runner.mission.ball_memory),
        )
    finally:
        runner.close()


def _score_rollout(runner: SimRunner, status: dict[str, Any], *, max_ticks: int) -> float:
    score = 0.0
    balls_remaining = len(runner.world.arena.balls)
    carrying = int(status["carrying"])
    state = str(status["state"])
    home_m = float(status["home_m"])
    ticks = max(1, runner.world.tick_count)

    if runner.mission.line_memory:
        score += min(200.0, len(runner.mission.line_memory) * 1.5)
    score += max(0.0, 120.0 - home_m * 40.0)
    score += max(0.0, 90.0 * (1.0 - ticks / max(1, max_ticks)))

    if runner.mission.obstacle_memory:
        score += 35.0
    if runner.mission.ball_memory:
        score += 120.0
    touched_ball = bool(runner.mission.ball_memory or runner.world.carrying_ball or carrying)
    if balls_remaining == 0 or touched_ball:
        score += 350.0
    if carrying and home_m < runner.config.home_radius_m * 1.5:
        score += 220.0
    if not touched_ball and balls_remaining > 0:
        score -= 140.0
    if state == "follow_line" and touched_ball and not carrying and home_m <= runner.config.home_radius_m * 1.5:
        score += 180.0

    score -= int(status["watchdog_resets"]) * 180.0
    score -= int(status["false_seek_exits"]) * 90.0
    score -= int(status["line_lost_ticks"]) * 1.5
    score -= max(0, int(status["state_switches"]) - 18) * 7.0
    return float(score)


def _diagnose_rollout(runner: SimRunner, status: dict[str, Any]) -> tuple[str, str]:
    carrying = int(status["carrying"])
    state = str(status["state"])
    home_m = float(status["home_m"])
    balls_remaining = len(runner.world.arena.balls)
    watchdog = int(status["watchdog_resets"])
    false_seek = int(status["false_seek_exits"])

    if balls_remaining == 0 and not carrying and state == "follow_line" and home_m <= runner.config.home_radius_m * 1.5:
        return "success", "ok"
    if carrying and home_m > runner.config.home_radius_m * 1.5:
        return "carried_not_returned", "ball_not_returned"
    if carrying and state != "follow_line":
        return "carried_stuck", f"state_{state}"
    if false_seek > 0:
        return "failed_seek", "false_seek_exit"
    if watchdog > 0:
        return "failed_watchdog", "watchdog_reset"
    if balls_remaining > 0 and runner.mission.ball_memory:
        return "picked_no_finish", "mission_incomplete"
    if balls_remaining > 0:
        return "no_pickup", "ball_not_picked"
    return "incomplete", state


def _fast_status(runner: SimRunner) -> dict[str, Any]:
    mission = runner.mission
    return {
        "state": mission.state.value,
        "home_m": math.hypot(
            mission.home_pose.x_m - mission.pose.x_m,
            mission.home_pose.y_m - mission.pose.y_m,
        ),
        "carrying": int(mission.is_carrying_ball()),
        "watchdog_resets": mission._watchdog_resets,
        "state_switches": mission._state_switches,
        "line_lost_ticks": mission._line_lost_ticks,
        "false_seek_exits": mission._false_seek_exits,
    }


def _is_terminal_success(runner: SimRunner, status: dict[str, Any]) -> bool:
    if not runner.mission.ball_memory:
        return False
    if int(status["carrying"]):
        return False
    return str(status["state"]) == "follow_line" and float(status["home_m"]) <= runner.config.home_radius_m * 1.5


def _randomize_world(runner: SimRunner, seed: int) -> None:
    rng = np.random.default_rng(seed + 101)
    arena = runner.world.arena
    cfg = runner.world.config
    cfg.duty_to_mps *= float(rng.uniform(0.82, 1.18))
    cfg.wheel_base_m *= float(rng.uniform(0.90, 1.10))
    cfg.motor_tau_s *= float(rng.uniform(0.70, 1.45))
    cfg.motor_dead_zone_duty = int(round(cfg.motor_dead_zone_duty * float(rng.uniform(0.70, 1.45))))
    cfg.slip_sigma_per_duty += float(rng.uniform(0.0, 0.0016))
    cfg.heading_slip_sigma_rad += float(rng.uniform(0.0, 0.035))
    cfg.ultrasonic_noise_cm += float(rng.uniform(0.0, 2.0))
    cfg.ultrasonic_miss_prob = min(0.18, cfg.ultrasonic_miss_prob + float(rng.uniform(0.0, 0.055)))
    cfg.ir_flicker_prob = min(0.12, cfg.ir_flicker_prob + float(rng.uniform(0.0, 0.045)))

    for line in arena.line_polylines:
        line.width_m = float(np.clip(line.width_m * rng.uniform(0.75, 1.35), 0.025, 0.07))
    arena._line_mask = None

    for ball in runner.world.arena.balls:
        ball.cx = _clamp(ball.cx + float(rng.uniform(-0.18, 0.18)), 0.25, arena.width_m - 0.25)
        ball.cy = _clamp(ball.cy + float(rng.uniform(-0.18, 0.18)), 0.25, arena.height_m - 0.25)
        ball.r = float(np.clip(ball.r * rng.uniform(0.85, 1.20), 0.03, 0.06))

    for obstacle in arena.circle_obstacles:
        obstacle.cx = _clamp(obstacle.cx + float(rng.uniform(-0.18, 0.18)), 0.35, arena.width_m - 0.35)
        obstacle.cy = _clamp(obstacle.cy + float(rng.uniform(-0.18, 0.18)), 0.35, arena.height_m - 0.35)
        obstacle.r = float(np.clip(obstacle.r * rng.uniform(0.75, 1.35), 0.07, 0.16))

    if rng.random() < 0.45:
        _add_plausible_extra_obstacle(runner, rng)

    pose = runner.world.pose
    pose.x_m = _clamp(pose.x_m + float(rng.uniform(-0.05, 0.08)), 0.12, arena.width_m - 0.12)
    pose.y_m = _clamp(pose.y_m + float(rng.uniform(-0.08, 0.08)), 0.12, arena.height_m - 0.12)
    pose.heading_rad += float(rng.uniform(-0.18, 0.18))
    runner.mission.pose.x_m = pose.x_m
    runner.mission.pose.y_m = pose.y_m
    runner.mission.pose.heading_rad = pose.heading_rad
    runner.mission.home_pose.x_m = pose.x_m
    runner.mission.home_pose.y_m = pose.y_m
    runner.mission.home_pose.heading_rad = pose.heading_rad
    runner.mission.line_graph.mark_home(pose.x_m, pose.y_m)

    # Ensure the ball remains plausible: reachable but not always dead-ahead.
    if runner.world.arena.balls:
        for ball in runner.world.arena.balls:
            if math.hypot(ball.cx - pose.x_m, ball.cy - pose.y_m) < 0.30:
                ball.cx = _clamp(ball.cx + 0.35, 0.4, arena.width_m - 0.4)
                ball.cy = _clamp(ball.cy + 0.10, 0.4, arena.height_m - 0.4)


def _add_plausible_extra_obstacle(runner: SimRunner, rng: np.random.Generator) -> None:
    arena = runner.world.arena
    if not arena.line_polylines:
        return
    line = arena.line_polylines[int(rng.integers(0, len(arena.line_polylines)))]
    if len(line.points_m) < 2:
        return

    segment_idx = int(rng.integers(0, len(line.points_m) - 1))
    x0, y0 = line.points_m[segment_idx]
    x1, y1 = line.points_m[segment_idx + 1]
    t = float(rng.uniform(0.25, 0.80))
    x = x0 + (x1 - x0) * t
    y = y0 + (y1 - y0) * t
    length = max(1e-6, math.hypot(x1 - x0, y1 - y0))
    nx = -(y1 - y0) / length
    ny = (x1 - x0) / length
    offset = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.08, 0.18))
    x = _clamp(x + nx * offset, 0.30, arena.width_m - 0.30)
    y = _clamp(y + ny * offset, 0.30, arena.height_m - 0.30)

    start_dist = math.hypot(x - runner.world.pose.x_m, y - runner.world.pose.y_m)
    if start_dist < 0.45:
        return
    for ball in arena.balls:
        if math.hypot(x - ball.cx, y - ball.cy) < 0.35:
            return
    arena.circle_obstacles.append(CircleObstacle(cx=x, cy=y, r=float(rng.uniform(0.07, 0.13))))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _to_unit(value: float, low: float, high: float) -> float:
    if math.isclose(high, low):
        return 0.0
    return 2.0 * (value - low) / (high - low) - 1.0


def _from_unit(value: float, low: float, high: float) -> float:
    return low + (float(value) + 1.0) * 0.5 * (high - low)


__all__ = [
    "EvalResult",
    "PARAM_SPECS",
    "apply_params",
    "default_param_vector",
    "evaluate_one",
    "evaluate_params",
    "load_params",
    "save_params",
    "vector_to_params",
]
