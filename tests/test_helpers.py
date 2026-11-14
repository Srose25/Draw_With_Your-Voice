from dataclasses import FrozenInstanceError
import math

import pygame
import pytest

from helpers import (
    LayoutState, begin_layout, cancel_layout, clear_canvas, commit_layout,
    draw_particle_marker, draw_stroke, generate_sine_samples, particle_layout,
)


GOLDEN = {
    1: ((400, 206),), 2: ((400, 206), (400, 490)),
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


@pytest.mark.parametrize("count", range(1, 13))
def test_golden_layouts(count):
    assert particle_layout(count, 800, 600) == GOLDEN[count]


def test_layout_scaling_preserves_arrangement():
    scaled = particle_layout(5, 1600, 1200)
    assert len(scaled) == len(GOLDEN[5])
    # Marker-radius inset changes the affine scale; compare normalized positions.
    for (x, y), (sx, sy) in zip(GOLDEN[5], scaled):
        canonical_x = (x - 38) / (762 - 38)
        canonical_y = (y - 118) / (578 - 118)
        actual_x = (sx - 70) / (1530 - 70)
        actual_y = (sy - 230) / (1162 - 230)
        assert actual_x == pytest.approx(canonical_x, abs=0.002)
        assert actual_y == pytest.approx(canonical_y, abs=0.002)


def test_layout_transaction_generations_and_immutability():
    previous = LayoutState("committed", GOLDEN[1], 4, False)
    pending = begin_layout(2, 800, 600, current_generation=previous.generation)
    assert pending.generation == 5 and pending.simulation_paused
    with pytest.raises(FrozenInstanceError):
        pending.generation = 99
    committed = commit_layout(pending)
    assert committed.generation == 5 and not committed.simulation_paused
    pending2 = begin_layout(3, 800, 600, committed.generation)
    assert commit_layout(pending2).generation == 6
    assert cancel_layout(pending2, committed) is committed


def test_layout_invalid_transitions():
    committed = LayoutState("committed", GOLDEN[1], 1, False)
    pending = begin_layout(2, 800, 600, 1)
    with pytest.raises(ValueError):
        commit_layout(committed)
    with pytest.raises(ValueError):
        cancel_layout(committed, committed)
    with pytest.raises(ValueError):
        begin_layout(1, 800, 600, -1)
    with pytest.raises(ValueError):
        commit_layout(LayoutState("pending", GOLDEN[1], 1, False))
    assert pending.status == "pending"


def test_alternate_layout_and_invalid_dimensions():
    points = particle_layout(3, 1600, 1200)
    assert len(points) == 3
    assert all(0 <= x <= 1600 and 0 <= y <= 1200 for x, y in points)
    with pytest.raises(ValueError):
        particle_layout(1, 10, 10)
    with pytest.raises(ValueError):
        particle_layout(13, 800, 600)


def test_headless_drawing_clear_polyline_and_clipping():
    surface = pygame.Surface((40, 40))
    clear_canvas(surface)
    assert surface.get_at((0, 0))[:3] == (255, 255, 255)
    draw_stroke(surface, [(2, 35), (20, 5), (37, 35)], (0, 0, 0), 3, "round")
    assert surface.get_at((20, 5))[:3] == (0, 0, 0)
    draw_stroke(surface, [(-10, 20), (10, 20), (50, 20)], (255, 0, 0), 5, "square")
    assert surface.get_at((0, 20))[:3] == (255, 0, 0)
    assert surface.get_at((10, 20))[:3] == (255, 0, 0)


def test_round_and_square_caps_differ():
    round_surface = pygame.Surface((30, 20))
    square_surface = pygame.Surface((30, 20))
    round_surface.fill((255, 255, 255))
    square_surface.fill((255, 255, 255))
    draw_stroke(round_surface, [(10, 10), (20, 10)], (0, 0, 0), 6, "round")
    draw_stroke(square_surface, [(10, 10), (20, 10)], (0, 0, 0), 6, "square")
    assert round_surface.get_at((10, 7))[:3] == (0, 0, 0)
    assert square_surface.get_at((7, 7))[:3] == (0, 0, 0)


def test_hollow_marker_geometry():
    surface = pygame.Surface((40, 40))
    surface.fill((255, 255, 255))
    draw_particle_marker(surface, (20, 30), (0, 0, 255), 6)
    assert surface.get_at((20, 30))[:3] == (255, 255, 255)
    assert surface.get_at((20, 24))[:3] == (0, 0, 255)
    assert surface.get_at((20, 23))[:3] == (255, 255, 255)


def test_sine_phase_amplitude_zero_frequency_and_no_duplicate_endpoint():
    assert generate_sine_samples(0.0, 1000, 3, amplitude=0.5, phase=math.pi / 2) == pytest.approx((0.5, 0.5, 0.5))
    samples = generate_sine_samples(250.0, 1000, 4)
    assert samples == pytest.approx((0.0, 1.0, 0.0, -1.0), abs=1e-9)
    assert samples[0] != samples[-1]
    assert len(generate_sine_samples(100, 1000, 0)) == 0
    for args in [(100, 0, 1), (100, 1000, -1), (math.nan, 1000, 1), (100, 1000, 1, 1.1), (100, 1000, 1, 1.0, math.inf)]:
        with pytest.raises(ValueError):
            generate_sine_samples(*args)
