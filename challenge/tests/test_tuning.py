from challenge.sim.runner import SimRunner
from challenge.tuning import (
    _randomize_world,
    default_param_vector,
    evaluate_params,
    vector_to_params,
)


def test_tuning_vector_maps_to_valid_params():
    params = vector_to_params(default_param_vector())

    assert params["line_crawl_speed"] >= 120
    assert params["seek_lock_frames"] >= 1
    assert 0.1 <= params["heading_tolerance_rad"] <= 1.0


def test_evaluate_params_smoke():
    params = vector_to_params(default_param_vector())

    score, results = evaluate_params(
        params,
        scenarios=["straight-line"],
        seeds=[0],
        max_ticks=5,
        domain_randomization=False,
    )

    assert results
    assert isinstance(score, float)
    assert results[0].scenario == "straight-line"


def test_domain_randomization_is_plausible_and_changes_setup():
    runner = SimRunner("full-course", seed=0)
    try:
        original_pose = (runner.world.pose.x_m, runner.world.pose.y_m, runner.world.pose.heading_rad)
        original_ball = (runner.world.arena.balls[0].cx, runner.world.arena.balls[0].cy)
        original_width = runner.world.arena.line_polylines[0].width_m

        _randomize_world(runner, seed=5)

        pose = runner.world.pose
        ball = runner.world.arena.balls[0]
        assert (pose.x_m, pose.y_m, pose.heading_rad) != original_pose
        assert (ball.cx, ball.cy) != original_ball
        assert runner.world.arena.line_polylines[0].width_m != original_width
        assert 0.12 <= pose.x_m <= runner.world.arena.width_m - 0.12
        assert 0.12 <= pose.y_m <= runner.world.arena.height_m - 0.12
        assert 0.25 <= ball.cx <= runner.world.arena.width_m - 0.25
        assert 0.25 <= ball.cy <= runner.world.arena.height_m - 0.25
        assert 0.025 <= runner.world.arena.line_polylines[0].width_m <= 0.07
    finally:
        runner.close()
