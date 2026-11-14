# Engineer Record — Interfaces, Dependencies, and Current Code

## Current implementation inventory

`main.py` is the current application entry point. It exposes import-safe `Application`, `UIState`, `apply_control_change()`, `PygameMixerAdapter`, and `main()` interfaces. It composes settings, particles, audio, drawing, layout transactions, the microphone icon, accessible header, mixer, and shutdown behavior at 800×600/60 FPS. Task_007 final hardening is complete; manual hardware smoke remains non-gating and unknown in this environment.

`settings.py` implements the immutable `Settings` dataclass, `SettingsValidationError`, `with_updates()`, and `to_dict()` with the Task_002 field/default/validation contract. `helpers.py` implements `LayoutState`, `particle_layout()`, `begin_layout()`, `commit_layout()`, `cancel_layout()`, `draw_stroke()`, `draw_particle_marker()`, `clear_canvas()`, and `generate_sine_samples()`. Helpers do not own display, event, mixer, or audio lifecycle state.

`particle.py` implements `ParticleSnapshot`, `AudioSnapshotLike`, `square_value()`, `circular_value()`, `Particle.step()`, `snapshot()`, `update_from_audio()`, `update_settings()`, `start()`, `stop()`, and bounded `join()`. It owns no Pygame calls; the structural audio protocol will be satisfied by the runtime `AudioSnapshot` defined in Task 005.

`README.md` now documents the verified `main.py` entry point and `requirements.txt` installation. Importing `main` is side-effect free; full application composition, mixer wiring, and clean shutdown are implemented and covered by the Task_006 headless suite.

## Contract inventory

There are currently no application routes, endpoints, environment variables, or feature flags. Implemented public Python interfaces include settings/helpers, particle/evaluator/lifecycle, `AudioSnapshot`, `PlaybackChunk`, `AudioProducer`, `InputStreamLike`, `MixerAdapter`, `UIState`, `Application`, `apply_control_change()`, and `PygameMixerAdapter`.

## Dependency and integration facts

The README and `requirements.txt` document Python 3.12 and pin `pygame==2.6.1`, `numpy==2.2.6`, `scipy==1.18.1`, and external `sounddevice==0.5.6`. The external package imports from site-packages and exposes `InputStream`; host PortAudio input-start failure is handled by manual fallback. The checked-in `sounddevice/` directory is not installed or imported as the runtime package.

Candidate upstream APIs demonstrated in that directory include `sounddevice.InputStream`, `RawInputStream`, callback arguments `(indata, frames, time, status)`, `query_devices()`, `query_hostapis()`, `check_input_settings()`, and NumPy-based processing in `plot_input.py`. These are examples, not project contracts.

## Invariants and blast radius

- Any future public interface must be documented with exact inputs, outputs, errors, and callers before implementation. Otherwise agents may silently break an undocumented contract.
- Audio callbacks must hand off copied/bounded data to processing code and must not block. Violations can cause dropouts, queue growth, or a frozen Pygame loop.
- Dependency versions and import paths must remain pinned and verified before integration changes. Assuming the vendored directory is importable can produce a startup failure.
- README launch instructions must remain synchronized with `main.py` and `requirements.txt`; drift affects onboarding and launch commands.

## Verification basis

Verified against `main.py`, all implementation modules, `requirements.txt`, all test files, `README.md`, `docs/project_plan.md`, `rg --files`, and the complete `sounddevice/` inventory. The focused UI suite passed 60 cases, the dedicated Task_007 gate passed 4 cases, and the full suite passed 186 tests. Pygame dummy-driver rendering, clean external sounddevice import, and PortAudio failure fallback were checked separately.

## Update this doc when

Update this file whenever a module, function/class signature, dependency, event contract, route, environment variable, audio queue, or runtime entry point is added, removed, or changed.

