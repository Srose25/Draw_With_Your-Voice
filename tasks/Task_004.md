# Task_004 — Implement threaded particle simulation

## Scope

Implement `particle.py` with safe state handoff, square/circular equation evaluation, particle positions, rendering state, and lifecycle behavior based on approved contracts.

## Proposed concrete implementation contract

- `ParticleSnapshot` is an immutable dataclass with exact fields: `position: tuple[float,float]`, `velocity: tuple[float,float]`, `anchor: tuple[float,float]`, `color: tuple[int,int,int]`, `brush_size: int`, `brush_style: Literal["round","square"]`, `last_valid_position: tuple[float,float]`, and `error: str|None`. `snapshot()` returns a fresh immutable value; a later valid step clears `error`.
- `AudioSnapshot` remains a runtime dataclass owned by `audio_producer.py`; `particle.py` uses only the structural `AudioSnapshotLike` protocol and does not duplicate that runtime class. Accepted `ok`/`manual` snapshots must have strictly increasing sequence numbers; lower or repeated sequences, malformed data, stale timestamps, and `silent`/`overflow`/`device_error` statuses are ignored while the last valid audio inputs remain active. A later valid higher-sequence snapshot recovers the inputs.
- `Particle(anchor: tuple[float,float], bounds: tuple[float,float,float,float], settings: Settings, *, clock: Callable[[],float]=time.monotonic)` owns one particle’s state. Bounds are `(left,top,right,bottom)` after marker-radius inset; initial position is `anchor`, initial velocity is `(0.0,0.0)`, and anchor must be finite and inside bounds. It exposes `start() -> None`, `stop() -> None`, `join(timeout: float=1.0) -> bool`, `update_from_audio(snapshot: AudioSnapshotLike) -> None`, `update_settings(settings: Settings) -> None`, `step(dt: float) -> ParticleSnapshot`, and `snapshot() -> ParticleSnapshot`. `AudioSnapshotLike` is the structural protocol owned by `particle.py`; Task_005 owns the runtime `AudioSnapshot` implementation.
- `step(dt)` is deterministic and is the only motion method used by worker execution and tests. It clamps `dt` to `[0,0.1]`, maps pixels to centered equation coordinates with screen-Y inversion, selects equations only from `Settings.plate_shape`, applies the Task_002 persistent-velocity blend/reflection contract, and never calls Pygame.
- `square_value` and `circular_value` are pure Pygame-free functions owned by `particle.py`; `AudioSnapshot` is defined once in `audio_producer.py` and consumed by `Particle` without schema duplication.
- Microphone-enabled mode consumes the latest valid audio inputs; microphone-disabled mode uses `Settings.frequency_hz` and `Settings.volume`; manual equation fields always come from `Settings`; silent/stale/overflow/device-error snapshots retain last-valid simulation inputs.
- The approved motion formula is volume-only: `volume` is the motion gain, while `amplitude` is retained as AudioSnapshot metadata and does not scale particle velocity. This separation is tested explicitly.
- The worker uses a lock-protected state, one idempotent non-daemon worker, an injected clock/tick source, an event for stop, and the property `worker_error: BaseException|None`. The first worker exception is retained until object disposal; `join(timeout)` returns `True` when stopped and `False` on timeout, never raises the worker exception, and validates non-negative finite timeouts. `join()` before `start()` returns `True`; `start()` after stop raises `RuntimeError`; repeated start while running is idempotent. Shutdown must join before application exit. Workers never import or call Pygame APIs.

### Circular pixel mapping proposal

For circular mode, use explicit pixel normalization: `x_screen=2*(x-center_x)/(right-left)`, `y_screen=2*(y-center_y)/(bottom-top)`, `x_equation=x_screen`, `y_equation=-y_screen`, `r=hypot(x_equation,y_equation)/sqrt(2)`, and `theta=atan2(y_equation,x_equation)` canonicalized from `+π` to `-π`. This maps rectangular drawable corners to `r=1`, keeps every drawable point in-domain, preserves screen-Y inversion, and avoids silent clamping. At the right-center point, `theta=0`; at the left-center point, `theta=-π`; at the top/bottom centers, `theta=+π/2/-π/2` respectively.

**Owner approval:** Approved by the user.

## Required tests

`tests/test_particle.py` must cover both evaluators and invalid inputs, screen-to-equation vectors, frequency endpoints, volume endpoints, dt clamping, one-axis/corner/multi-period reflection, reflected-velocity persistence, non-finite last-valid retention, manual/audio precedence, stale/error behavior, concurrent snapshot/update coherence, settings replacement, idempotent lifecycle/bounded join, worker exception propagation, and proof that workers perform no Pygame calls. Tests use fake clocks/audio and no wall-clock sleeps.

Required circular mapping vectors include right-center `(x=right,y=center)` mapping to `(r=1/sqrt(2),theta=0)`, left-center `(x=left,y=center)` mapping to `(r=1/sqrt(2),theta=-π)`, and top/bottom centers mapping to `theta=+π/2/-π/2`; positive sine weight must produce opposite signs at the top/bottom centers for order 1 while remaining zero at the horizontal centers. `worker_error` tests assert first-error retention, non-raising `join`, timeout `False`, and `RuntimeError` on start-after-stop.

## Planned files and interfaces

- `particle.py`: a `Particle` object with position snapshot, color/brush state, plate/equation configuration, `start()`, `stop()`, `update_from_audio(snapshot)`, `snapshot()`, and `join()` lifecycle methods. Worker threads must not render or mutate Pygame surfaces.
- `tests/test_particle.py`: deterministic motion, equation dispatch, snapshot consistency, invalid input, worker start/stop, and no-render-from-worker tests.

## Acceptance criteria

- Particle positions remain finite and within drawable bounds after updates.
- Square and circular evaluators are selected explicitly and use Task_002 contracts.
- Audio/manual frequency updates are safe under concurrent reads; consumers see coherent snapshots.
- Manual settings/equation updates have an explicit safe path in addition to `update_from_audio(snapshot)`.
- Worker lifecycle is idempotent, bounded, cleanly stoppable, and surfaces exceptions to the owner.
- Rendering is performed only by the Pygame/UI thread.
- Tests cover deterministic updates without uncontrolled threads plus one fake-clock/audio lifecycle integration test.
- Documentation and review artifacts are updated before completion.

## Invariants and blast radius

The UI owns rendering and worker shutdown is guaranteed. Violations can freeze the UI, leak threads, or corrupt visible state.

## Verification

Run focused particle tests, lifecycle checks, and the full suite; record results in the task review artifact.

## Status

Complete — implementation and full verification passed. See `docs/reviews/Review-Task-004.md`.
