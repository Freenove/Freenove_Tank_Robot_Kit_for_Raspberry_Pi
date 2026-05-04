import math
import time
from dataclasses import dataclass
from enum import Enum
from statistics import median
from typing import Callable


@dataclass
class MissionConfig:
    """Single mission configuration object for challenge runtime."""

    loop_sleep_s: float = 0.05
    obstacle_distance_cm: float = 18.0
    pickup_distance_cm: float = 15.0
    home_radius_m: float = 0.22

    # Line-follow and fallback behavior.
    line_code_zero_is_center: bool = True
    line_crawl_speed: int = 260

    # Avoidance motion profile.
    avoid_backup_speed: int = -1200
    avoid_backup_s: float = 0.30
    avoid_turn_left_speed: int = -1000
    avoid_turn_right_speed: int = 1000
    avoid_turn_s: float = 0.34
    avoid_bypass_speed: int = 900
    avoid_bypass_s: float = 0.42
    avoid_return_turn_s: float = 0.28
    avoid_settle_s: float = 0.12

    # Clamp timing.
    pre_open_before_pick: bool = True
    pick_timeout_s: float = 6.0
    drop_timeout_s: float = 4.0
    raise_arm_after_pick: bool = True
    carry_servo0_angle: int = 150
    carry_servo1_angle: int = 140
    carry_pose_settle_s: float = 0.15

    # Dead-reckoning constants for return-to-start.
    duty_to_mps: float = 0.00022
    wheel_base_m: float = 0.16
    heading_tolerance_rad: float = 0.28
    return_home_speed: int = 950
    return_home_slow_speed: int = 700
    return_home_slow_radius_m: float = 0.55
    return_home_use_graph: bool = False

    # Vision (red-ball seek) — gated; falls back to legacy path when disabled.
    use_vision: bool = False
    vision_every_n_ticks: int = 3
    seek_lock_frames: int = 3
    seek_lost_frames: int = 8
    seek_approach_radius_px: int = 30
    seek_forward_duty: int = 900
    seek_steer_kp: float = 1.0
    seek_steer_kd: float = 0.0025
    seek_commit_center_px: int = 110
    seek_commit_min_radius_px: int = 8
    seek_commit_max_distance_cm: float = 85.0
    seek_distance_agree_ratio: float = 0.65
    seek_max_s: float = 5.0
    seek_failed_cooldown_s: float = 2.0
    avoid_cooldown_s: float = 1.0
    line_recovery_cooldown_s: float = 1.0

    # Robustness
    sonic_median_window: int = 3
    ir_majority_window: int = 3
    state_timeout_s: float = 8.0
    spiral_search_budget_s: float = 4.0


class MissionState(Enum):
    FOLLOW_LINE = "follow_line"
    SEEK_BALL = "seek_ball"
    AVOID_OBSTACLE = "avoid_obstacle"
    PICK_BALL = "pick_ball"
    RETURN_HOME = "return_home"
    DROP_BALL = "drop_ball"


@dataclass
class Pose2D:
    x_m: float = 0.0
    y_m: float = 0.0
    heading_rad: float = 0.0


@dataclass
class MapPoint:
    x_m: float
    y_m: float
    kind: str


@dataclass
class GraphNode:
    x_m: float
    y_m: float


class LineGraph:
    def __init__(
        self,
        merge_distance_m: float = 0.06,
        obstacle_block_radius_m: float = 0.12,
    ) -> None:
        self.merge_distance_m = merge_distance_m
        self.obstacle_block_radius_m = obstacle_block_radius_m
        self.nodes: list[GraphNode] = []
        self.edges: dict[int, dict[int, float]] = {}
        self.last_node: int | None = None
        self.home_node: int | None = None
        self.obstacle_nodes: set[int] = set()

    def mark_home(self, x_m: float, y_m: float) -> None:
        self.home_node = self._find_or_add_node(x_m, y_m)

    def add_line_point(self, x_m: float, y_m: float) -> int:
        node_idx = self._find_or_add_node(x_m, y_m)
        if self.last_node is not None and self.last_node != node_idx:
            self._add_edge(self.last_node, node_idx)
        self.last_node = node_idx
        return node_idx

    def add_obstacle(self, x_m: float, y_m: float) -> None:
        node_idx = self._find_or_add_node(x_m, y_m)
        self.obstacle_nodes.add(node_idx)

    def find_nearest_node(self, x_m: float, y_m: float) -> int | None:
        best_idx = None
        best_dist = None
        for idx, node in enumerate(self.nodes):
            dist = math.hypot(node.x_m - x_m, node.y_m - y_m)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = idx
        return best_idx

    def shortest_path(self, start: int, goal: int) -> list[int]:
        if start == goal:
            return [start]
        if start in self.obstacle_nodes or goal in self.obstacle_nodes:
            return []

        unvisited: set[int] = set(range(len(self.nodes)))
        dist: dict[int, float] = {start: 0.0}
        prev: dict[int, int] = {}

        while unvisited:
            current = None
            current_dist = None
            for idx in unvisited:
                if idx not in dist:
                    continue
                if current_dist is None or dist[idx] < current_dist:
                    current = idx
                    current_dist = dist[idx]

            if current is None:
                break
            if current == goal:
                break

            unvisited.remove(current)
            for neighbor, cost in self.edges.get(current, {}).items():
                if neighbor not in unvisited:
                    continue
                if neighbor in self.obstacle_nodes:
                    continue
                candidate = dist[current] + cost
                if candidate < dist.get(neighbor, float("inf")):
                    dist[neighbor] = candidate
                    prev[neighbor] = current

        if goal not in dist:
            return []

        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path

    def _find_or_add_node(self, x_m: float, y_m: float) -> int:
        for idx, node in enumerate(self.nodes):
            if math.hypot(node.x_m - x_m, node.y_m - y_m) <= self.merge_distance_m:
                return idx
        idx = len(self.nodes)
        self.nodes.append(GraphNode(x_m, y_m))
        self.edges[idx] = {}
        return idx

    def _add_edge(self, a: int, b: int) -> None:
        node_a = self.nodes[a]
        node_b = self.nodes[b]
        cost = math.hypot(node_b.x_m - node_a.x_m, node_b.y_m - node_a.y_m)
        self.edges[a][b] = cost
        self.edges[b][a] = cost


class ChallengeMission:
    """Simple mission that uses only car.py capabilities."""

    def __init__(
        self,
        car,
        config: MissionConfig,
        *,
        clock: Callable[[], float] | None = None,
    ):
        self.car = car
        self.config = config
        self._clock = clock
        self.state = MissionState.FOLLOW_LINE
        self._carrying_ball = False

        self.pose = Pose2D()
        self.home_pose = Pose2D()

        self._cmd_left = 0
        self._cmd_right = 0
        self._last_motion_ts = self._now()

        self._avoid_phase = ""
        self._avoid_phase_end_ts = 0.0
        self._avoid_resume_state = MissionState.FOLLOW_LINE

        # Permanent memory for observed entities.
        self.obstacle_memory: list[MapPoint] = []
        self.ball_memory: list[MapPoint] = []
        self.line_memory: list[MapPoint] = []
        self.line_graph = LineGraph()
        self._return_path_nodes: list[int] = []
        self._return_path_idx = 0

        # Manual (WASD) non-blocking override state.
        self._manual_override_end_ts: float = 0.0

        # Vision state.
        self._vision_pid = None
        self._seek_lock_count = 0
        self._seek_miss_count = 0
        self._last_detection = None  # type: ignore[var-annotated]
        self._tick_index = 0

        # Robustness state.
        self._sonic_history: list[float] = []
        self._ir_history: list[int] = []
        self._state_entry_ts: float = self._now()
        self._spiral_entry_ts: float = 0.0
        self._spiral_phase: int = 0  # 0 not active, 1 left, 2 right, 3 done
        self._watchdog_pose = Pose2D()
        self._watchdog_distance_cm = -1.0
        self._watchdog_ir = 7
        self._watchdog_resets = 0
        self._last_avoid_end_ts = -999.0
        self._last_line_recovery_ts = -999.0
        self._seek_cooldown_until_ts = -999.0
        self._state_switches = 0
        self._line_lost_ticks = 0
        self._false_seek_exits = 0
        self._last_state_reason = "follow_line"

    def step(self) -> None:
        self._integrate_pose()
        self._tick_index += 1

        # If a manual override is active, skip autonomous behaviors.
        if self._now() < self._manual_override_end_ts:
            return
        distance = self._distance_cm()

        # Vision: pull a frame every N ticks while in states where it matters.
        detection = self._last_detection
        if self.config.use_vision and self._tick_index % max(1, self.config.vision_every_n_ticks) == 0:
            detection = self._poll_vision()
        self._last_detection = detection

        if self._apply_watchdog(distance):
            return

        if self.state == MissionState.AVOID_OBSTACLE:
            self._step_avoidance()
            return
        if self.state == MissionState.PICK_BALL:
            self._pick_ball()
            return
        if self.state == MissionState.DROP_BALL:
            self._drop_ball()
            return
        if self.state == MissionState.SEEK_BALL:
            self._seek_ball_step(distance, detection)
            return

        if self._is_obstacle(distance):
            self._remember_obstacle(distance)
            self._start_avoidance(resume_state=self.state)
            self._step_avoidance()
            return

        if self.state == MissionState.RETURN_HOME:
            self._return_home_step()
            return

        # FOLLOW_LINE: vision takes precedence when it has a confident lock.
        if self.config.use_vision and not self._carrying_ball:
            ir = self._read_ir()
            if self._has_seek_lock() and self._should_seek_ball(distance, detection, ir):
                self._enter_state(MissionState.SEEK_BALL, reason="seek_lock")
                self._seek_ball_step(distance, detection)
                return

        if self._is_pickup_distance(distance):
            self._remember_ball_here()
            self._enter_state(MissionState.PICK_BALL, reason="pickup_range")
            return

        self._follow_line_continuous()

    def reset_home_anchor(self) -> None:
        self.home_pose = Pose2D(self.pose.x_m, self.pose.y_m, self.pose.heading_rad)
        self.line_graph.mark_home(self.home_pose.x_m, self.home_pose.y_m)

    def is_carrying_ball(self) -> bool:
        return self._carrying_ball

    def set_manual_carrying_state(self, carrying: bool) -> None:
        self._carrying_ball = carrying
        self._enter_state(
            MissionState.RETURN_HOME if carrying else MissionState.FOLLOW_LINE,
            reason="manual_carry" if carrying else "manual_release",
        )

    def get_status(self) -> dict[str, float | int | str]:
        return {
            "state": self.state.value,
            "state_reason": self._last_state_reason,
            "state_age_s": round(max(0.0, self._now() - self._state_entry_ts), 3),
            "x_m": self.pose.x_m,
            "y_m": self.pose.y_m,
            "heading_deg": math.degrees(self.pose.heading_rad),
            "home_m": self._distance_to_home(),
            "distance_cm": self._distance_cm(),
            "ir": self._read_ir(),
            "carrying": int(self._carrying_ball),
            "balls": len(self.ball_memory),
            "obstacles": len(self.obstacle_memory),
            "route_nodes": len(self._return_path_nodes),
            "watchdog_resets": self._watchdog_resets,
            "state_switches": self._state_switches,
            "line_lost_ticks": self._line_lost_ticks,
            "false_seek_exits": self._false_seek_exits,
        }

    def start_manual_drive(self, key: str, duration_s: float) -> bool:
        """Start a non-blocking manual drive override for `duration_s` seconds.

        While active, autonomous behaviors are suspended and pose integration
        continues using the commanded wheel outputs.
        """
        now = self._now()
        if key == "w":
            self._drive(900, 900)
        elif key == "s":
            self._drive(-900, -900)
        elif key == "a":
            self._drive(-850, 850)
        elif key == "d":
            self._drive(850, -850)
        else:
            return False

        self._manual_override_end_ts = now + max(0.05, duration_s)
        return True

    def manual_pickup_toggle(self) -> None:
        if self._carrying_ball:
            self._drop_ball()
            return
        self._pick_ball()

    def _follow_line_continuous(self) -> None:
        ir = self._read_ir()
        if self._is_line_lost(ir):
            self._line_lost_search_step()
            return

        # Record line observations (debounced by checking we're actually on a line).
        try:
            self.line_memory.append(MapPoint(self.pose.x_m, self.pose.y_m, "line"))
            self.line_graph.add_line_point(self.pose.x_m, self.pose.y_m)
        except Exception:
            pass

        # Drive directly via the IR→duty mapping. Do NOT delegate to
        # `car.mode_infrared` — that method has its own auto-pickup loop that
        # fights the mission state machine on the real robot.
        left, right = self._infer_line_command(ir)
        self._drive(left, right)

    def _enter_state(self, state: MissionState, reason: str | None = None) -> None:
        if self.state == state:
            return
        self.state = state
        self._state_switches += 1
        self._state_entry_ts = self._now()
        self._last_state_reason = reason or state.value
        self._reset_watchdog_snapshot()
        if state != MissionState.SEEK_BALL:
            self._seek_miss_count = 0
            self._last_detection = None
        if state == MissionState.FOLLOW_LINE:
            self._return_path_nodes = []
            self._return_path_idx = 0
            self._spiral_phase = 0

    def _poll_vision(self):
        if self._carrying_ball:
            self._seek_lock_count = 0
            return None

        camera = getattr(self.car, "camera", None)
        if camera is None:
            self._record_vision_miss()
            return None

        try:
            frame = camera.get_frame_bgr()
        except Exception:
            self._record_vision_miss()
            return None

        if frame is None:
            self._record_vision_miss()
            return None

        try:
            from challenge.vision.redball import detect_red_ball

            detection = detect_red_ball(frame)
        except Exception:
            self._record_vision_miss()
            return None

        if detection is None:
            self._record_vision_miss()
            return None

        self._seek_lock_count += 1
        self._seek_miss_count = 0
        return detection

    def _record_vision_miss(self) -> None:
        self._seek_miss_count += 1
        if self.state != MissionState.SEEK_BALL:
            self._seek_lock_count = 0

    def _has_seek_lock(self) -> bool:
        return self._seek_lock_count >= max(1, self.config.seek_lock_frames)

    def _should_seek_ball(self, distance_cm: float, detection, ir: int) -> bool:
        detection = detection or self._last_detection
        if detection is None:
            return False
        now = self._now()
        if now < self._seek_cooldown_until_ts:
            return False
        if now - self._last_avoid_end_ts < self.config.avoid_cooldown_s:
            return False
        if now - self._last_line_recovery_ts < self.config.line_recovery_cooldown_s:
            return False
        if self._is_line_lost(ir):
            return False

        image_w, _ = detection.image_size
        center_error = abs(detection.center_xy[0] - image_w / 2.0)
        if center_error > self.config.seek_commit_center_px:
            return False
        if detection.radius_px < self.config.seek_commit_min_radius_px:
            return False
        if detection.distance_cm > self.config.seek_commit_max_distance_cm:
            return False
        if distance_cm > 0:
            agree_ratio = self.config.seek_distance_agree_ratio
            lower = detection.distance_cm * max(0.1, 1.0 - agree_ratio)
            upper = detection.distance_cm * (1.0 + agree_ratio)
            if not lower <= distance_cm <= upper:
                return False
        return True

    def _seek_ball_step(self, distance_cm: float, detection) -> None:
        if self._now() - self._state_entry_ts > self.config.seek_max_s:
            self._false_seek_exits += 1
            self._seek_lock_count = 0
            self._seek_cooldown_until_ts = self._now() + self.config.seek_failed_cooldown_s
            self._enter_state(MissionState.FOLLOW_LINE, reason="seek_timeout")
            return

        detection = detection or self._last_detection
        if detection is None:
            self._stop_drive()
            if self._seek_miss_count >= max(1, self.config.seek_lost_frames):
                self._false_seek_exits += 1
                self._seek_lock_count = 0
                self._seek_cooldown_until_ts = self._now() + self.config.seek_failed_cooldown_s
                self._enter_state(MissionState.FOLLOW_LINE, reason="seek_lost")
            return

        if (
            self._is_pickup_distance(distance_cm)
            and detection.radius_px >= self.config.seek_approach_radius_px
        ):
            self._remember_ball_here()
            self._enter_state(MissionState.PICK_BALL, reason="ball_close")
            return

        if self._vision_pid is None:
            from challenge.controllers.pid import Incremental_PID

            self._vision_pid = Incremental_PID(
                P=self.config.seek_steer_kp,
                I=0.0,
                D=self.config.seek_steer_kd,
            )

        image_w, _ = detection.image_size
        self._vision_pid.setPoint = image_w / 2.0
        steer = float(self._vision_pid.PID_compute(detection.center_xy[0]))
        steer = max(-1100.0, min(1100.0, steer * 10.0))

        base = self.config.seek_forward_duty
        left = int(max(-4095, min(4095, base + steer)))
        right = int(max(-4095, min(4095, base - steer)))
        self._drive(left, right)

    def _line_lost_search_step(self) -> None:
        self._line_lost_ticks += 1
        now = self._now()
        if self._spiral_phase == 0:
            self._spiral_entry_ts = now
            self._spiral_phase = 1

        elapsed = now - self._spiral_entry_ts
        if elapsed > self.config.spiral_search_budget_s:
            self._spiral_phase = 0
            self._last_line_recovery_ts = now
            self._drive(self.config.line_crawl_speed, self.config.line_crawl_speed)
            return

        phase_s = max(0.35, self.config.spiral_search_budget_s / 4.0)
        phase = int(elapsed / phase_s) % 4
        duty = max(300, self.config.line_crawl_speed)
        if phase == 0:
            self._drive(-duty, duty)
        elif phase == 1:
            self._drive(duty, duty)
        elif phase == 2:
            self._drive(duty, -duty)
        else:
            self._drive(duty, duty)

    def _reset_watchdog_snapshot(self) -> None:
        self._watchdog_pose = Pose2D(
            self.pose.x_m,
            self.pose.y_m,
            self.pose.heading_rad,
        )
        self._watchdog_distance_cm = self._sonic_history[-1] if self._sonic_history else -1.0
        self._watchdog_ir = self._ir_history[-1] if self._ir_history else 7

    def _apply_watchdog(self, distance_cm: float) -> bool:
        if self.state in (MissionState.FOLLOW_LINE, MissionState.PICK_BALL, MissionState.DROP_BALL):
            self._reset_watchdog_snapshot()
            return False

        timeout_s = max(0.0, self.config.state_timeout_s)
        if timeout_s <= 0.0:
            return False
        if self._now() - self._state_entry_ts <= timeout_s:
            return False

        pose_delta = math.hypot(
            self.pose.x_m - self._watchdog_pose.x_m,
            self.pose.y_m - self._watchdog_pose.y_m,
        )
        heading_delta = abs(self._normalize_angle(self.pose.heading_rad - self._watchdog_pose.heading_rad))
        current_ir = self._ir_history[-1] if self._ir_history else self._watchdog_ir
        distance_delta = (
            abs(distance_cm - self._watchdog_distance_cm)
            if distance_cm > 0 and self._watchdog_distance_cm > 0
            else 0.0
        )
        sensor_changed = current_ir != self._watchdog_ir or distance_delta > 4.0
        pose_changed = pose_delta > 0.03 or heading_delta > 0.20

        if pose_changed or sensor_changed:
            self._state_entry_ts = self._now()
            self._reset_watchdog_snapshot()
            return False

        self._stop_drive()
        self._return_path_nodes = []
        self._return_path_idx = 0
        self._avoid_phase = ""
        self._seek_lock_count = 0
        self._seek_miss_count = 0
        self._last_detection = None
        self._spiral_phase = 0
        self._watchdog_resets += 1
        self._enter_state(MissionState.FOLLOW_LINE, reason="watchdog_reset")
        return True

    def _return_home_step(self) -> None:
        if self._distance_to_home() <= self.config.home_radius_m:
            self._enter_state(MissionState.DROP_BALL, reason="home_reached")
            return

        target_heading = math.atan2(
            self.home_pose.y_m - self.pose.y_m,
            self.home_pose.x_m - self.pose.x_m,
        )
        heading_error = self._normalize_angle(target_heading - self.pose.heading_rad)

        if abs(heading_error) > self.config.heading_tolerance_rad:
            if heading_error > 0:
                self._drive(-700, 700)
            else:
                self._drive(700, -700)
            return

        speed = self.config.return_home_speed
        if self._distance_to_home() <= self.config.return_home_slow_radius_m:
            speed = self.config.return_home_slow_speed
        self._drive(speed, speed)

    def _pick_ball(self) -> None:
        self._stop_drive()
        if self.config.pre_open_before_pick:
            self._run_clamp(mode=2, timeout_s=self.config.drop_timeout_s)
            self._sleep(0.10)
        self._run_clamp(mode=1, timeout_s=self.config.pick_timeout_s)
        self._set_carry_arm_pose()
        self._carrying_ball = True
        self._enter_state(MissionState.RETURN_HOME, reason="ball_picked")
        self._plan_return_path()

    def _drop_ball(self) -> None:
        self._stop_drive()
        self._run_clamp(mode=2, timeout_s=self.config.drop_timeout_s)
        self._carrying_ball = False
        self._enter_state(MissionState.FOLLOW_LINE, reason="ball_dropped")

    def _start_avoidance(self, resume_state: MissionState) -> None:
        self._enter_state(MissionState.AVOID_OBSTACLE, reason="obstacle_detected")
        self._avoid_resume_state = resume_state
        self._avoid_phase = "backup"
        self._avoid_phase_end_ts = self._now() + self.config.avoid_backup_s

    def _step_avoidance(self) -> None:
        now = self._now()
        if self._avoid_phase == "backup":
            self._drive(self.config.avoid_backup_speed, self.config.avoid_backup_speed)
            if now >= self._avoid_phase_end_ts:
                self._avoid_phase = "turn"
                self._avoid_phase_end_ts = now + self.config.avoid_turn_s
            return

        if self._avoid_phase == "turn":
            self._drive(
                self.config.avoid_turn_left_speed, self.config.avoid_turn_right_speed
            )
            if now >= self._avoid_phase_end_ts:
                self._avoid_phase = "bypass"
                self._avoid_phase_end_ts = now + self.config.avoid_bypass_s
            return

        if self._avoid_phase == "bypass":
            self._drive(self.config.avoid_bypass_speed, self.config.avoid_bypass_speed)
            if now >= self._avoid_phase_end_ts:
                self._avoid_phase = "return"
                self._avoid_phase_end_ts = now + self.config.avoid_return_turn_s
            return

        if self._avoid_phase == "return":
            self._drive(
                self.config.avoid_turn_right_speed, self.config.avoid_turn_left_speed
            )
            if now >= self._avoid_phase_end_ts:
                self._avoid_phase = "settle"
                self._avoid_phase_end_ts = now + self.config.avoid_settle_s
            return

        self._stop_drive()
        if now >= self._avoid_phase_end_ts:
            self._avoid_phase = ""
            self._last_avoid_end_ts = now
            self._enter_state(self._avoid_resume_state, reason="avoid_complete")

    def _run_clamp(self, mode: int, timeout_s: float) -> None:
        self.car.set_mode_clamp(mode)
        deadline = self._now() + timeout_s
        while self.car.get_mode_clamp() == mode:
            self.car.mode_clamp()
            if self._now() >= deadline:
                self.car.set_mode_clamp(0)
                break

    def _set_carry_arm_pose(self) -> None:
        if not self.config.raise_arm_after_pick:
            return
        servo = getattr(self.car, "servo", None)
        if servo is None:
            return
        try:
            servo.setServoAngle("0", self.config.carry_servo0_angle)
            servo.setServoAngle("1", self.config.carry_servo1_angle)
            self._sleep(max(0.0, self.config.carry_pose_settle_s))
        except Exception:
            # Carry pose is a visibility improvement, not mission-critical.
            return

    def _remember_obstacle(self, distance_cm: float) -> None:
        distance_m = distance_cm / 100.0
        x_m = self.pose.x_m + distance_m * math.cos(self.pose.heading_rad)
        y_m = self.pose.y_m + distance_m * math.sin(self.pose.heading_rad)
        self.obstacle_memory.append(MapPoint(x_m=x_m, y_m=y_m, kind="obstacle"))
        self.line_graph.add_obstacle(x_m, y_m)

    def _remember_ball_here(self) -> None:
        self.ball_memory.append(MapPoint(self.pose.x_m, self.pose.y_m, "ball"))

    def get_map_string(self, size_m: float = 2.0, resolution: int = 41) -> str:
        """Render a small ASCII map centered at home pose.

        - `size_m` is the width/height in meters
        - `resolution` is the number of characters per side (odd preferred)
        """
        if resolution < 3:
            resolution = 3

        half = size_m / 2.0
        step = size_m / float(resolution - 1)

        # Map from world coords to grid indices.
        def to_idx(x_m: float, y_m: float):
            rel_x = x_m - self.home_pose.x_m
            rel_y = y_m - self.home_pose.y_m
            i = int((rel_y + half) / step)
            j = int((rel_x + half) / step)
            return i, j

        # Initialize grid with spaces.
        grid = [[" " for _ in range(resolution)] for _ in range(resolution)]

        # Draw lines, obstacles, balls.
        for p in self.line_memory:
            i, j = to_idx(p.x_m, p.y_m)
            if 0 <= i < resolution and 0 <= j < resolution:
                grid[i][j] = "-"

        for p in self.obstacle_memory:
            i, j = to_idx(p.x_m, p.y_m)
            if 0 <= i < resolution and 0 <= j < resolution:
                grid[i][j] = "X"

        for p in self.ball_memory:
            i, j = to_idx(p.x_m, p.y_m)
            if 0 <= i < resolution and 0 <= j < resolution:
                grid[i][j] = "o"

        # Home and current pose
        hi, hj = to_idx(self.home_pose.x_m, self.home_pose.y_m)
        ci, cj = to_idx(self.pose.x_m, self.pose.y_m)
        if 0 <= hi < resolution and 0 <= hj < resolution:
            grid[hi][hj] = "H"
        if 0 <= ci < resolution and 0 <= cj < resolution:
            grid[ci][cj] = "*"

        # Compose string with row 0 at top (y positive up -> show top to bottom)
        rows = ["".join(row) for row in reversed(grid)]
        title = f"map(center=home size={size_m}m res={resolution})"
        return title + "\n" + "\n".join(rows)

    def _is_obstacle(self, distance_cm: float) -> bool:
        if self._carrying_ball:
            return 0 < distance_cm <= self.config.obstacle_distance_cm
        # Prefer pickup first when not carrying and close enough.
        if self._is_pickup_distance(distance_cm):
            return False
        return 0 < distance_cm <= self.config.obstacle_distance_cm

    def _is_pickup_distance(self, distance_cm: float) -> bool:
        return 0 < distance_cm <= self.config.pickup_distance_cm

    def _is_line_lost(self, infrared_code: int) -> bool:
        if infrared_code == 7:
            return True
        if infrared_code == 0 and not self.config.line_code_zero_is_center:
            return True
        return False

    def _distance_cm(self) -> float:
        try:
            distance = float(self.car.sonic.get_distance())
        except Exception:
            return -1.0
        if distance > 0:
            self._sonic_history.append(distance)
            window = max(1, self.config.sonic_median_window)
            self._sonic_history = self._sonic_history[-window:]
        if not self._sonic_history:
            return -1.0
        return float(median(self._sonic_history))

    def _read_ir(self) -> int:
        try:
            code = int(self.car.infrared.read_all_infrared())
        except Exception:
            return 7
        self._ir_history.append(code)
        window = max(1, self.config.ir_majority_window)
        self._ir_history = self._ir_history[-window:]
        counts: dict[int, int] = {}
        for item in self._ir_history:
            counts[item] = counts.get(item, 0) + 1
        return max(counts.items(), key=lambda item: (item[1], item[0] == code))[0]

    def _infer_line_command(self, infrared_code: int) -> tuple[int, int]:
        if infrared_code == 2:
            return 1200, 1200
        if infrared_code == 4:
            return -1500, 2500
        if infrared_code == 6:
            return -2000, 4000
        if infrared_code == 1:
            return 2500, -1500
        if infrared_code == 3:
            return 4000, -2000
        if infrared_code == 0 and self.config.line_code_zero_is_center:
            return 1200, 1200
        return self.config.line_crawl_speed, self.config.line_crawl_speed

    def _integrate_pose(self) -> None:
        now = self._now()
        dt = now - self._last_motion_ts
        self._last_motion_ts = now
        if dt <= 0.0:
            return

        dt = min(dt, 0.2)
        left_mps = self._cmd_left * self.config.duty_to_mps
        right_mps = self._cmd_right * self.config.duty_to_mps

        v = 0.5 * (left_mps + right_mps)
        omega = (right_mps - left_mps) / max(self.config.wheel_base_m, 0.001)
        self.pose.heading_rad = self._normalize_angle(
            self.pose.heading_rad + omega * dt
        )
        self.pose.x_m += v * math.cos(self.pose.heading_rad) * dt
        self.pose.y_m += v * math.sin(self.pose.heading_rad) * dt

    def _now(self) -> float:
        if self._clock is not None:
            return float(self._clock())
        return time.monotonic()

    def _sleep(self, seconds: float) -> None:
        if self._clock is None:
            time.sleep(seconds)

    def _drive(self, left: int, right: int) -> None:
        self.car.motor.setMotorModel(int(left), int(right))
        self._cmd_left = int(left)
        self._cmd_right = int(right)

    def _stop_drive(self) -> None:
        self._drive(0, 0)

    def _distance_to_home(self) -> float:
        return math.hypot(
            self.home_pose.x_m - self.pose.x_m, self.home_pose.y_m - self.pose.y_m
        )

    def _plan_return_path(self) -> None:
        self._return_path_nodes = []
        self._return_path_idx = 0

        if self.line_graph.home_node is None:
            return
        start = self.line_graph.find_nearest_node(self.pose.x_m, self.pose.y_m)
        if start is None:
            return
        path = self.line_graph.shortest_path(start, self.line_graph.home_node)
        if len(path) >= 2:
            self._return_path_nodes = path

    def _follow_return_path(self) -> bool:
        if not self._return_path_nodes:
            return False

        if self._return_path_idx >= len(self._return_path_nodes):
            self._return_path_nodes = []
            return False

        node_idx = self._return_path_nodes[self._return_path_idx]
        node = self.line_graph.nodes[node_idx]
        target_dist = math.hypot(node.x_m - self.pose.x_m, node.y_m - self.pose.y_m)

        if target_dist <= max(0.04, self.line_graph.merge_distance_m * 0.8):
            self._return_path_idx += 1
            if self._return_path_idx >= len(self._return_path_nodes):
                self._return_path_nodes = []
                return False
            node_idx = self._return_path_nodes[self._return_path_idx]
            node = self.line_graph.nodes[node_idx]

        target_heading = math.atan2(node.y_m - self.pose.y_m, node.x_m - self.pose.x_m)
        heading_error = self._normalize_angle(target_heading - self.pose.heading_rad)

        if abs(heading_error) > self.config.heading_tolerance_rad:
            if heading_error > 0:
                self._drive(-700, 700)
            else:
                self._drive(700, -700)
            return True

        self._drive(850, 850)
        return True

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle
