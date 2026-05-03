import argparse
import importlib.util
from pathlib import Path
import select
import sys
import termios
import time
import tty
from typing import Callable, Optional


repo_root = Path(__file__).resolve().parents[1]
server_dir = repo_root / "Code" / "Server"
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from challenge.mission import ChallengeMission, MissionConfig  # noqa: E402


MOVEMENT_COMMANDS = {"w", "a", "s", "d", "space", " "}


def load_car_class():
    car_path = server_dir / "car.py"
    spec = importlib.util.spec_from_file_location("challenge_server_car", car_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load car module from {car_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "Car"):
        raise RuntimeError(f"Car class not found in {car_path}")
    return module.Car


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run challenge mission (car.py-based) with optional manual WASD controls"
    )
    parser.add_argument("--obstacle-cm", type=float, default=18.0)
    parser.add_argument("--pickup-cm", type=float, default=8.0)
    parser.add_argument("--home-radius-m", type=float, default=0.22)
    parser.add_argument("--status-interval", type=float, default=1.0)
    parser.add_argument("--loop-sleep", type=float, default=0.05)
    parser.add_argument("--line-crawl-speed", type=int, default=260)
    parser.add_argument("--ir-zero-lost", action="store_true")
    return parser.parse_args()


def apply_args(cfg: MissionConfig, args: argparse.Namespace) -> None:
    cfg.obstacle_distance_cm = args.obstacle_cm
    cfg.pickup_distance_cm = args.pickup_cm
    cfg.home_radius_m = max(0.05, args.home_radius_m)
    cfg.loop_sleep_s = max(0.01, args.loop_sleep)
    cfg.line_crawl_speed = max(120, args.line_crawl_speed)
    if args.ir_zero_lost:
        cfg.line_code_zero_is_center = False


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
            "[challenge] state=%s ir=%s distance_cm=%.1f carrying=%s home_m=%.2f balls=%s obstacles=%s"
            % (
                status["state"],
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


def main() -> None:
    args = parse_args()
    cfg = MissionConfig()
    apply_args(cfg, args)

    Car = load_car_class()
    car = Car()
    mission = ChallengeMission(car=car, config=cfg)
    mission.reset_home_anchor()

    status_interval = max(0.0, args.status_interval)
    last_status = 0.0
    console = RuntimeConsole()

    print("[challenge] main started (car.py runtime)")
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

            commands = coalesce_commands(commands)

            manual_handled = False
            for command in commands:
                if handle_command(
                    command, mission, cfg, emit_line=console.print_info_line
                ):
                    manual_handled = True

            if not manual_handled:
                mission.step()

            now = time.monotonic()
            if status_interval > 0 and now - last_status >= status_interval:
                status = mission.get_status()
                console.print_status_line(
                    "[challenge][status] state=%s ir=%s distance_cm=%.1f carrying=%s home_m=%.2f balls=%s obstacles=%s"
                    % (
                        status["state"],
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
        car.close()


if __name__ == "__main__":
    main()
