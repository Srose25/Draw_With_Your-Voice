"""Pure layout/math helpers and UI-thread-only surface drawing helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Sequence

import pygame


_CANONICAL_WIDTH = 800
_CANONICAL_HEIGHT = 600
_CANONICAL_INNER = (38, 118, 762, 578)
_GOLDEN: dict[int, tuple[tuple[int, int], ...]] = {
    1: ((400, 206),),
    2: ((400, 206), (400, 490)),
    3: ((400, 206), (591, 419), (209, 419)),
    4: ((556, 448), (244, 448), (244, 248), (556, 248)),
    5: ((400, 206), (610, 304), (530, 463), (270, 463), (190, 304)),
    6: ((400, 206), (591, 277), (591, 419), (400, 490), (209, 419), (209, 277)),
    7: ((400, 206), (591, 277), (591, 419), (400, 490), (209, 419), (209, 277), (400, 348)),
    8: ((400, 206), (556, 248), (621, 348), (556, 448), (400, 490), (244, 448), (179, 348), (244, 248)),
    9: ((400, 206), (610, 304), (530, 463), (270, 463), (190, 304), (478, 398), (322, 398), (322, 298), (478, 298)),
    10: ((400, 206), (610, 304), (530, 463), (270, 463), (190, 304), (400, 277), (505, 326), (465, 405), (335, 405), (295, 326)),
    11: ((400, 206), (591, 277), (591, 419), (400, 490), (209, 419), (209, 277), (400, 277), (505, 326), (465, 405), (335, 405), (295, 326)),
    12: ((556, 448), (244, 448), (244, 248), (556, 248), (544, 348), (400, 440), (256, 348), (400, 256), (447, 378), (353, 378), (353, 318), (447, 318)),
}


@dataclass(frozen=True, slots=True)
class LayoutState:
    status: Literal["pending", "committed"]
    points: tuple[tuple[int, int], ...]
    generation: int
    simulation_paused: bool


def _validate_layout_args(count: int, width: int, height: int, marker_radius: int) -> None:
    if type(count) is not int or not 1 <= count <= 12:
        raise ValueError("count must be an integer from 1 through 12")
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("width and height must be positive integers")
    if type(marker_radius) is not int or marker_radius < 0:
        raise ValueError("marker_radius must be a non-negative integer")
    left, top = round(32 * width / 800), round(112 * height / 600)
    right, bottom = round(768 * width / 800), round(584 * height / 600)
    if right - left <= 2 * marker_radius or bottom - top <= 2 * marker_radius:
        raise ValueError("drawable area is too small for marker radius")


def particle_layout(count: int, width: int, height: int, marker_radius: int = 6) -> tuple[tuple[int, int], ...]:
    _validate_layout_args(count, width, height, marker_radius)
    if width == 800 and height == 600 and marker_radius == 6:
        return _GOLDEN[count]

    left, top = round(32 * width / 800), round(112 * height / 600)
    right, bottom = round(768 * width / 800), round(584 * height / 600)
    il, it = left + marker_radius, top + marker_radius
    ir, ib = right - marker_radius, bottom - marker_radius
    cl, ct, cr, cb = _CANONICAL_INNER
    return tuple(
        (
            round(il + (x - cl) * (ir - il) / (cr - cl)),
            round(it + (y - ct) * (ib - it) / (cb - ct)),
        )
        for x, y in _GOLDEN[count]
    )


def begin_layout(count: int, width: int, height: int, current_generation: int = 0) -> LayoutState:
    if type(current_generation) is not int or current_generation < 0:
        raise ValueError("current_generation must be a non-negative integer")
    return LayoutState("pending", particle_layout(count, width, height), current_generation + 1, True)


def commit_layout(pending: LayoutState) -> LayoutState:
    if pending.status != "pending" or not pending.simulation_paused:
        raise ValueError("commit requires a pending paused layout")
    return LayoutState("committed", pending.points, pending.generation, False)


def cancel_layout(pending: LayoutState, previous: LayoutState) -> LayoutState:
    if pending.status != "pending" or not pending.simulation_paused:
        raise ValueError("cancel requires a pending paused layout")
    if previous.status != "committed" or previous.simulation_paused:
        raise ValueError("previous layout must be committed and unpaused")
    return previous


def _validate_color(color: tuple[int, int, int]) -> None:
    if type(color) is not tuple or len(color) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
        raise ValueError("color must be a 3-item RGB tuple")


def draw_stroke(surface: pygame.Surface, points: Sequence[tuple[int, int]], color: tuple[int, int, int], size: int, style: str) -> None:
    _validate_color(color)
    if type(size) is not int or size < 1:
        raise ValueError("size must be a positive integer")
    if style not in ("round", "square"):
        raise ValueError("style must be round or square")
    if not points:
        return
    if len(points) == 1:
        x, y = points[0]
        if style == "round":
            pygame.draw.circle(surface, color, (x, y), size // 2)
        else:
            pygame.draw.rect(surface, color, pygame.Rect(x - size // 2, y - size // 2, size, size))
        return
    pygame.draw.lines(surface, color, False, list(points), size)
    if style == "round":
        radius = size // 2
        pygame.draw.circle(surface, color, points[0], radius)
        pygame.draw.circle(surface, color, points[-1], radius)
    else:
        half = size // 2
        for x, y in (points[0], points[-1]):
            pygame.draw.rect(surface, color, pygame.Rect(x - half, y - half, size, size))


def draw_particle_marker(surface: pygame.Surface, position: tuple[int, int], color: tuple[int, int, int], radius: int) -> None:
    _validate_color(color)
    if type(radius) is not int or radius < 2:
        raise ValueError("radius must be an integer of at least 2")
    pygame.draw.circle(surface, color, position, radius, width=2)


def clear_canvas(surface: pygame.Surface, background: tuple[int, int, int] = (255, 255, 255)) -> None:
    _validate_color(background)
    surface.fill(background)


def generate_sine_samples(frequency_hz: float, sample_rate: int, length: int, amplitude: float = 1.0, phase: float = 0.0) -> tuple[float, ...]:
    values = (frequency_hz, amplitude, phase)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
        raise ValueError("frequency, amplitude, and phase must be numeric")
    if any(not math.isfinite(float(v)) for v in values):
        raise ValueError("frequency, amplitude, and phase must be finite")
    if type(sample_rate) is not int or sample_rate <= 0:
        raise ValueError("sample_rate must be a positive integer")
    if type(length) is not int or length < 0:
        raise ValueError("length must be a non-negative integer")
    if not 0.0 <= float(amplitude) <= 1.0:
        raise ValueError("amplitude must be in [0, 1]")
    return tuple(float(amplitude) * math.sin(2.0 * math.pi * float(frequency_hz) * i / sample_rate + float(phase)) for i in range(length))
