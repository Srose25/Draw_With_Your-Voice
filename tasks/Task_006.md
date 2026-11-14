# Task_006 — Integrate the Pygame application UI

## Scope

Integrate settings, particles, audio, drawing, clear/toggle controls, microphone icon behavior, header/help text, and the 1–12 particle selection pause/resume behavior in `main.py`.

## Planned files and interfaces

- `main.py`: explicit `main()` entry point, clean event loop, keyboard/mouse handling, header/control rendering, and composition of settings/audio/particle services.
- `tests/test_main_controls.py` and headless UI fakes: control transitions, shortcuts, clear/draw toggles, microphone icon state, particle-count pause/resume, and clean shutdown.
- `README.md`: corrected run instructions and dependency notes only after implementation is verified.

Keyboard focus order and bindings must be deterministic: particle count, brush color, brush size, brush style, plate shape, all approved manual equation parameters, frequency slider, frequency presets, and microphone toggle are reachable by keyboard; arrows adjust numeric controls, Enter/Space activates buttons, and Escape cancels an in-progress selection without partial mutation. Mouse hitboxes and the microphone-button activation region are recorded for headless tests.

## Acceptance criteria

- Header visibly explains controls and current state without relying on color alone.
- Brush color, size, style, particle count, frequency slider 60–5000 Hz, volume control, presets 60/120/220/440/528/880 Hz, plate shape, and microphone toggle are reachable and visibly reflected.
- When the microphone is disabled, every approved square/circular equation parameter is reachable, validated, and visibly reflected; tests cover each parameter's update and invalid-input path.
- `E` toggles continuous drawing, `C` clears the canvas, and quit exits the loop and joins workers.
- Manual mode remains usable when audio is unavailable; the microphone asset is used with an accessible state label.
- Particle-count selection pauses updates until the new layout commits, then displays exactly the selected count.
- Each particle position is rendered as a hollow circle on the drawable canvas below the header; headless tests assert marker geometry, drawable-region separation, and visible position updates, and the manual checklist confirms the markers are visible.
- No Pygame calls occur from worker threads; headless tests use fakes or dummy drivers.
- Tests cover every control path and clean shutdown without real audio hardware.
- Documentation and review artifacts are updated before completion.

## Invariants and blast radius

The main loop owns UI/rendering and controls never leave simulation state partially committed. Violations affect all user-visible behavior and can leak workers.

## Concrete contract pending owner approval

This section resolves the Task_006 analysis blockers with an executable, headless-testable UI contract. The owner approved the contract and all three specialists signed off on the completed implementation.

### Application seam and thread ownership

- `main.py` defines an import-safe `Application` and `main()` entry point. Importing `main` creates no window, mixer, stream, worker, or event loop. `main()` returns an integer and never calls `sys.exit()`.
- `Application` accepts injectable `pygame_api`, `audio_factory`, `particle_factory`, `mixer_factory`, `frame_clock_factory`, `event_source`, `width=800`, and `height=600`. It exposes `handle_event(event)`, `update(dt)`, `render()`, `shutdown()`, and `run()`.
- The UI thread alone calls Pygame display/surface/font APIs, `AudioProducer.next_playback_chunk()`, and `MixerAdapter.initialize/submit/stop/close`. Particle and audio workers never call Pygame.
- Shutdown is idempotent and ordered: stop/join audio producer, stop/join particles, stop/close mixer, then call `pygame.quit()`. A mixer failure records a visible UI error and does not stop particle updates.

### Canonical geometry and hitboxes

The canonical window is 800×600. The header is `Rect(0, 0, 800, 112)`. The drawable canvas is `Rect(32, 112, 736, 472)` and particle bounds are `(38, 118, 762, 578)`. Hollow markers use radius 6, line width 2, and are rendered after the canvas strokes; all marker centers remain inside the particle bounds.

The following inclusive-left/exclusive-right rectangles are stable mouse hitboxes:

| Control | Rectangle `(left, top, width, height)` |
| --- | --- |
| `particle_count` | `(8, 8, 67, 22)` |
| `brush_color` | `(80, 8, 70, 22)` |
| `brush_size` | `(155, 8, 70, 22)` |
| `brush_style` | `(230, 8, 70, 22)` |
| `plate_shape` | `(305, 8, 70, 22)` |
| `microphone_enabled` | `(380, 8, 80, 22)` |
| `drawing_enabled` | `(465, 8, 60, 22)` |
| `clear` | `(530, 8, 60, 22)` |
| `frequency` | `(8, 36, 252, 22)` |
| `volume` | `(270, 36, 120, 22)` |
| `preset_60`, `preset_120`, `preset_220`, `preset_440`, `preset_528`, `preset_880` | six adjacent 65×22 rectangles beginning at `(400, 36)` |
| `square_n`, `square_m`, `circular_order`, `circular_root_index`, `circular_cosine_weight`, `circular_sine_weight` | six adjacent 92×40 rectangles beginning at `(8, 64)` |

The header renders text labels and current values for every control. Disabled manual equation fields are visibly marked `MIC ON` and remain keyboard-skipped until the microphone is disabled. State is never communicated by color alone; labels and a focus outline are always present.

### Focus, keyboard, and atomic settings contract

- Tab and Shift+Tab traverse this deterministic order: particle count, brush color, brush size, brush style, plate shape, square `n`, square `m`, circular order, circular root, circular cosine weight, circular sine weight, frequency, volume, six presets in ascending listed order, microphone toggle, drawing toggle, clear.
- Enter/Space activates the focused control. Escape cancels an in-progress particle-count or numeric edit without mutating committed settings. `E` toggles drawing, `C` clears, and `QUIT` requests shutdown. Arrow keys adjust focused numeric controls.
- Numeric steps are: particle count 1; brush size 1; square modes 1; circular order/root 1; circular weights 0.1; frequency 10 Hz; volume 0.05. Values remain within the Settings ranges. Clicking the frequency/volume rectangles maps horizontal position linearly to their ranges.
- Brush color cycles a fixed accessible palette `((0,0,0), (220,40,40), (30,100,220), (30,150,80), (140,60,180))`; brush style and plate shape toggle between their two approved values. Presets set frequency to 60/120/220/440/528/880 Hz.
- `apply_control_change(settings, control, value)` is the single atomic settings update path. It calls `Settings.with_updates`; validation failure leaves the prior settings unchanged and stores a visible error string. Microphone-enabled settings disable all manual equation controls; microphone-disabled settings enable them.

### Particle layout and audio transitions

- A particle-count edit begins a `LayoutState` transaction and pauses simulation. Existing particles are stopped and joined; the committed layout remains rendered while the edit is pending. Enter commits the new layout, updates `particle_count`, constructs exactly the selected number of new particles with bounds `(38, 118, 762, 578)`, and starts them. Escape cancels without settings mutation, reconstructs the previous committed layout, and resumes it. Generations increase monotonically.
- Because `AudioProducer` and `Particle` cannot restart after completed stop, a microphone transition stops/joins the old producer and replaces it with a new producer configured from the atomically updated settings. The same replacement rule is used for particle sets after layout commit/cancel.
- Each frame consumes at most one latest audio snapshot and at most one manual `PlaybackChunk`. Manual chunks are submitted only when microphone is disabled and volume is positive; microphone enable or zero volume stops playback.

### Required test seam

`tests/test_main_controls.py` uses fake Pygame, event, clock, audio, particle, and mixer objects. It must assert import side-effect isolation; every focus/binding/hitbox; every Settings field valid and invalid path; equation-field visibility; particle layout pending/commit/cancel generations and exact counts; marker geometry/header separation; drawing/clear behavior; one-chunk-per-frame UI-thread mixer ownership; mixer/device failure resilience; and ordered, idempotent shutdown with no live workers.

## Contract clarifications after Round 1 review

The owner-approved values below resolve the remaining architecture, engineering, and QA blockers. This section remains pending owner approval before implementation.

### Exact injected interfaces

- `AudioFactory = Callable[[Settings], AudioProducer]`.
- `ParticleFactory = Callable[[tuple[float, float], tuple[float, float, float, float], Settings], Particle]`.
- `MixerFactory = Callable[[object], MixerAdapter]`; the object is the injected Pygame API. The default adapter owns one Pygame mixer channel, stops/replaces the prior sound on each `submit()`, and accepts one 512-sample signed-16-bit `PlaybackChunk` at a time.
- `EventSource = Callable[[], Iterable[object]]` returning objects with `type` and, when applicable, `key`, `pos`, and `button` attributes. Fakes use the same fields and injected constants `QUIT`, `KEYDOWN`, `MOUSEBUTTONDOWN`, and `MOUSEMOTION`.
- `FrameClock` exposes `tick(fps: int) -> int`; `frame_clock_factory: Callable[[], FrameClock]` creates it. The audio and particle services retain their own monotonic clocks through their existing factories.
- `PygameApi` is the injected module/facade exposing `init`, `quit`, `display.set_mode`, `display.set_caption`, `display.flip`, `Surface`, `Rect`, `draw`, `font`, `image.load`, `event`, `time`, `mixer`, and the event/key constants used by the contract. `main()` has signature `main(*, pygame_api=None, audio_factory=AudioProducer, particle_factory=Particle, mixer_factory=None, frame_clock_factory=None, event_source=None, width=800, height=600) -> int`.
- `Application` has constructor parameters matching those factories plus `settings: Settings | None = None`; its public methods are `handle_event(event: object) -> None`, `update(dt: float) -> None`, `render() -> None`, `shutdown() -> None`, and `run() -> int`. Importing `main` performs none of these side effects.

### Consent, state, and settings transactions

- The persisted `Settings` default remains unchanged for compatibility, but `Application` starts with microphone consent off: its effective initial settings use `microphone_enabled=False` and the first explicit microphone activation is the only action allowed to open a device. Importing or constructing the module never opens a microphone.
- `UIState` is a frozen/slot-based value with these exact fields: `settings: Settings`, `pending_settings: Settings | None`, `layout: LayoutState`, `pending_layout: LayoutState | None`, `focus_control: str`, `drawing_enabled: bool`, `shutdown_requested: bool`, `error_message: str | None`, `audio_status: Literal["ok", "manual", "silent", "stale", "overflow", "device_error"] | None`, `audio_diagnostic: Literal["none", "unavailable", "error"]`, and `mixer_available: bool`. `Application.ui_state -> UIState` returns the current immutable state. Committed settings change only on an accepted control activation/Enter; pending values are rendered with a `PENDING` label and discarded by Escape.
- `apply_control_change(settings: Settings, control: str, value: object) -> Settings` is defined in `main.py`. Its allowed control names are exactly the Settings field names plus `frequency_preset`; `drawing_enabled` and `clear` are separate UI-state/action transitions. It returns a new validated Settings value or raises `SettingsValidationError` without mutating the input. The Application catches the error, preserves committed and pending values, and exposes the message in `UIState.error_message`.
- Numeric arrow and slider edits stage a new Settings value; Enter commits it. Toggles, brush palette/style, plate shape, presets, drawing, and clear activate immediately. Disabled manual equation controls are skipped by focus and reject direct events with an accessible error.
- Right/Up increment and Left/Down decrement; range endpoints clamp to the valid minimum/maximum and never wrap. Tab and Shift+Tab wrap focus. Escape cancels the staged numeric or particle-count edit. For the frequency and volume sliders, the rightmost pixel is included and mapping is `t=clamp((x-left)/(width-1),0,1)`, `frequency=60 + round(t*4940)`, and `volume=round(clamp(t,0,1)*20)/20`; therefore the leftmost and rightmost pixels select exact endpoints. Clicks outside a hitbox are ignored.

### Failure, drawing, and layout rules

- Audio/particle factory, start, stop, join, mixer initialize, and mixer submit exceptions are caught, recorded in `error_message`, and followed by best-effort cleanup of every remaining resource in shutdown order. Rendering continues while the application is alive. `pygame.quit()` is attempted last; `run()` returns 0 even after a recoverable service failure. A `join()` returning `False` is recorded as an error and does not prevent subsequent cleanup.
- `replace_audio(settings)` stops and joins the prior producer before constructing the replacement. Enabling the microphone constructs and starts exactly one replacement producer; disabling it constructs exactly one manual producer without opening a device. If microphone startup fails, the committed Settings is synchronized to `microphone_enabled=False`, `audio_status` retains the producer status, `audio_diagnostic` becomes `unavailable` or `error`, and manual playback remains eligible. No producer instance is restarted after completed stop and no duplicate stream is allowed.
- Particle-count cancel restores the prior committed points, count, generation, particle Settings, audio state, and drawing state by reconstructing a fresh worker set at the prior anchors/settings; it does not promise to restore stopped workers' transient position/velocity snapshots because the approved `Particle` interface has no state-restore API. Commit publishes only the new generation and selected count.
- `drawing_enabled` defaults to `False`. E is ignored while a numeric edit is pending. Each frame records one prior position per particle; when enabled, it draws the full segment from prior to current position with the committed brush settings, then renders hollow markers. Clear removes stroke history and resets prior positions to current snapshots. Missing/error snapshots produce no stroke but do not remove the marker.
- The per-frame order is: poll events; apply committed control transitions; call `latest_snapshot()` once and publish that snapshot to every particle; poll at most one manual chunk and submit it; draw strokes; draw hollow markers; render header/focus/error text; flip; tick the frame clock.

### Dependency and accessibility gate

`requirements.txt` pins verified `pygame==2.6.1`. The injected Pygame facade owns orchestration, events, display, fonts, images, timing, and mixer calls; the existing `helpers.py` drawing primitives continue to draw on compatible `pygame.Surface` objects. Headless tests set SDL’s dummy video driver and use real Pygame surfaces, with fake event/audio/mixer services, so no display or hardware is required. Every control has a visible text label, textual current value, keyboard focus outline, and non-color state text. Microphone labels distinguish `MIC OFF`, `MIC ON`, `MIC UNAVAILABLE`, and `MIC ERROR`; disabled equation controls are labeled `DISABLED WHILE MIC ON`.

### Verification basis and freshness

The proposed seam is grounded in the current `main.py`, `settings.py`, `helpers.py`, `particle.py`, `audio_producer.py`, and completed Task_003–005 contracts. The geometry preserves the existing golden layout’s 112-pixel header and approved drawable/particle bounds. Update this task when a UI control, geometry rectangle, keyboard binding, settings mapping, worker lifecycle, mixer handoff, or headless test criterion changes.

## Verification

Run headless control tests, a manual smoke checklist, and the full suite; record results in the task review artifact.

## Status

Complete. Task_003, Task_004, and Task_005 are complete; Task_006 implementation and verification passed. See `docs/reviews/Review-Task-006.md`.
