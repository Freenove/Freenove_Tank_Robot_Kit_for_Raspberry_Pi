from challenge.sim.scenarios import build_world


def test_ultrasonic_distance_tracks_ball_ahead():
    world = build_world("line-with-ball", seed=1)
    world.pose.x_m = 3.0
    world.pose.y_m = 2.0
    world.pose.heading_rad = 0.0

    distance_cm = world.read_sonic_cm()

    assert 5.0 <= distance_cm <= 8.0


def test_ir_code_changes_when_crossing_line():
    world = build_world("straight-line", seed=1)
    world.pose.x_m = 1.0
    world.pose.y_m = 2.0
    world.pose.heading_rad = 0.0

    assert world.read_ir_code() == 2

    world.pose.y_m = 2.20

    assert world.read_ir_code() == 0


def test_clamp_pickup_requires_ball_in_reach():
    world = build_world("line-with-ball", seed=1)
    world.pose.x_m = 3.18
    world.pose.y_m = 2.0
    world.pose.heading_rad = 0.0
    world.set_clamp_mode(1)

    for _ in range(40):
        world.tick(world.config.dt_s)

    assert world.carrying_ball
    assert len(world.arena.balls) == 0
