"""Pure particle equations, deterministic motion, and worker lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
import math
import threading
import time
from typing import Callable, Literal, Protocol

from settings import Settings

try:  # SciPy is an approved runtime dependency for circular modes.
    from scipy.special import jn_zeros, jv
except ImportError as exc:  # pragma: no cover - exercised by import-isolation tests
    jn_zeros = None  # type: ignore[assignment]
    jv = None  # type: ignore[assignment]
    _SCIPY_IMPORT_ERROR: ImportError | None = exc
else:
    _SCIPY_IMPORT_ERROR = None


Status = Literal["ok", "manual", "silent", "stale", "overflow", "device_error"]


class AudioSnapshotLike(Protocol):
    """Structural boundary for the runtime AudioSnapshot owned by Task_005."""

    frequency_hz: float
    amplitude: float
    volume: float
    sequence: int
    timestamp_monotonic: float
    status: Status


@dataclass(frozen=True, slots=True)
class ParticleSnapshot:
    position: tuple[float, float]
    velocity: tuple[float, float]
    anchor: tuple[float, float]
    color: tuple[int, int, int]
    brush_size: int
    brush_style: Literal["round", "square"]
    last_valid_position: tuple[float, float]
    error: str | None


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def square_value(x: float, y: float, n: int, m: int) -> float:
    x = _finite_number(x, "x")
    y = _finite_number(y, "y")
    if not -1.0 <= x <= 1.0 or not -1.0 <= y <= 1.0:
        raise ValueError("square coordinates must be in [-1, 1]")
    if type(n) is not int or type(m) is not int or not 1 <= n <= 8 or not 1 <= m <= 8:
        raise ValueError("square modes must be integers in [1, 8]")
    n, m = sorted((n, m))
    if n == m:
        return 0.0
    u, v = (x + 1.0) / 2.0, (y + 1.0) / 2.0
    return (
        math.cos(n * math.pi * u) * math.cos(m * math.pi * v)
        - math.cos(m * math.pi * u) * math.cos(n * math.pi * v)
    )


def circular_value(
    r: float,
    theta: float,
    order: int,
    root_index: int,
    cosine_weight: float,
    sine_weight: float,
) -> float:
    r = _finite_number(r, "r")
    theta = _finite_number(theta, "theta")
    cosine_weight = _finite_number(cosine_weight, "cosine_weight")
    sine_weight = _finite_number(sine_weight, "sine_weight")
    if not 0.0 <= r <= 1.0:
        raise ValueError("r must be in [0, 1]")
    if type(order) is not int or not 0 <= order <= 8:
        raise ValueError("order must be an integer in [0, 8]")
    if type(root_index) is not int or not 1 <= root_index <= 8:
        raise ValueError("root_index must be an integer in [1, 8]")
    if not -1.0 <= cosine_weight <= 1.0 or not -1.0 <= sine_weight <= 1.0:
        raise ValueError("circular weights must be in [-1, 1]")
    norm = math.hypot(cosine_weight, sine_weight)
    if norm == 0.0:
        raise ValueError("circular coefficient vector cannot be zero")
    if _SCIPY_IMPORT_ERROR is not None or jv is None or jn_zeros is None:
        raise RuntimeError("SciPy is unavailable for circular evaluation") from _SCIPY_IMPORT_ERROR
    k = float(jn_zeros(order, root_index)[root_index - 1])
    angular = (
        (cosine_weight / norm) * math.cos(order * theta)
        + (sine_weight / norm) * math.sin(order * theta)
    )
    return float(jv(order, k * r)) * angular


def _reflect(value: float, velocity: float, low: float, high: float) -> tuple[float, float]:
    length = high - low
    period = 2.0 * length
    folded = (value - low) % period
    if folded <= length:
        position = low + folded
        odd_reflection = False
    else:
        position = high - (folded - length)
        odd_reflection = True
    return position, -velocity if odd_reflection else velocity


class Particle:
    """One Pygame-independent particle with an optional simulation worker."""

    def __init__(
        self,
        anchor: tuple[float, float],
        bounds: tuple[float, float, float, float],
        settings: Settings,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if type(anchor) is not tuple or len(anchor) != 2:
            raise ValueError("anchor must be a two-item tuple")
        anchor_value = tuple(_finite_number(v, "anchor") for v in anchor)
        if type(bounds) is not tuple or len(bounds) != 4:
            raise ValueError("bounds must be (left, top, right, bottom)")
        bound_values = tuple(_finite_number(v, "bound") for v in bounds)
        left, top, right, bottom = bound_values
        if not left < right or not top < bottom:
            raise ValueError("bounds must have positive area")
        if not left <= anchor_value[0] <= right or not top <= anchor_value[1] <= bottom:
            raise ValueError("anchor must be inside bounds")
        if not isinstance(settings, Settings):
            raise TypeError("settings must be Settings")
        if not callable(clock):
            raise TypeError("clock must be callable")

        self._anchor = (anchor_value[0], anchor_value[1])
        self._bounds = (left, top, right, bottom)
        self._settings = settings
        self._position = self._anchor
        self._velocity = (0.0, 0.0)
        self._last_valid_position = self._anchor
        self._error: str | None = None
        self._audio: tuple[float, float, float, int, float, Status] | None = None
        self._audio_sequence: int | None = None
        self._clock = clock
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._worker_error: BaseException | None = None
        self._ever_started = False
        self._last_tick: float | None = None

    @property
    def worker_error(self) -> BaseException | None:
        with self._lock:
            return self._worker_error

    def update_from_audio(self, snapshot: AudioSnapshotLike) -> None:
        required = ("frequency_hz", "amplitude", "volume", "sequence", "timestamp_monotonic", "status")
        try:
            values = {name: getattr(snapshot, name) for name in required}
            frequency = _finite_number(values["frequency_hz"], "frequency_hz")
            amplitude = _finite_number(values["amplitude"], "amplitude")
            volume = _finite_number(values["volume"], "volume")
            sequence = values["sequence"]
            timestamp = _finite_number(values["timestamp_monotonic"], "timestamp_monotonic")
            status = values["status"]
            if type(sequence) is not int or sequence < 0:
                raise ValueError("sequence must be a non-negative integer")
            if not 0.0 <= amplitude <= 1.0 or not 0.0 <= volume <= 1.0:
                raise ValueError("audio amplitude and volume must be in [0, 1]")
            if status not in ("ok", "manual"):
                return
            if self._clock() - timestamp > 0.25:
                return
        except (AttributeError, TypeError, ValueError):
            return
        with self._lock:
            if self._audio_sequence is not None and sequence <= self._audio_sequence:
                return
            self._audio = (frequency, amplitude, volume, sequence, timestamp, status)
            self._audio_sequence = sequence

    def update_settings(self, settings: Settings) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("settings must be Settings")
        with self._lock:
            self._settings = settings

    def _inputs(self) -> tuple[float, float]:
        settings = self._settings
        if not settings.microphone_enabled:
            return settings.frequency_hz, settings.volume
        if self._audio is not None:
            frequency, _amplitude, volume, _sequence, _timestamp, _status = self._audio
            return frequency, volume
        return settings.frequency_hz, settings.volume

    def _field(self, x: float, y: float) -> float:
        left, top, right, bottom = self._bounds
        center_x, center_y = (left + right) / 2.0, (top + bottom) / 2.0
        x_screen = 2.0 * (x - center_x) / (right - left)
        y_screen = 2.0 * (y - center_y) / (bottom - top)
        x_equation, y_equation = x_screen, -y_screen
        if self._settings.plate_shape == "square":
            return square_value(x_equation, y_equation, self._settings.square_n, self._settings.square_m)
        radius = math.hypot(x_equation, y_equation) / math.sqrt(2.0)
        theta = math.atan2(y_equation, x_equation)
        if theta == math.pi:
            theta = -math.pi
        return circular_value(
            radius,
            theta,
            self._settings.circular_order,
            self._settings.circular_root_index,
            self._settings.circular_cosine_weight,
            self._settings.circular_sine_weight,
        )

    def step(self, dt: float) -> ParticleSnapshot:
        with self._lock:
            try:
                dt = _finite_number(dt, "dt")
                dt = min(0.1, max(0.0, dt))
                field_value = self._field(*self._position)
                if not math.isfinite(field_value):
                    raise ValueError("non-finite field value")
                frequency, volume = self._inputs()
                field_scale = 2.0 if self._settings.plate_shape == "square" else 1.0
                field_norm = min(1.0, max(-1.0, field_value / field_scale))
                if not math.isfinite(field_norm):
                    raise ValueError("non-finite normalized field")
                frequency_norm = min(1.0, max(0.0, (frequency - 60.0) / 4940.0))
                speed = 60.0 + 180.0 * frequency_norm
                dx = self._anchor[0] - (self._bounds[0] + self._bounds[2]) / 2.0
                dy = self._anchor[1] - (self._bounds[1] + self._bounds[3]) / 2.0
                radial_length = math.hypot(dx, dy)
                radial = (1.0, 0.0) if radial_length == 0.0 else (dx / radial_length, dy / radial_length)
                target = (radial[0] * speed * volume * field_norm, radial[1] * speed * volume * field_norm)
                candidate = (self._position[0] + self._velocity[0] * dt, self._position[1] + self._velocity[1] * dt)
                reflected_x, velocity_x = _reflect(candidate[0], self._velocity[0], self._bounds[0], self._bounds[2])
                reflected_y, velocity_y = _reflect(candidate[1], self._velocity[1], self._bounds[1], self._bounds[3])
                if not all(math.isfinite(v) for v in (*target, reflected_x, reflected_y, velocity_x, velocity_y)):
                    raise ValueError("non-finite particle update")
                alpha = min(1.0, dt * 12.0)
                self._position = (reflected_x, reflected_y)
                self._velocity = (
                    velocity_x + alpha * (target[0] - velocity_x),
                    velocity_y + alpha * (target[1] - velocity_y),
                )
                self._last_valid_position = self._position
                self._error = None
            except (ValueError, RuntimeError, OverflowError) as exc:
                self._position = self._last_valid_position
                self._velocity = self._velocity if all(math.isfinite(v) for v in self._velocity) else (0.0, 0.0)
                self._error = str(exc)
            return self._snapshot_locked()

    def _snapshot_locked(self) -> ParticleSnapshot:
        settings = self._settings
        return ParticleSnapshot(
            self._position,
            self._velocity,
            self._anchor,
            settings.brush_color,
            settings.brush_size,
            settings.brush_style,
            self._last_valid_position,
            self._error,
        )

    def snapshot(self) -> ParticleSnapshot:
        with self._lock:
            return self._snapshot_locked()

    def _run(self) -> None:
        try:
            self._last_tick = self._clock()
            while not self._stop_event.is_set():
                now = self._clock()
                previous = self._last_tick
                self._last_tick = now
                self.step(0.0 if previous is None else now - previous)
                self._stop_event.wait(0.01)
        except BaseException as exc:  # worker failures must be observable and stop the worker
            with self._lock:
                if self._worker_error is None:
                    self._worker_error = exc
            self._stop_event.set()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            if self._ever_started or self._stop_event.is_set():
                raise RuntimeError("a stopped particle cannot be restarted")
            self._ever_started = True
            self._thread = threading.Thread(target=self._run, name="particle-worker", daemon=False)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: float = 1.0) -> bool:
        timeout = _finite_number(timeout, "timeout")
        if timeout < 0.0:
            raise ValueError("timeout must be non-negative")
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        if thread is threading.current_thread():
            return False
        thread.join(timeout)
        with self._lock:
            return not thread.is_alive()
