from challenge.mission import MissionConfig, MissionState
from challenge.sim.runner import SimRunner


def test_seek_ball_locks_then_picks_and_returns():
    cfg = MissionConfig(
        use_vision=True,
        vision_every_n_ticks=1,
        seek_lock_frames=2,
        pickup_distance_cm=20.0,
        obstacle_distance_cm=6.0,
        seek_approach_radius_px=24,
    )
    runner = SimRunner("line-with-ball", seed=1, config=cfg, use_vision=True)
    runner.world.config.pickup_radius_m = 0.25
    try:
        runner.world.pose.x_m = 2.75
        runner.world.pose.y_m = 2.0
        runner.world.pose.heading_rad = 0.0
        runner.mission.pose.x_m = 2.75
        runner.mission.pose.y_m = 2.0
        runner.mission.pose.heading_rad = 0.0

        runner.tick()
        runner.tick()

        assert runner.mission.state == MissionState.SEEK_BALL

        runner.world.pose.x_m = 3.03
        runner.world.pose.y_m = 2.0
        runner.mission.pose.x_m = 3.03
        runner.mission.pose.y_m = 2.0
        runner.tick()
        runner.tick()

        assert runner.mission.state == MissionState.PICK_BALL

        runner.tick()

        assert runner.mission.state == MissionState.RETURN_HOME
        assert runner.mission.is_carrying_ball()
        assert runner.world.carrying_ball
        assert len(runner.world.arena.balls) == 0
    finally:
        runner.close()
