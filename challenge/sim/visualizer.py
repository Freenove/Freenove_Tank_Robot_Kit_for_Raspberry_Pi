"""Pygame visualizer for the simulated arena and camera feed."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from challenge.mission import ChallengeMission

    from .world import SimWorld


class PygameVisualizer:
    def __init__(self, world: "SimWorld", mission: "ChallengeMission") -> None:
        import pygame

        self.pygame = pygame
        self.world = world
        self._quit = False
        self._speed = 1.0
        pygame.init()
        self.screen = pygame.display.set_mode((960, 560))
        pygame.display.set_caption("Tank Simulator")
        self.font = pygame.font.Font(None, 22)
        self.small_font = pygame.font.Font(None, 18)
        self.draw(mission)

    @property
    def speed(self) -> float:
        return self._speed

    def poll_commands(self) -> list[str]:
        pygame = self.pygame
        commands: list[str] = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit = True
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self._quit = True
                elif event.key == pygame.K_w:
                    commands.append("w")
                elif event.key == pygame.K_a:
                    commands.append("a")
                elif event.key == pygame.K_s:
                    commands.append("s")
                elif event.key == pygame.K_d:
                    commands.append("d")
                elif event.key == pygame.K_SPACE:
                    commands.append("space")
                elif event.key == pygame.K_h:
                    commands.append("home")
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    self._speed = min(8.0, self._speed * 1.25)
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                    self._speed = max(0.25, self._speed / 1.25)
        return commands

    def draw(self, mission: "ChallengeMission") -> None:
        pygame = self.pygame
        self.screen.fill((238, 238, 232))

        arena_rect = pygame.Rect(18, 18, 520, 520)
        camera_rect = pygame.Rect(560, 18, 380, 285)
        status_rect = pygame.Rect(560, 320, 380, 218)

        pygame.draw.rect(self.screen, (247, 247, 242), arena_rect)
        pygame.draw.rect(self.screen, (45, 45, 42), arena_rect, width=2)
        self._draw_arena(arena_rect, mission)
        self._draw_camera(camera_rect)
        self._draw_status(status_rect, mission)

        pygame.display.flip()

    def should_quit(self) -> bool:
        return self._quit

    def close(self) -> None:
        self.pygame.quit()

    def _to_screen(self, rect, x_m: float, y_m: float) -> tuple[int, int]:
        scale = min(rect.width / self.world.arena.width_m, rect.height / self.world.arena.height_m)
        x = rect.left + int(round(x_m * scale))
        y = rect.bottom - int(round(y_m * scale))
        return x, y

    def _draw_arena(self, rect, mission: "ChallengeMission") -> None:
        pygame = self.pygame
        arena = self.world.arena

        for line in arena.line_polylines:
            points = [self._to_screen(rect, x, y) for x, y in line.points_m]
            width_px = max(2, int(round(line.width_m * rect.width / max(arena.width_m, 0.01))))
            if len(points) >= 2:
                pygame.draw.lines(self.screen, (15, 15, 15), False, points, width_px)

        for obs in arena.circle_obstacles:
            cx, cy = self._to_screen(rect, obs.cx, obs.cy)
            r = max(3, int(round(obs.r * rect.width / max(arena.width_m, 0.01))))
            pygame.draw.circle(self.screen, (215, 104, 45), (cx, cy), r)

        for obs in arena.rect_obstacles:
            cx, cy = self._to_screen(rect, obs.cx, obs.cy)
            scale = rect.width / max(arena.width_m, 0.01)
            box = pygame.Rect(0, 0, int(obs.half_w * 2 * scale), int(obs.half_h * 2 * scale))
            box.center = (cx, cy)
            pygame.draw.rect(self.screen, (105, 105, 105), box)

        for ball in arena.balls:
            cx, cy = self._to_screen(rect, ball.cx, ball.cy)
            r = max(5, int(round(ball.r * rect.width / max(arena.width_m, 0.01))))
            pygame.draw.circle(self.screen, (210, 20, 20), (cx, cy), r)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), r, width=1)

        for node in mission.line_graph.nodes:
            x, y = self._to_screen(rect, node.x_m, node.y_m)
            pygame.draw.circle(self.screen, (50, 120, 170), (x, y), 2)

        self._draw_ultrasonic_cone(rect)
        self._draw_ir_points(rect)
        self._draw_robot(rect)

    def _draw_robot(self, rect) -> None:
        pygame = self.pygame
        pose = self.world.pose
        cx, cy = self._to_screen(rect, pose.x_m, pose.y_m)
        heading = pose.heading_rad
        scale = rect.width / max(self.world.arena.width_m, 0.01)
        length = 0.18 * scale
        width = 0.10 * scale

        nose = (cx + math.cos(heading) * length, cy - math.sin(heading) * length)
        left = (
            cx + math.cos(heading + 2.45) * width,
            cy - math.sin(heading + 2.45) * width,
        )
        right = (
            cx + math.cos(heading - 2.45) * width,
            cy - math.sin(heading - 2.45) * width,
        )
        pygame.draw.polygon(self.screen, (35, 85, 145), [nose, left, right])
        pygame.draw.circle(self.screen, (245, 245, 245), (cx, cy), 3)

    def _draw_ir_points(self, rect) -> None:
        from .sensors import IR_OFFSETS_M

        pygame = self.pygame
        pose = self.world.pose
        cos_h = math.cos(pose.heading_rad)
        sin_h = math.sin(pose.heading_rad)
        for forward, lateral in IR_OFFSETS_M:
            x = pose.x_m + forward * cos_h - lateral * sin_h
            y = pose.y_m + forward * sin_h + lateral * cos_h
            sx, sy = self._to_screen(rect, x, y)
            color = (20, 20, 20) if self.world.arena.is_on_line(x, y) else (235, 235, 90)
            pygame.draw.circle(self.screen, color, (sx, sy), 4)

    def _draw_ultrasonic_cone(self, rect) -> None:
        pygame = self.pygame
        pose = self.world.pose
        origin = self._to_screen(rect, pose.x_m, pose.y_m)
        points = [origin]
        for delta_deg in (-7.5, 7.5):
            theta = pose.heading_rad + math.radians(delta_deg)
            x = pose.x_m + math.cos(theta) * 0.7
            y = pose.y_m + math.sin(theta) * 0.7
            points.append(self._to_screen(rect, x, y))
        pygame.draw.polygon(self.screen, (180, 210, 225), points, width=1)

    def _draw_camera(self, rect) -> None:
        pygame = self.pygame
        pygame.draw.rect(self.screen, (30, 30, 30), rect)
        frame_bgr = self.world.render_camera_bgr()
        if frame_bgr is None:
            return
        frame_rgb = np.ascontiguousarray(frame_bgr[:, :, ::-1].swapaxes(0, 1))
        surface = pygame.surfarray.make_surface(frame_rgb)
        surface = pygame.transform.smoothscale(surface, (rect.width, rect.height))
        self.screen.blit(surface, rect.topleft)
        pygame.draw.rect(self.screen, (45, 45, 42), rect, width=2)

    def _draw_status(self, rect, mission: "ChallengeMission") -> None:
        pygame = self.pygame
        pygame.draw.rect(self.screen, (248, 248, 244), rect)
        pygame.draw.rect(self.screen, (45, 45, 42), rect, width=2)
        status = mission.get_status()
        carry_pose = "-"
        if hasattr(self.world, "carry_pose_is_raised"):
            try:
                carry_pose = "raised" if self.world.carry_pose_is_raised() else "low"
            except Exception:
                carry_pose = "-"
        lines = [
            f"state: {status['state']}",
            f"reason: {status['state_reason']}  age: {status['state_age_s']:.2f}s",
            f"ir: {status['ir']}  sonic: {status['distance_cm']:.1f} cm",
            f"pose: {status['x_m']:.2f}, {status['y_m']:.2f}, {status['heading_deg']:.0f} deg",
            f"home: {status['home_m']:.2f} m  carrying: {status['carrying']}  arm: {carry_pose}",
            f"balls seen: {status['balls']}  obstacles: {status['obstacles']}",
            f"route nodes: {status['route_nodes']}  watchdog: {status['watchdog_resets']}",
            f"sim ticks: {self.world.tick_count}  speed: {self._speed:.2f}x",
        ]
        y = rect.top + 14
        for line in lines:
            text = self.font.render(line, True, (32, 32, 30))
            self.screen.blit(text, (rect.left + 14, y))
            y += 26
        hint = self.small_font.render("WASD move  Space clamp  H home  +/- speed  Q quit", True, (80, 80, 76))
        self.screen.blit(hint, (rect.left + 14, rect.bottom - 28))


__all__ = ["PygameVisualizer"]
