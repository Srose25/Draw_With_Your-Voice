# Architect Record — Current System and Boundaries

## Status and scope

This is a grounded snapshot after `Task_007`. The repository contains implemented settings, helpers, particle, audio, and Pygame UI composition modules, focused tests, the microphone asset, pinned dependency metadata, planning documentation, and final-gate verification artifacts. Task_007 is complete; manual hardware smoke remains explicitly non-gating and unknown in this environment.

## Verified current architecture

- `main.py` initializes Pygame, creates an 800×600 window, creates a white canvas, handles window close and the `C` key, blits the canvas, and runs a 60 FPS loop.
- `main.py` provides import-safe `Application`/`main()` composition, consent-off startup, injected service boundaries, deterministic controls, pending layout transactions, UI-thread mixer ownership, accessible status rendering, and ordered shutdown.
- `settings.py` implements immutable validated settings, and `helpers.py` implements deterministic layouts, layout transactions, surface-only drawing helpers, hollow markers, clearing, and pure sine samples.
- `particle.py` implements pure square/circular evaluators, centered/circular mapping, persistent reflected motion, immutable snapshots, manual/audio precedence, and a bounded non-daemon worker. `audio_producer.py` implements immutable latest-only FFT snapshots, lazy stale status, bounded callback handoff, failure-to-manual fallback, and pure manual `PlaybackChunk` generation.
- `tests/test_settings.py`, `tests/test_helpers.py`, `tests/test_particle.py`, and `tests/test_audio_producer.py` provide the current focused verification suite.
- `tests/test_particle.py` covers the particle equations, motion, concurrency, lifecycle, error handling, and Pygame isolation.
- There are no implemented routes, network services, persistent stores, authentication boundaries, route schemas, or application event contracts; implemented module-level Python interfaces are documented in `docs/engineer.md`.
- `assets/microphone_icon.png` is loaded and rendered by the UI.
- `docs/project_plan.md` describes the intended particle, settings, audio, and Chladni-equation design. That document is forward-looking, not evidence of implementation.

## Trust boundaries and security notes

Microphone capture crosses from local audio hardware/PortAudio into an asynchronous Python callback and then into application state. The callback does not block on GUI work, disk I/O, or unbounded processing. Task_005 and Task_006 implement opt-in capture, bounded copied input, no raw retention, visible failure fallback, and UI-thread-only mixer ownership.

The checked-in `sounddevice` directory is not the runtime dependency: external `sounddevice==0.5.6` is pinned in `requirements.txt` and verified from site-packages with `InputStream` and device enumeration. Host PortAudio input-start failure is visible and falls back to manual mode.

## Invariants and blast radius

- Current documentation must distinguish verified code from intended design. Violating this can cause agents to implement against nonexistent contracts.
- The UI loop must remain responsive when audio is eventually added. Blocking it would affect drawing, controls, and shutdown behavior.
- Audio input must remain opt-in and failure-tolerant once implemented. Changing that assumption would affect privacy, startup, and device-error handling.
- No route, network schema, or application event contract exists today; the implemented Python interfaces are documented in `docs/engineer.md`. Introducing a route, schema, event, or changing an existing public Python signature requires a new full review cycle.

## Verification basis

Verified against `main.py`, all implementation modules, `requirements.txt`, all test files, `README.md`, `docs/project_plan.md`, the microphone asset, the repository file inventory, and all files under `sounddevice/` as of Task_007. The focused UI suite passed 60 cases, the dedicated Task_007 gate passed 4 cases, and the full suite passed 186 tests with the SDL dummy driver. Task_007 is complete; manual hardware smoke remains non-gating and unknown.

## Update this doc when

Update this file when the application entry point, audio/device boundary, threading model, persistence/network boundary, security assumptions, or intended architecture changes.

