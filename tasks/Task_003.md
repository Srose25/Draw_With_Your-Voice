# Task_003 — Implement settings, layouts, and helpers

## Scope

Implement `settings.py` and `helpers.py`, including validated settings state, 1–12 particle layout generation, drawing/clear helpers, and deterministic sine-wave support as approved by Task_002.

## Planned files and interfaces

- `settings.py`: an immutable `@dataclass(frozen=True, slots=True) Settings` with the exact Task_002 fields/defaults: brush_size=5, brush_color=(0,0,0), brush_style="round", particle_count=1, microphone_enabled=True, frequency_hz=440.0, volume=0.5, plate_shape="square", square_n=1, square_m=2, circular_order=0, circular_root_index=1, circular_cosine_weight=1.0, circular_sine_weight=0.0. It exposes `with_updates(**changes) -> Settings` and `to_dict() -> dict[str, object]`. Invalid candidates raise `SettingsValidationError` with stable categories `type|range|enum|finite|dependency` and cannot partially mutate.
- `helpers.py`: the exact pure interfaces `particle_layout(count:int,width:int,height:int,marker_radius:int=6) -> tuple[tuple[int,int], ...]`, `begin_layout(count,width,height,current_generation:int=0) -> LayoutState`, `commit_layout(pending:LayoutState) -> LayoutState`, `cancel_layout(pending:LayoutState,previous:LayoutState) -> LayoutState`, `draw_stroke(surface,points,color,size,style) -> None`, `draw_particle_marker(surface,position,color,radius) -> None`, `clear_canvas(surface,background=(255,255,255)) -> None`, and `generate_sine_samples(frequency_hz,sample_rate,length,amplitude=1.0,phase=0.0) -> tuple[float,...]`.
- `LayoutState` is immutable with `status: Literal["pending","committed"]`, ordered `points`, `generation:int`, and `simulation_paused:bool`. `begin_layout` returns `pending`/`paused=True` with `generation=current_generation+1`; `commit_layout` returns `committed`/`paused=False` preserving that generation; `cancel_layout` returns the previous committed state unchanged. The UI/simulation observes this state to pause updates and atomically replace visible points.
- `draw_stroke` is UI-thread-only and operates only on a caller-provided surface: round style uses round caps, square style uses square caps/stamps, and it performs no display/event/mixer calls. `draw_particle_marker` renders a hollow circle with a 2-pixel outline. `clear_canvas` fills the configured background.
- `generate_sine_samples` is pure and non-blocking: sample `i` is `amplitude*sin(2π*frequency_hz*i/sample_rate+phase)`, exactly `length` samples with no duplicated endpoint. It validates finite values, positive sample rate, non-negative length, and amplitude `[0,1]`; playback/state remain in Task_005.
- `tests/test_settings.py`, `tests/test_helpers.py`: unit tests for validation, all counts 1–12, geometry invariants, draw/clear behavior, and sine samples.

## Acceptance criteria

- Every settings field has a default, range/type validation, and test coverage.
- Every count 1–12 exactly matches Task_002’s independent 800×600 arrays; alternate dimensions preserve cardinality, bounds, and arrangement invariants, and invalid/too-small dimensions raise `ValueError` without unbounded allocation.
- Layout selection exposes observable pending/committed state with generation and pause fields; pending changes pause simulation, commit returns a committed state atomically, and cancellation preserves the prior committed state.
- Settings failures cover wrong types (including booleans passed as integers), NaN/inf, invalid ranges/enums, serialization names, and no partial mutation.
- Drawing tests use headless `pygame.Surface` objects with no display, microphone, network, mixer, or event-loop dependency; tests assert white background clearing, round/square stroke pixels, hollow-marker geometry, and canvas-edge clipping.
- Sine tests cover known values, zero frequency, phase, amplitude, exact length/no duplicate endpoint, invalid sample rate/length/finite values, and deterministic repeatability.
- Supported brush styles and every approved equation-parameter field are enumerated by Task_002 before implementation; unknown choices remain explicitly marked until approved.
- Tests run without microphone, display, or network access.
- Documentation and review artifacts are updated before completion.

## Invariants and blast radius

Settings updates are atomic and layout output is deterministic. Violations affect every particle, UI control, and test fixture.

## Verification

Run focused tests plus the full suite; record results and protected-path checks in the task review artifact.

## Status

Complete — implementation and focused verification passed. See `docs/reviews/Review-Task-003.md`.
