# Task_005 — Implement audio producer and fallback input

## Scope

Implement `audio_producer.py` with microphone capture integration, FFT snapshots, thread-safe handoff, graceful device failure, and sine-wave/manual fallback based on approved contracts and `sound_device_essentials.md`.

## Planned files and interfaces

- `audio_producer.py`: an `AudioProducer` with `start()`, `stop()`, `latest_snapshot()`, and a callback handoff publishing a bounded latest-value `AudioSnapshot` containing frequency, amplitude/volume, timestamp/sequence, and status. In manual mode it owns sample generation and audio state; `main.py` owns all `pygame.mixer` calls on the UI thread. Playback stops when microphone mode is enabled or volume reaches zero.
- `tests/fakes.py`, `tests/test_audio_producer.py`: fake streams/devices, deterministic FFT buffers, overflow/error injection, and lifecycle tests.
- Dependency metadata only after verification and unanimous approval; the checked-in `sounddevice/` directory is not assumed importable.

## Acceptance criteria

- Dependency/importability/version/PortAudio checks pass in the documented clean environment before microphone code is enabled.
- Callback work is bounded and non-blocking; the handoff retains only the latest bounded snapshot with a documented drop policy.
- FFT bin mapping and amplitude normalization are deterministic for known sine buffers within documented tolerance.
- No device/permission failure prevents manual mode; failures are visible and do not crash the main loop.
- Manual mode produces audible sine playback at the selected frequency and volume without blocking the UI; enabling the microphone or setting volume to zero stops playback.
- `start()`/`stop()` are idempotent, close the stream, and leak no threads or unbounded audio.
- Audio retention is transient only unless later explicitly approved.
- Tests use fakes by default and require no hardware, permission, or display.
- Documentation and review artifacts are updated before completion.

## Invariants and blast radius

The UI never blocks on audio and raw audio is not retained beyond the bounded handoff. Violations affect privacy, responsiveness, and deterministic simulation.

## Verification

Run dependency checks, focused fake-audio tests, failure-injection tests, and the full suite; record results in the task review artifact.

## Concrete approved contract

This section resolves the open specification questions identified by the Task_005 three-agent review. The owner approved this contract, and its implementation and clean-environment dependency verification are complete.

### Audio snapshot and handoff

- `AudioSnapshot` is a frozen, slot-based value with exactly `frequency_hz: float`, `amplitude: float`, `volume: float`, `sequence: int`, `timestamp_monotonic: float`, and `status: Literal["ok", "manual", "silent", "stale", "overflow", "device_error"]`. It contains no sample data.
- `sequence` starts at zero and increases for every published snapshot. The producer stores exactly one latest snapshot behind a lock; there is no queue, history, cache, or retained raw audio. `latest_snapshot()` returns an immutable copy/value.
- Initial state is `manual` with the current settings frequency and volume when the microphone is disabled, and `silent` with zero amplitude when it is enabled but no valid frame has arrived.
- `ok` and `manual` replace frequency/amplitude/volume with the newest valid values. `silent`, `stale`, `overflow`, and `device_error` publish a new status while retaining the last valid frequency/amplitude/volume, so the simulation continues normally until valid data arrives.
- For a valid microphone frame, `volume` equals the same normalized frame amplitude used by the snapshot (`volume == amplitude`). Manual snapshots use the settings volume. Error statuses retain both values from the last valid snapshot.
- `stale` is emitted lazily by `latest_snapshot()`: when microphone mode is enabled and the injected clock is more than `0.25` seconds past the last snapshot timestamp, the producer publishes one `stale` snapshot (incrementing `sequence` and refreshing its timestamp) while retaining the last valid values. Repeated reads while still stale do not increment the sequence again; a later valid frame returns to `ok`. Manual mode never becomes stale because its configured sine state is continuous.
- Callback input is copied only into a single bounded pending frame. A newer frame replaces an older pending frame; callback work never waits for FFT processing. Malformed, nonfinite, empty, or out-of-range input is nonfatal and becomes the corresponding error status.

### FFT and validation

- Processing uses mono float samples at 48,000 Hz, frame/block size 512, `numpy.fft.rfft`, a rectangular window, no zero padding, and no retained frame history. Multi-channel input is averaged across channels.
- The dominant bin is the nonnegative-frequency bin with greatest magnitude; ties choose the lowest bin. Frequency is `bin * 48000 / 512`. DC and non-DC amplitude are normalized as `abs(X[0])/N` and `2*abs(X[k])/N`, respectively, then limited to `[0, 1]`.
- Silence is amplitude `< 1e-3`. Nonfinite values, overflow flags, empty frames, and device/permission/no-device failures do not raise through the UI thread. A frequency outside the visual contract `[60, 5000]` is rejected as `device_error` while retaining the last valid values.
- Required deterministic fixture: a 512-sample bin-aligned sine at bin 10 and amplitude `0.8` produces `937.5 Hz` and amplitude `0.8`, with absolute tolerance `1e-6`; tests also cover DC, ties, silence, clipping, channel averaging, and invalid data.

### Producer lifecycle and playback

- `AudioProducer(settings, *, stream_factory=None, clock=time.monotonic, sample_rate=48000, channels=1, block_size=512, fft_size=512)` exposes `start()`, `stop()`, `join(timeout=1.0)`, `latest_snapshot()`, `update_settings(settings)`, and `worker_error`.
- `start()` and `stop()` are idempotent; `stop()` closes the stream and joins processing without blocking the UI beyond the bounded join timeout. A callback arriving after stop is ignored. Worker exceptions are retained for diagnostics and do not terminate the application loop.
- The microphone is never opened on import. It is opened only when explicitly enabled. Device, permission, PortAudio, and stream failures fall back to manual mode without disabling visual simulation.
- The producer exposes a pure `PlaybackChunk` for manual sine output: 48,000 Hz, mono, signed 16-bit PCM, 512 samples per chunk, with frequency and volume from settings. The main/UI thread owns all `pygame.mixer` initialization, submission, and shutdown through a fakeable mixer adapter. Manual playback runs only when the microphone is disabled and volume is greater than zero; enabling the microphone or setting volume to zero stops it. Mixer failures are visible but do not stop particle updates.

### Dependency gate

- The already verified numerical pins remain `numpy==2.2.6` and `scipy==1.18.1`.
- The external `sounddevice` package must be pinned only after a clean-environment verification of its import, stream API, and PortAudio failure behavior. PyPI currently lists `sounddevice 0.5.6` as its latest release (published 2026-08-17), but the repository's vendored `sounddevice/` directory is not an approved runtime dependency. The engineer must record the clean-install result before adding dependency metadata. [PyPI sounddevice](https://pypi.org/project/sounddevice/)

### Required test doubles

- Tests provide a fake stream that can emit deterministic frames, overflow status, permission/device errors, callbacks after stop, and worker exceptions, plus a fake mixer that records initialization, chunk submission, stop, and close calls. The suite remains headless and hardware-independent.

## Contract clarifications after Round 2 review

The owner approved the concrete contract above. The following executable details resolve the remaining review blockers without changing the approved behavior.

### Stream and lifecycle boundary

- `StreamFactory` is `Callable[[Callable[[object, object, object, object], None], int, int, int], InputStreamLike]`; the callback receives `(indata, frames, time_info, status)`. `InputStreamLike` exposes `start()`, `stop()`, and `close()`.
- `start()` creates at most one stream and one non-daemon worker. Calling it while running is a no-op; calling it after a completed stop raises `RuntimeError`, matching Task_004. `stop()` sets the stop event, clears the pending frame, asks the stream to stop/close, and is idempotent. `join(timeout)` accepts only a finite, non-negative timeout and returns `True` if the worker is not alive after the call and `False` otherwise; it does not raise for a never-started producer. `worker_error` is `BaseException | None`. Stream and worker exceptions are retained in `worker_error` and publish `device_error` when possible.
- Stop clears the pending frame and callback-owned reference. The producer retains only the immutable latest snapshot and no frame array after processing or stop.

### Error/status mapping

`overflow` is used only for an overflow callback flag. `silent` is used only for a finite frame below the amplitude threshold. `device_error` is used for stream open/start/stop/close failures, permission/no-device/PortAudio failures, callback exceptions, malformed or nonfinite/empty frames, and frequencies outside `[60, 5000]`. `stale` is published when the last valid snapshot age exceeds `0.25` seconds. Every status publication increments `sequence`, updates the monotonic timestamp, and retains the last valid values.

### Playback handoff

- `PlaybackChunk` is frozen/slot-based with `samples: bytes`, `sample_rate: int`, `channels: int`, `sample_width: int`, `frequency_hz: float`, `volume: float`, and `sequence: int`.
- `AudioProducer.next_playback_chunk()` is a pure, nonblocking producer-side method returning one current chunk or `None`; it retains no chunk history. A UI-owned `MixerAdapter` has `initialize(sample_rate, channels, sample_width)`, `submit(chunk)`, `stop()`, and `close()`. Only the main/UI thread calls this adapter. The UI polls at most one chunk per frame, so no playback queue can grow.
- `update_settings()` atomically replaces settings. Disabling the microphone makes the next snapshot `manual` and permits chunks when volume is positive; enabling it publishes `silent` until a valid frame and makes `next_playback_chunk()` return `None`. Volume zero also returns `None`; increasing volume resumes manual chunks only when microphone mode is disabled. Mixer initialization/submission errors are reported through status/diagnostics and never stop particle updates.

### Scope boundary after Round 3 review

Task_005 verifies and exposes the pure `PlaybackChunk` producer and fakeable `MixerAdapter` boundary. Wiring the adapter into `main.py`, including actual `pygame.mixer` initialization, UI-thread polling, and audible end-to-end playback, is explicitly Task_006 scope and is a required downstream acceptance gate. Task_005 must still switch to manual mode after microphone/device startup failure so Task_006 can resume playback safely.

### Contract verification basis

The shape and lifecycle are grounded in `particle.py`, `settings.py`, `helpers.py`, and the approved Task_002/Task_004 contracts. FFT behavior is a proposed deterministic implementation contract and must be validated by the required vectors before sign-off. Dependency status was checked against the official PyPI project page on 2026-11-14.

### Update this task when

Update this task when the audio snapshot schema, FFT parameters, producer lifecycle, microphone permission behavior, playback handoff, dependency pin, or fake-device test contract changes.

## Status

Complete. Task_006 owns integrated Pygame mixer/UI wiring and end-to-end audible playback.
