import pytest

from challenge.mission import MissionConfig
from challenge.sim.runner import SimRunner


def test_visualizer_draws_with_dummy_video_driver(monkeypatch):
    pygame = pytest.importorskip("pygame")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    runner = SimRunner("line-with-ball", seed=1, config=MissionConfig(use_vision=True))
    visualizer = None
    try:
        from challenge.sim.visualizer import PygameVisualizer

        visualizer = PygameVisualizer(runner.world, runner.mission)
        visualizer.draw(runner.mission)
        assert visualizer.should_quit() is False
    finally:
        if visualizer is not None:
            visualizer.close()
        else:
            pygame.quit()
        runner.close()
