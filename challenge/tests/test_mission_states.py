from challenge.mission import MissionConfig, MissionState
from challenge.sim.runner import SimRunner


def test_sonic_median_ignores_single_miss():
    cfg = MissionConfig(sonic_median_window=3)
    runner = SimRunner("line-with-ball", seed=1, config=cfg)
    try:
        runner.mission._sonic_history = [28.0, 30.0]
        runner.world.config.ultrasonic_miss_prob = 1.0

        assert runner.mission._distance_cm() == 29.0
    finally:
        runner.close()


def test_ir_majority_ignores_single_tick_flicker():
    cfg = MissionConfig(ir_majority_window=3)
    runner = SimRunner("straight-line", seed=1, config=cfg)
    try:
        runner.mission._ir_history = [2, 2]
        runner.world.pose.y_m = 2.20

        assert runner.mission._read_ir() == 2
    finally:
        runner.close()


def test_line_lost_uses_search_before_crawl_fallback():
    cfg = MissionConfig(
        spiral_search_budget_s=2.0,
        line_crawl_speed=260,
        line_code_zero_is_center=False,
    )
    runner = SimRunner("straight-line", seed=1, config=cfg)
    try:
        runner.world.pose.y_m = 2.5
        runner.mission.pose.y_m = 2.5
        runner.mission._follow_line_continuous()

        assert runner.world.cmd_left_duty < 0
        assert runner.world.cmd_right_duty > 0
    finally:
        runner.close()


def test_watchdog_resets_stuck_seek_state():
    cfg = MissionConfig(state_timeout_s=0.01)
    runner = SimRunner("line-with-ball", seed=1, config=cfg)
    try:
        runner.mission._enter_state(MissionState.SEEK_BALL)
        runner.mission._state_entry_ts = runner.world.elapsed_s - 1.0
        runner.mission._reset_watchdog_snapshot()
        runner.mission._last_detection = None

        runner.mission.step()

        assert runner.mission.state == MissionState.FOLLOW_LINE
        assert runner.mission.get_status()["watchdog_resets"] == 1
    finally:
        runner.close()
