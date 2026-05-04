"""Simulator runner for exercising ChallengeMission in tests or CLI."""

from __future__ import annotations

import argparse
import time
from typing import Callable

from challenge.hardware.mock_car import MockCar
from challenge.mission import ChallengeMission, MissionConfig
from challenge.sim.scenarios import build_world
from challenge.sim.world import SimWorld


class SimRunner:
    def __init__(
        self,
        scenario: str = "full-course",
        *,
        seed: int | None = None,
        config: MissionConfig | None = None,
        use_vision: bool = False,
    ) -> None:
        self.world = build_world(scenario, seed=seed)
        self.car = MockCar(self.world)
        self.config = config or MissionConfig()
        self.config.use_vision = use_vision
        self.mission = ChallengeMission(
            self.car,
            self.config,
            clock=lambda: self.world.elapsed_s,
        )
        self.mission.reset_home_anchor()

    def tick(self, dt_s: float | None = None) -> None:
        dt_s = dt_s if dt_s is not None else self.config.loop_sleep_s
        self.mission.step()
        self.world.tick(dt_s)

    def run_until(
        self,
        predicate: Callable[["SimRunner"], bool],
        *,
        max_ticks: int = 1000,
        realtime: bool = False,
    ) -> bool:
        for _ in range(max_ticks):
            if predicate(self):
                return True
            self.tick()
            if realtime:
                time.sleep(self.config.loop_sleep_s)
        return predicate(self)

    def close(self) -> None:
        self.car.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the tank simulator.")
    parser.add_argument("--scenario", default="full-course")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--ticks", type=int, default=400)
    parser.add_argument("--use-vision", action="store_true")
    parser.add_argument("--params", default=None, help="JSON params file from CMA-ES training")
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="disable the pygame visualizer",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = MissionConfig()
    if args.params:
        from challenge.tuning import apply_params, load_params

        apply_params(config, load_params(args.params))
    runner = SimRunner(args.scenario, seed=args.seed, config=config, use_vision=args.use_vision)
    visualizer = None
    try:
        if not args.headless:
            try:
                from challenge.sim.visualizer import PygameVisualizer

                visualizer = PygameVisualizer(runner.world, runner.mission)
            except Exception as exc:
                print(f"[sim] visualizer disabled: {exc}")
                visualizer = None

        for _ in range(max(0, args.ticks)):
            if visualizer is not None:
                for command in visualizer.poll_commands():
                    if command in ("w", "a", "s", "d"):
                        runner.mission.start_manual_drive(command, runner.config.loop_sleep_s * 4.0)
                    elif command == "space":
                        runner.mission.manual_pickup_toggle()
                    elif command == "home":
                        runner.mission.reset_home_anchor()
                if visualizer.should_quit():
                    break
            runner.tick()
            if visualizer is not None:
                visualizer.draw(runner.mission)
            if args.realtime:
                time.sleep(runner.config.loop_sleep_s)
        status = runner.mission.get_status()
        print(
            "[sim] state=%s carrying=%s home_m=%.2f balls=%s ticks=%s"
            % (
                status["state"],
                status["carrying"],
                status["home_m"],
                len(runner.world.arena.balls),
                runner.world.tick_count,
            )
        )
    finally:
        if visualizer is not None:
            visualizer.close()
        runner.close()


if __name__ == "__main__":
    main()


__all__ = ["SimRunner"]
