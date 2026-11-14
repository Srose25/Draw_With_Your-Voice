"""Bounded microphone analysis and manual sine-wave audio state."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.machinery
import importlib.util
import math
from pathlib import Path
import site
import sys
import threading
import time
from typing import Callable, Literal, Protocol

import numpy as np

from helpers import generate_sine_samples
from settings import Settings


Status = Literal["ok", "manual", "silent", "stale", "overflow", "device_error"]


@dataclass(frozen=True, slots=True)
class AudioSnapshot:
    frequency_hz: float
    amplitude: float
    volume: float
    sequence: int
    timestamp_monotonic: float
    status: Status


@dataclass(frozen=True, slots=True)
class PlaybackChunk:
    samples: bytes
    sample_rate: int
    channels: int
    sample_width: int
    frequency_hz: float
    volume: float
    sequence: int


class InputStreamLike(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


StreamFactory = Callable[[Callable[[object, object, object, object], None], int, int, int], InputStreamLike]


class MixerAdapter(Protocol):
    def initialize(self, sample_rate: int, channels: int, sample_width: int) -> None: ...
    def submit(self, chunk: PlaybackChunk) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


def _default_stream_factory(callback: Callable[[object, object, object, object], None], sample_rate: int, channels: int, block_size: int) -> InputStreamLike:
    """Create the external sounddevice stream, never the vendored example tree."""
    try:
        current = sys.modules.get("sounddevice")
        current_origin = getattr(current, "__file__", "") if current is not None else ""
        project_vendor = Path(__file__).resolve().parent / "sounddevice"
        if current is not None and current_origin and project_vendor in Path(current_origin).resolve().parents:
            del sys.modules["sounddevice"]
        search_paths = [path for path in site.getsitepackages() if path]
        spec = importlib.machinery.PathFinder.find_spec("sounddevice", search_paths)
        if spec is None or spec.loader is None or not spec.origin:
            raise ImportError("external sounddevice package not found")
        sounddevice = importlib.util.module_from_spec(spec)
        sys.modules["sounddevice"] = sounddevice
        spec.loader.exec_module(sounddevice)
        stream_type = getattr(sounddevice, "InputStream")
    except BaseException as exc:
        raise RuntimeError("external sounddevice InputStream is unavailable") from exc
    return stream_type(samplerate=sample_rate, channels=channels, blocksize=block_size, dtype="float32", callback=callback)


def _status_text(status: object) -> str:
    return str(status).lower() if status else ""


class AudioProducer:
    """Latest-only audio producer with a fakeable stream boundary."""

    def __init__(
        self,
        settings: Settings,
        *,
        stream_factory: StreamFactory | None = None,
        clock: Callable[[], float] = time.monotonic,
        sample_rate: int = 48_000,
        channels: int = 1,
        block_size: int = 512,
        fft_size: int = 512,
    ) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("settings must be Settings")
        if type(sample_rate) is not int or sample_rate <= 0:
            raise ValueError("sample_rate must be a positive integer")
        if type(channels) is not int or channels <= 0:
            raise ValueError("channels must be a positive integer")
        if type(block_size) is not int or block_size <= 0:
            raise ValueError("block_size must be a positive integer")
        if type(fft_size) is not int or fft_size <= 0:
            raise ValueError("fft_size must be a positive integer")
        if not callable(clock):
            raise TypeError("clock must be callable")

        self._settings = settings
        self._stream_factory = stream_factory or _default_stream_factory
        self._clock = clock
        self._sample_rate = sample_rate
        self._channels = channels
        self._block_size = block_size
        self._fft_size = fft_size
        self._lock = threading.RLock()
        self._pending_frame: np.ndarray | None = None
        self._pending_event = threading.Event()
        self._stop_event = threading.Event()
        self._stream: InputStreamLike | None = None
        self._thread: threading.Thread | None = None
        self._started = False
        self._worker_error: BaseException | None = None
        self._sequence = 0
        self._ever_started = False
        self._playback_phase = 0.0
        self._playback_sequence = 0
        self._last_valid = (settings.frequency_hz, 0.0, settings.volume)
        self._last_valid_timestamp = float(clock())
        self._last_snapshot_timestamp = self._last_valid_timestamp
        self._stale_emitted_for: float | None = None
        initial_status: Status = "manual" if not settings.microphone_enabled else "silent"
        self._latest = AudioSnapshot(
            settings.frequency_hz,
            0.0,
            settings.volume,
            0,
            self._last_valid_timestamp,
            initial_status,
        )

    @property
    def worker_error(self) -> BaseException | None:
        with self._lock:
            return self._worker_error

    def latest_snapshot(self) -> AudioSnapshot:
        with self._lock:
            if (
                self._settings.microphone_enabled
                and self._latest.status != "manual"
                and self._clock() - self._last_snapshot_timestamp > 0.25
                and self._stale_emitted_for != self._last_snapshot_timestamp
            ):
                self._stale_emitted_for = self._last_snapshot_timestamp
                self._publish("stale")
            return self._latest

    def _publish(self, status: Status, *, frequency: float | None = None, amplitude: float | None = None, volume: float | None = None) -> AudioSnapshot:
        with self._lock:
            if status in ("ok", "manual"):
                assert frequency is not None and amplitude is not None and volume is not None
                self._last_valid = (frequency, amplitude, volume)
                self._last_valid_timestamp = float(self._clock())
                self._stale_emitted_for = None
            frequency_value, amplitude_value, volume_value = self._last_valid
            self._sequence += 1
            snapshot = AudioSnapshot(
                float(frequency_value if frequency is None else frequency),
                float(amplitude_value if amplitude is None else amplitude),
                float(volume_value if volume is None else volume),
                self._sequence,
                float(self._clock()),
                status,
            )
            self._latest = snapshot
            self._last_snapshot_timestamp = snapshot.timestamp_monotonic
            return snapshot

    def _callback(self, indata: object, frames: int | None = None, time_info: object = None, status: object = None) -> None:
        del frames, time_info
        with self._lock:
            if not self._started or self._stop_event.is_set():
                return
        status_value = _status_text(status)
        if status_value:
            self._publish("overflow" if "overflow" in status_value else "device_error")
            return
        declared_shape = getattr(indata, "shape", None)
        declared_size = getattr(indata, "size", None)
        if declared_shape is not None:
            try:
                valid_shape = (
                    (len(declared_shape) == 1 and int(declared_shape[0]) <= self._block_size)
                    or (len(declared_shape) == 2 and int(declared_shape[0]) <= self._block_size and int(declared_shape[1]) <= 8)
                )
                if not valid_shape or int(declared_size) <= 0:
                    self._publish("device_error")
                    return
            except (TypeError, ValueError, OverflowError):
                self._publish("device_error")
                return
        elif isinstance(indata, (list, tuple)) and (not indata or len(indata) > self._block_size):
            self._publish("device_error")
            return
        try:
            frame = np.asarray(indata, dtype=np.float64)
            if frame.ndim not in (1, 2) or frame.size == 0 or not np.all(np.isfinite(frame)):
                self._publish("device_error")
                return
            frame = np.array(frame, dtype=np.float64, copy=True)
        except (TypeError, ValueError, OverflowError):
            self._publish("device_error")
            return
        with self._lock:
            if not self._started or self._stop_event.is_set():
                return
            self._pending_frame = frame
            self._pending_event.set()

    def _process_frame(self, frame: np.ndarray) -> None:
        try:
            if frame.ndim == 2:
                samples = np.mean(frame, axis=1)
            elif frame.ndim == 1:
                samples = frame
            else:
                raise ValueError("audio frame must be one- or two-dimensional")
            if samples.size != self._fft_size or not np.all(np.isfinite(samples)):
                raise ValueError("audio frame has invalid length or values")
            spectrum = np.abs(np.fft.rfft(samples))
            maximum = float(np.max(spectrum))
            tie_tolerance = 1e-12 * max(1.0, maximum)
            tied = np.flatnonzero(np.abs(spectrum - maximum) <= tie_tolerance)
            bin_index = int(tied[0])
            magnitude = float(spectrum[bin_index])
            amplitude = magnitude / self._fft_size if bin_index == 0 else 2.0 * magnitude / self._fft_size
            amplitude = min(1.0, max(0.0, amplitude))
            frequency = bin_index * self._sample_rate / self._fft_size
            if amplitude < 1e-3:
                self._publish("silent")
            elif not 60.0 <= frequency <= 5000.0:
                self._publish("device_error")
            else:
                self._publish("ok", frequency=frequency, amplitude=amplitude, volume=amplitude)
        except (TypeError, ValueError, FloatingPointError, OverflowError):
            self._publish("device_error")

    def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                self._pending_event.wait(0.1)
                if self._stop_event.is_set():
                    break
                with self._lock:
                    frame = self._pending_frame
                    self._pending_frame = None
                    self._pending_event.clear()
                if frame is not None:
                    self._process_frame(frame)
        except BaseException as exc:
            with self._lock:
                if self._worker_error is None:
                    self._worker_error = exc
                self._settings = self._settings.with_updates(microphone_enabled=False)
            self._stop_event.set()
            try:
                self._publish("device_error")
            except BaseException:
                pass

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            if self._ever_started:
                raise RuntimeError("a stopped audio producer cannot be restarted")
            self._ever_started = True
            self._started = True
            self._stop_event.clear()
            self._pending_event.clear()
            if not self._settings.microphone_enabled:
                return
            try:
                self._stream = self._stream_factory(
                    self._callback,
                    self._sample_rate,
                    self._channels,
                    self._block_size,
                )
                self._stream.start()
                self._thread = threading.Thread(target=self._run, name="audio-producer", daemon=False)
                self._thread.start()
            except BaseException as exc:
                self._worker_error = self._worker_error or exc
                self._settings = self._settings.with_updates(microphone_enabled=False)
                stream = self._stream
                self._stream = None
                self._started = False
                self._publish("device_error")
                if stream is not None:
                    try:
                        stream.close()
                    except BaseException:
                        pass

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            self._pending_event.set()
            self._pending_frame = None
            stream = self._stream
            self._stream = None
            self._started = False
        stream_error: BaseException | None = None
        if stream is not None:
            try:
                stream.stop()
            except BaseException as exc:
                stream_error = exc
            finally:
                try:
                    stream.close()
                except BaseException as exc:
                    stream_error = stream_error or exc
        if stream_error is not None:
            with self._lock:
                self._worker_error = self._worker_error or stream_error
                self._settings = self._settings.with_updates(microphone_enabled=False)
            self._publish("device_error")
        self.join(1.0)
        with self._lock:
            self._pending_event.clear()

    def join(self, timeout: float = 1.0) -> bool:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(float(timeout)) or timeout < 0:
            raise ValueError("timeout must be a non-negative finite number")
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        if thread is threading.current_thread():
            return False
        thread.join(float(timeout))
        with self._lock:
            if not thread.is_alive():
                self._thread = None
            return not thread.is_alive()

    def update_settings(self, settings: Settings) -> None:
        if not isinstance(settings, Settings):
            raise TypeError("settings must be Settings")
        with self._lock:
            was_microphone_enabled = self._settings.microphone_enabled
            self._settings = settings
            microphone_enabled = settings.microphone_enabled
            if microphone_enabled and not was_microphone_enabled:
                self._last_valid_timestamp = float(self._clock())
                self._stale_emitted_for = None
        if not microphone_enabled:
            self._publish("manual", frequency=settings.frequency_hz, amplitude=0.0, volume=settings.volume)
        elif not was_microphone_enabled:
            self._publish("silent")

    def next_playback_chunk(self) -> PlaybackChunk | None:
        with self._lock:
            settings = self._settings
            if settings.microphone_enabled or settings.volume <= 0.0:
                return None
            frequency = settings.frequency_hz
            volume = settings.volume
            phase = self._playback_phase
            sequence = self._playback_sequence + 1
            self._playback_sequence = sequence
        samples = generate_sine_samples(frequency, self._sample_rate, self._block_size, amplitude=volume, phase=phase)
        values = np.asarray(np.rint(np.asarray(samples) * 32767.0), dtype="<i2")
        phase = (phase + 2.0 * math.pi * frequency * self._block_size / self._sample_rate) % (2.0 * math.pi)
        with self._lock:
            self._playback_phase = phase
        return PlaybackChunk(values.tobytes(), self._sample_rate, 1, 2, frequency, volume, sequence)
