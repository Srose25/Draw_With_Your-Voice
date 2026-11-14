"""Validated immutable application settings for Draw With Your Voice."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import math
from typing import Literal


class SettingsValidationError(ValueError):
    """Raised when a settings update is invalid.

    ``category`` is stable so callers can distinguish type, range, enum,
    finite-value, and dependency failures without parsing the message.
    """

    def __init__(self, category: str, message: str) -> None:
        if category not in {"type", "range", "enum", "finite", "dependency"}:
            raise ValueError(f"unknown validation category: {category}")
        self.category = category
        super().__init__(message)


def _require_type(name: str, value: object, expected: type) -> None:
    if expected is int:
        valid = type(value) is int
    elif expected is float:
        valid = type(value) is float
    else:
        valid = type(value) is expected
    if not valid:
        raise SettingsValidationError("type", f"{name} must be {expected.__name__}")


def _finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise SettingsValidationError("finite", f"{name} must be finite")


def _range(name: str, value: float, low: float, high: float) -> None:
    if not low <= value <= high:
        raise SettingsValidationError("range", f"{name} must be in [{low}, {high}]")


@dataclass(frozen=True, slots=True)
class Settings:
    brush_size: int = 5
    brush_color: tuple[int, int, int] = (0, 0, 0)
    brush_style: Literal["round", "square"] = "round"
    particle_count: int = 1
    microphone_enabled: bool = True
    frequency_hz: float = 440.0
    volume: float = 0.5
    plate_shape: Literal["square", "circular"] = "square"
    square_n: int = 1
    square_m: int = 2
    circular_order: int = 0
    circular_root_index: int = 1
    circular_cosine_weight: float = 1.0
    circular_sine_weight: float = 0.0

    def __post_init__(self) -> None:
        _require_type("brush_size", self.brush_size, int)
        _range("brush_size", self.brush_size, 1, 50)

        if type(self.brush_color) is not tuple or len(self.brush_color) != 3:
            raise SettingsValidationError("type", "brush_color must be a 3-item tuple")
        for channel in self.brush_color:
            _require_type("brush_color channel", channel, int)
            _range("brush_color channel", channel, 0, 255)

        if type(self.brush_style) is not str:
            raise SettingsValidationError("type", "brush_style must be str")
        if self.brush_style not in ("round", "square"):
            raise SettingsValidationError("enum", "brush_style must be round or square")
        _require_type("particle_count", self.particle_count, int)
        _range("particle_count", self.particle_count, 1, 12)
        if type(self.microphone_enabled) is not bool:
            raise SettingsValidationError("type", "microphone_enabled must be bool")

        for name, value, low, high in (
            ("frequency_hz", self.frequency_hz, 60.0, 5000.0),
            ("volume", self.volume, 0.0, 1.0),
            ("circular_cosine_weight", self.circular_cosine_weight, -1.0, 1.0),
            ("circular_sine_weight", self.circular_sine_weight, -1.0, 1.0),
        ):
            _require_type(name, value, float)
            value = float(value)
            _finite(name, value)
            _range(name, value, low, high)

        if type(self.plate_shape) is not str:
            raise SettingsValidationError("type", "plate_shape must be str")
        if self.plate_shape not in ("square", "circular"):
            raise SettingsValidationError("enum", "plate_shape must be square or circular")
        for name, value, low, high in (
            ("square_n", self.square_n, 1, 8),
            ("square_m", self.square_m, 1, 8),
            ("circular_order", self.circular_order, 0, 8),
            ("circular_root_index", self.circular_root_index, 1, 8),
        ):
            _require_type(name, value, int)
            _range(name, value, low, high)

        if self.circular_cosine_weight == 0.0 and self.circular_sine_weight == 0.0:
            raise SettingsValidationError("range", "circular coefficient vector cannot be zero")

    def with_updates(self, **changes: object) -> "Settings":
        unknown = set(changes) - set(self.__dataclass_fields__)
        if unknown:
            raise SettingsValidationError("type", f"unknown settings: {sorted(unknown)}")
        return replace(self, **changes)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
