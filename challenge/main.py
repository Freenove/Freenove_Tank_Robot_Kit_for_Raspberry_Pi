import argparse
from pathlib import Path
import select
import sys
import termios
import time
import tty
from typing import Callable, Optional


repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from challenge.hardware import make_car  # noqa: E402
from challenge.mission import ChallengeMission, MissionConfig  # noqa: E402


MOVEMENT_COMMANDS = {"w", "a", "s", "d", "space", " "}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run challenge mission. Picks the real Freenove tank on a "
        "Raspberry Pi and the in-process simulator everywhere else."
    )
    parser.add_argument(
        "--mode", choices=["sim", "real", "auto"], default="auto",
        help="hardware backend: sim (mock+SimWorld), real (Freenove), auto (default)",
    )
    parser.add_argument(
        "--scenario", default="full-course",
        help="named scenario for sim mode (see challenge/sim/scenarios.py)",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="open the pygame visualizer (sim mode only)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="seed sim RNG for reproducible runs",
    )
    parser.add_argument("--use-vision", action="store_true",
                        help="enable red-ball vision pipeline (mission)")
    parser.add_argument("--params", default=None,
                        help="load mission tuning params JSON (for example outputs/ga/best_params.json)")
    parser.add_argument("--obstacle-cm", type=float, default=18.0)
    parser.add_argument("--pickup-cm", type=float, default=8.0)
    parser.add_argument("--home-radius-m", type=float, default=0.22)
    parser.add_argument("--status-interval", type=float, default=1.0)
    parser.add_argument("--loop-sleep", type=float, default=0.05)
    parser.add_argument("--line-crawl-speed", type=int, default=260)
    parser.add_argument("--ir-zero-lost", action="store_true")
    parser.add_argument("--calibrate", action="store_true",
                        help="print sensor and arm state without running the mission")
    parser.add_argument("--calibrate-arm", action="store_true",
                        help="move the carry arm pose during calibration")
    parser.add_argument("--calibrate-seconds", type=float, default=8.0)
    parser.add_argument("--calibrate-interval", type=float, default=0.75)
    return parser.parse_args()


def apply_args(cfg: MissionConfig, args: argparse.Namespace) -> None:
    cfg.obstacle_distance_cm = args.obstacle_cm
    cfg.pickup_distance_cm = args.pickup_cm
    cfg.home_radius_m = max(0.05, args.home_radius_m)
    cfg.loop_sleep_s = max(0.01, args.loop_sleep)
    cfg.line_crawl_speed = max(120, args.line_crawl_speed)
    if args.ir_zero_lost:
        cfg.line_code_zero_is_center = False
    if getattr(args, "params", None):
        from challenge.tuning import apply_params, load_params

        apply_params(cfg, load_params(args.params))


def read_command() -> Optional[str]:
    if not sys.stdin or sys.stdin.closed or not sys.stdin.isatty():
        return None

    try:
        readable, _, _ = select.select([sys.stdin], [], [], 0.0)
    except (OSError, ValueError):
        return None

    if not readable:
        return None

    line = sys.stdin.readline()
    if not line:
        return None
    return line.rstrip("\r\n").lower()


class RuntimeConsole:
    """Interactive console that keeps command prompt while status lines stream."""

    def __init__(self) -> None:
        self.enabled = bool(sys.stdin and not sys.stdin.closed and sys.stdin.isatty())
        self._fd: Optional[int] = None
        self._term_state = None
        self._buffer = ""

    def start(self) -> None:
        if not self.enabled:
            return

        try:
            self._fd = sys.stdin.fileno()
            self._term_state = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
            self._redraw_prompt()
        except Exception:
            self.enabled = False
            self._fd = None
            self._term_state = None

    def stop(self) -> None:
        if self._fd is not None and self._term_state is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._term_state)
            except Exception:
                pass

        if self.enabled:
            sys.stdout.write("\n")
            sys.stdout.flush()

    def poll_commands(self) -> list[str]:
        if not self.enabled:
            return []

        commands: list[str] = []
        while True:
            try:
                readable, _, _ = select.select([sys.stdin], [], [], 0.0)
            except (OSError, ValueError):
                break

            if not readable:
                break

            char = sys.stdin.read(1)
            if not char:
                break

            command = self._process_char(char)
            if command:
                commands.append(command)

        return commands

    def print_status_line(self, line: str) -> None:
        if not self.enabled:
            print(line)
            return

        sys.stdout.write("\r\033[2K" + line + "\n")
        self._redraw_prompt()

    def print_info_line(self, line: str) -> None:
        self.print_status_line(line)

    def _process_char(self, char: str) -> Optional[str]:
        if char == "\x03":
            raise KeyboardInterrupt

        if char in ("\r", "\n"):
            command = self._buffer.strip().lower()
            self._buffer = ""
            self._redraw_prompt()
            return command if command else None

        if char in ("\x7f", "\b"):
            if self._buffer:
                self._buffer = self._buffer[:-1]
                self._redraw_prompt()
            return None

        lowered = char.lower()
        if not self._buffer and lowered in ("w", "a", "s", "d"):
            return lowered
        if not self._buffer and char == " ":
            return "space"

        if char.isprintable():
            self._buffer += char
            self._redraw_prompt()
        return None

    def _redraw_prompt(self) -> None:
        if not self.enabled:
            return
        sys.stdout.write("\r\033[2K[challenge][cmd] " + self._buffer)
        sys.stdout.flush()


def handle_command(
    command: str,
    mission: ChallengeMission,
    cfg: MissionConfig,
    emit_line: Callable[[str], None] = print,
) -> bool:
    step_s = max(0.10, min(0.28, cfg.loop_sleep_s * 4.0))

    # Use non-blocking manual override instead of blocking pulse.
    if command in ("w", "a", "s", "d"):
        mission.start_manual_drive(command, step_s)
        return True

    if command in (" ", "space"):
        mission.manual_pickup_toggle()
        return True

    if command == "home":
        mission.reset_home_anchor()
        emit_line("[challenge] home anchor reset")
        return True

    if command == "status":
        status = mission.get_status()
        emit_line(
            "[challenge] state=%s reason=%s age=%.2fs ir=%s distance_cm=%.1f carrying=%s "
            "home_m=%.2f balls=%s obstacles=%s"
            % (
                status["state"],
                status["state_reason"],
                float(status["state_age_s"]),
                status["ir"],
                status["distance_cm"],
                status["carrying"],
                status["home_m"],
                status["balls"],
                status["obstacles"],
            )
        )
        return True

    if command in ("help", "?"):
        emit_line("[challenge] commands: w a s d space home status help")
        return True

    return False


def coalesce_commands(commands: list[str]) -> list[str]:
    """Collapse repeated movement keys so terminal key-repeat does not queue actions."""

    if not commands:
        return []

    output: list[str] = []
    pending_movement: Optional[str] = None
    for command in commands:
        if command in MOVEMENT_COMMANDS:
            pending_movement = "space" if command == " " else command
            continue

        if pending_movement is not None:
            output.append(pending_movement)
            pending_movement = None

        output.append(command)

    if pending_movement is not None:
        output.append(pending_movement)

    return output


def _build_sim_world(args: argparse.Namespace):
    from challenge.sim.scenarios import build_world

    return build_world(args.scenario, seed=args.seed)


def _run_calibration(
    mission: ChallengeMission,
    cfg: MissionConfig,
    *,
    duration_s: float,
    interval_s: float,
    set_arm_pose: bool,
) -> None:
    servo = getattr(mission.car, "servo", None)
    if set_arm_pose:
        if servo is not None:
            try:
                servo.setServoAngle("0", cfg.carry_servo0_angle)
                servo.setServoAngle("1", cfg.carry_servo1_angle)
            except Exception as exc:
                print(f"[challenge][calibrate] arm move failed: {exc}")
        else:
            print("[challenge][calibrate] arm move skipped: servo unavailable")

    print(
        "[challenge][calibrate] seconds=%.1f interval=%.2f arm=%s"
        % (duration_s, interval_s, bool(set_arm_pose))
    )
    start = time.monotonic()
    while time.monotonic() - start < max(0.0, duration_s):
        status = mission.get_status()
        servo0 = None
        servo1 = None
        if servo is not None:
            try:
                servo0 = servo.getServoAngle("0")
                servo1 = servo.getServoAngle("1")
            except Exception:
                servo0 = servo1 = None
        raised = None
        world = getattr(mission.car, "_world", None)
        if world is None:
            world = getattr(mission.car, "world", None)
        if world is not None and hasattr(world, "carry_pose_is_raised"):
            try:
                raised = bool(world.carry_pose_is_raised())
            except Exception:
                raised = None
        print(
            "[challenge][calibrate] state=%s reason=%s age=%.2fs ir=%s dist=%.1fcm "
            "carrying=%s home=%.2fm servo0=%s servo1=%s carry_pose=%s"
            % (
                status["state"],
                status["state_reason"],
                float(status["state_age_s"]),
                status["ir"],
                status["distance_cm"],
                status["carrying"],
                status["home_m"],
                servo0 if servo0 is not None else "-",
                servo1 if servo1 is not None else "-",
                "-" if raised is None else ("raised" if raised else "low"),
            )
        )
        time.sleep(max(0.05, interval_s))


def main() -> None:
    args = parse_args()
    cfg = MissionConfig()
    apply_args(cfg, args)
    cfg.use_vision = bool(args.use_vision)

    sim_world = None
    chosen_mode = args.mode
    if chosen_mode == "auto":
        chosen_mode = "real" if sys.platform.startswith("linux") else "sim"

    if chosen_mode == "sim":
        sim_world = _build_sim_world(args)

    try:
        car = make_car(chosen_mode, world=sim_world)
    except RuntimeError as exc:
        print(f"[challenge] {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    mission = ChallengeMission(car=car, config=cfg)
    mission.reset_home_anchor()

    if args.calibrate:
        try:
            _run_calibration(
                mission,
                cfg,
                duration_s=args.calibrate_seconds,
                interval_s=args.calibrate_interval,
                set_arm_pose=bool(args.calibrate_arm),
            )
        finally:
            car.close()
        return

    visualizer = None
    if chosen_mode == "sim" and args.gui:
        try:
            from challenge.sim.visualizer import PygameVisualizer

            visualizer = PygameVisualizer(sim_world, mission)
        except Exception as exc:  # pygame may fail to init in some envs
            print(f"[challenge] gui disabled: {exc}")
            visualizer = None

    status_interval = max(0.0, args.status_interval)
    last_status = 0.0
    console = RuntimeConsole()

    print(f"[challenge] mode={chosen_mode} scenario={args.scenario if chosen_mode == 'sim' else '-'}"
          f" vision={cfg.use_vision}")
    print(
        "[challenge] obstacle_cm=%.1f pickup_cm=%.1f home_radius_m=%.2f"
        % (cfg.obstacle_distance_cm, cfg.pickup_distance_cm, cfg.home_radius_m)
    )
    print(
        "[challenge] commands: w a s d (tap key), space (tap key), home/status/help + Enter"
    )

    try:
        console.start()
        while True:
            if console.enabled:
                commands = console.poll_commands()
            else:
                command = read_command()
                commands = [command] if command else []

            if visualizer is not None:
                gui_commands = visualizer.poll_commands()
                if gui_commands:
                    commands = list(commands) + list(gui_commands)

            commands = coalesce_commands(commands)

            manual_handled = False
            for command in commands:
                if handle_command(
                    command, mission, cfg, emit_line=console.print_info_line
                ):
                    manual_handled = True

            if not manual_handled:
                mission.step()

            if sim_world is not None:
                # Advance the world after the mission step so motor commands
                # issued this tick get applied next tick. Using mission loop
                # cadence keeps the simulator deterministic w.r.t. mission.
                speed = getattr(visualizer, "speed", 1.0) if visualizer is not None else 1.0
                sim_world.tick(cfg.loop_sleep_s * max(0.25, min(8.0, float(speed))))

            if visualizer is not None:
                visualizer.draw(mission)
                if visualizer.should_quit():
                    break

            now = time.monotonic()
            if status_interval > 0 and now - last_status >= status_interval:
                status = mission.get_status()
                console.print_status_line(
                    "[challenge][status] state=%s reason=%s age=%.2fs ir=%s distance_cm=%.1f "
                    "carrying=%s home_m=%.2f balls=%s obstacles=%s"
                    % (
                        status["state"],
                        status["state_reason"],
                        float(status["state_age_s"]),
                        status["ir"],
                        status["distance_cm"],
                        status["carrying"],
                        status["home_m"],
                        status["balls"],
                        status["obstacles"],
                    )
                )
                # Also emit a small ASCII map showing home/current/lines/objects.
                try:
                    map_str = mission.get_map_string(size_m=2.0, resolution=41)
                    console.print_info_line(map_str)
                except Exception:
                    pass
                last_status = now

            time.sleep(cfg.loop_sleep_s)
    except KeyboardInterrupt:
        console.print_info_line("[challenge] stopping")
    finally:
        console.stop()
        if visualizer is not None:
            visualizer.close()
        car.close()


if __name__ == "__main__":
    main()
