from challenge.mission import MissionConfig
from challenge.sim.runner import SimRunner


def test_full_course_seeded_headless_smoke():
    cfg = MissionConfig(use_vision=True, vision_every_n_ticks=1)
    runner = SimRunner("full-course", seed=42, config=cfg, use_vision=True)
    try:
        for _ in range(25):
            runner.tick()

        status = runner.mission.get_status()
        assert status["state"] in {
            "follow_line",
            "seek_ball",
            "avoid_obstacle",
            "pick_ball",
            "return_home",
            "drop_ball",
        }
        assert status["watchdog_resets"] == 0
    finally:
        runner.close()
