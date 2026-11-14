import math

import pytest

from settings import Settings, SettingsValidationError


def test_defaults_cover_every_field():
    assert Settings().to_dict() == {
        "brush_size": 5, "brush_color": (0, 0, 0), "brush_style": "round",
        "particle_count": 1, "microphone_enabled": True, "frequency_hz": 440.0,
        "volume": 0.5, "plate_shape": "square", "square_n": 1, "square_m": 2,
        "circular_order": 0, "circular_root_index": 1,
        "circular_cosine_weight": 1.0, "circular_sine_weight": 0.0,
    }


def test_valid_update_covers_every_field_and_is_immutable():
    original = Settings()
    updated = original.with_updates(
        brush_size=12, brush_color=(1, 2, 3), brush_style="square",
        particle_count=12, microphone_enabled=False, frequency_hz=880.0,
        volume=0.25, plate_shape="circular", square_n=8, square_m=7,
        circular_order=8, circular_root_index=8,
        circular_cosine_weight=0.6, circular_sine_weight=0.8,
    )
    assert original.brush_size == 5
    assert updated.to_dict()["particle_count"] == 12
    assert updated.to_dict()["plate_shape"] == "circular"


@pytest.mark.parametrize("field,value", [
    ("brush_size", True), ("brush_color", [0, 0, 0]), ("brush_style", 1),
    ("particle_count", False), ("microphone_enabled", 1),
    ("frequency_hz", 440), ("volume", 1), ("plate_shape", 1),
    ("square_n", 1.0), ("square_m", True), ("circular_order", 1.0),
    ("circular_root_index", True), ("circular_cosine_weight", 1),
    ("circular_sine_weight", "0"),
])
def test_rejects_wrong_types(field, value):
    with pytest.raises(SettingsValidationError) as error:
        Settings().with_updates(**{field: value})
    assert error.value.category == "type"


@pytest.mark.parametrize("field,value", [
    ("brush_size", 0), ("brush_size", 51), ("brush_color", (0, 0, 256)),
    ("particle_count", 0), ("particle_count", 13), ("frequency_hz", 59.9),
    ("frequency_hz", 5000.1), ("volume", -0.1), ("volume", 1.1),
    ("square_n", 0), ("square_m", 9), ("circular_order", -1),
    ("circular_order", 9), ("circular_root_index", 0),
    ("circular_root_index", 9), ("circular_cosine_weight", -1.1),
    ("circular_sine_weight", 1.1),
])
def test_rejects_wrong_ranges(field, value):
    with pytest.raises(SettingsValidationError) as error:
        Settings().with_updates(**{field: value})
    assert error.value.category == "range"


@pytest.mark.parametrize("field,value", [("brush_style", "ink"), ("plate_shape", "triangle")])
def test_rejects_invalid_enums(field, value):
    with pytest.raises(SettingsValidationError) as error:
        Settings().with_updates(**{field: value})
    assert error.value.category == "enum"


@pytest.mark.parametrize("field,value", [
    ("frequency_hz", math.nan), ("frequency_hz", math.inf), ("volume", math.nan),
    ("circular_cosine_weight", math.inf), ("circular_sine_weight", -math.inf),
])
def test_rejects_non_finite_values(field, value):
    with pytest.raises(SettingsValidationError) as error:
        Settings().with_updates(**{field: value})
    assert error.value.category == "finite"


def test_rejects_zero_circular_weight_vector_and_unknown_field():
    with pytest.raises(SettingsValidationError) as error:
        Settings().with_updates(circular_cosine_weight=0.0, circular_sine_weight=0.0)
    assert error.value.category == "range"
    with pytest.raises(SettingsValidationError) as error:
        Settings().with_updates(unknown_field=1)
    assert error.value.category == "type"
