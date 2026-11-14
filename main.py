"""Import-safe Pygame application composition for Draw With Your Voice."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from audio_producer import AudioProducer, MixerAdapter, PlaybackChunk
from helpers import LayoutState, begin_layout, clear_canvas, commit_layout, draw_particle_marker, draw_stroke
from particle import Particle, ParticleSnapshot
from settings import Settings, SettingsValidationError

AudioStatus = Literal["ok", "manual", "silent", "stale", "overflow", "device_error"]
AudioDiagnostic = Literal["none", "unavailable", "error"]

@dataclass(frozen=True, slots=True)
class UIState:
    settings: Settings
    pending_settings: Settings | None
    layout: LayoutState
    pending_layout: LayoutState | None
    focus_control: str
    drawing_enabled: bool
    shutdown_requested: bool
    error_message: str | None
    audio_status: AudioStatus | None
    audio_diagnostic: AudioDiagnostic
    mixer_available: bool

CONTROL_ORDER = ("particle_count", "brush_color", "brush_size", "brush_style", "plate_shape", "square_n", "square_m", "circular_order", "circular_root_index", "circular_cosine_weight", "circular_sine_weight", "frequency", "volume", "preset_60", "preset_120", "preset_220", "preset_440", "preset_528", "preset_880", "microphone_enabled", "drawing_enabled", "clear")
PRESETS = {f"preset_{v}": float(v) for v in (60, 120, 220, 440, 528, 880)}
PALETTE = ((0, 0, 0), (220, 40, 40), (30, 100, 220), (30, 150, 80), (140, 60, 180))
EQUATION_CONTROLS = {"square_n", "square_m", "circular_order", "circular_root_index", "circular_cosine_weight", "circular_sine_weight"}
HITBOXES = {"particle_count": (8, 8, 67, 22), "brush_color": (80, 8, 70, 22), "brush_size": (155, 8, 70, 22), "brush_style": (230, 8, 70, 22), "plate_shape": (305, 8, 70, 22), "microphone_enabled": (380, 8, 80, 22), "drawing_enabled": (465, 8, 60, 22), "clear": (530, 8, 60, 22), "frequency": (8, 36, 252, 22), "volume": (270, 36, 120, 22)}
for i, name in enumerate(PRESETS): HITBOXES[name] = (400 + i * 65, 36, 65, 22)
for i, name in enumerate(("square_n", "square_m", "circular_order", "circular_root_index", "circular_cosine_weight", "circular_sine_weight")): HITBOXES[name] = (8 + i * 92, 64, 92, 40)

def apply_control_change(settings: Settings, control: str, value: object) -> Settings:
    if control == "frequency_preset":
        if value not in (60, 120, 220, 440, 528, 880): raise SettingsValidationError("range", "unknown frequency preset")
        return settings.with_updates(frequency_hz=float(value))
    if control not in Settings.__dataclass_fields__: raise SettingsValidationError("type", f"unsupported settings control: {control}")
    return settings.with_updates(**{control: value})

class PygameMixerAdapter:
    def __init__(self, pygame_api) -> None: self._pygame, self._channel, self._initialized = pygame_api, None, False
    def initialize(self, sample_rate: int, channels: int, sample_width: int) -> None:
        if not self._initialized:
            self._pygame.mixer.init(frequency=sample_rate, channels=channels, size=-8 * sample_width)
            self._channel, self._initialized = self._pygame.mixer.Channel(0), True
    def submit(self, chunk: PlaybackChunk) -> None:
        if not self._initialized: self.initialize(chunk.sample_rate, chunk.channels, chunk.sample_width)
        self._channel.stop(); self._channel.play(self._pygame.mixer.Sound(buffer=chunk.samples))
    def stop(self) -> None:
        if self._channel is not None: self._channel.stop()
    def close(self) -> None:
        self.stop()
        if self._initialized: self._pygame.mixer.quit()
        self._initialized, self._channel = False, None

class Application:
    def __init__(self, *, pygame_api=None, audio_factory=AudioProducer, particle_factory=Particle, mixer_factory=None, frame_clock_factory=None, event_source=None, settings: Settings | None = None, width: int = 800, height: int = 600) -> None:
        if pygame_api is None:
            import pygame as pygame_api
        self.pygame, self.width, self.height = pygame_api, width, height
        self._audio_factory, self._particle_factory = audio_factory, particle_factory
        self._mixer_factory, self._event_source = mixer_factory or PygameMixerAdapter, event_source or self.pygame.event.get
        self._clock = (frame_clock_factory or self.pygame.time.Clock)()
        base = settings or Settings(); self._settings = base.with_updates(microphone_enabled=False)
        self._canvas, self._screen, self._font, self._mic_icon = self.pygame.Surface((width, height)), None, None, None
        clear_canvas(self._canvas)
        self._audio = self._mixer = None; self._particles: list[Particle] = []; self._snapshots: list[ParticleSnapshot] = []
        self._layout = commit_layout(begin_layout(self._settings.particle_count, width, height)); self._pending_layout = None; self._pending_settings = None
        self._focus_index = 0; self._drawing = False; self._shutdown_requested = False; self._error_message = None
        self._audio_status: AudioStatus | None = "manual"; self._audio_diagnostic: AudioDiagnostic = "none"; self._mixer_available = True; self._previous_positions = []
        self._replace_audio(self._settings); self._replace_particles(self._layout, self._settings)

    @property
    def ui_state(self) -> UIState:
        return UIState(self._settings, self._pending_settings, self._layout, self._pending_layout, self._focused(), self._drawing, self._shutdown_requested, self._error_message, self._audio_status, self._audio_diagnostic, self._mixer_available)
    @property
    def particles(self): return tuple(self._particles)
    def _record_error(self, value) -> None: self._error_message = str(value)

    def _replace_audio(self, settings: Settings) -> None:
        if self._audio is not None:
            try: self._audio.stop()
            except BaseException as exc: self._record_error(exc)
            try:
                if not self._audio.join(1.0): self._record_error("audio worker did not stop")
            except BaseException as exc: self._record_error(exc)
        try:
            self._audio = self._audio_factory(settings); self._audio.start(); self._audio_status = self._audio.latest_snapshot().status if settings.microphone_enabled else "manual"
            self._audio_diagnostic = "none"
        except BaseException as exc:
            self._record_error(exc); self._audio_diagnostic = "unavailable"; self._settings = self._settings.with_updates(microphone_enabled=False)
            failed = self._audio
            if failed is not None:
                try: failed.stop()
                except BaseException as cleanup: self._record_error(cleanup)
                try: failed.join(1.0)
                except BaseException as cleanup: self._record_error(cleanup)
            try: self._audio = self._audio_factory(self._settings); self._audio.start()
            except BaseException as fallback: self._record_error(fallback)
            for particle in self._particles:
                try: particle.update_settings(self._settings)
                except BaseException as particle_error: self._record_error(particle_error)
            self._audio_status = "device_error"

    def _replace_particles(self, layout: LayoutState, settings: Settings) -> None:
        for particle in self._particles:
            try: particle.stop()
            except BaseException as exc: self._record_error(exc)
        for particle in self._particles:
            try:
                if not particle.join(1.0): self._record_error("particle worker did not stop")
            except BaseException as exc: self._record_error(exc)
        self._particles = []
        for x, y in layout.points:
            try:
                self._particles.append(self._particle_factory((float(x), float(y)), (38.0, 118.0, 762.0, 578.0), settings))
            except BaseException as exc:
                self._record_error(exc)
        for particle in self._particles:
            try: particle.start()
            except BaseException as exc: self._record_error(exc)

    def _commit_settings(self, settings: Settings) -> None:
        changed = settings.microphone_enabled != self._settings.microphone_enabled; self._settings = settings
        for particle in self._particles: particle.update_settings(settings)
        if changed: self._replace_audio(settings)
        for particle in self._particles: particle.update_settings(self._settings)
        if (self._settings.microphone_enabled or self._settings.volume <= 0.0) and self._mixer is not None:
            try: self._mixer.stop()
            except BaseException as exc: self._record_error(exc)
        if self._settings.microphone_enabled and CONTROL_ORDER[self._focus_index] in EQUATION_CONTROLS:
            self._focus_index = CONTROL_ORDER.index("frequency")

    def _stage(self, control: str, value: object) -> None:
        if self._settings.microphone_enabled and control in EQUATION_CONTROLS:
            self._record_error("DISABLED WHILE MIC ON"); return
        settings_control = "frequency_hz" if control == "frequency" else control
        if control in PRESETS: settings_control, value = "frequency_preset", int(PRESETS[control])
        try: pending = apply_control_change(self._pending_settings or self._settings, settings_control, value)
        except SettingsValidationError as exc: self._record_error(exc); return
        self._pending_settings = pending
        if control == "particle_count":
            if self._pending_layout is None:
                self._pending_layout = begin_layout(pending.particle_count, self.width, self.height, self._layout.generation)
                for particle in self._particles: particle.stop()
                for particle in self._particles:
                    if not particle.join(1.0): self._record_error("particle worker did not stop")
            else:
                self._pending_layout = begin_layout(pending.particle_count, self.width, self.height, self._layout.generation)

    def _commit_pending(self) -> None:
        if self._pending_settings is None: return
        settings, layout = self._pending_settings, self._pending_layout; self._pending_settings = self._pending_layout = None
        if layout is not None:
            self._commit_settings(settings); self._layout = commit_layout(layout); self._replace_particles(self._layout, self._settings)
        else: self._commit_settings(settings)
    def _cancel_pending(self) -> None:
        if self._pending_settings is not None: self._pending_settings = self._pending_layout = None; self._replace_particles(self._layout, self._settings)
    def _focusable_order(self):
        return tuple(c for c in CONTROL_ORDER if c not in EQUATION_CONTROLS) if self._settings.microphone_enabled else CONTROL_ORDER
    def _focused(self) -> str:
        order = self._focusable_order()
        if CONTROL_ORDER[self._focus_index] not in order: self._focus_index = CONTROL_ORDER.index(order[0])
        return order[order.index(CONTROL_ORDER[self._focus_index])]
    def _adjust(self, direction: int) -> None:
        control, current = self._focused(), self._pending_settings or self._settings; values = current.to_dict(); field = "frequency_hz" if control == "frequency" else control
        steps = {"particle_count": 1, "brush_size": 1, "square_n": 1, "square_m": 1, "circular_order": 1, "circular_root_index": 1, "circular_cosine_weight": .1, "circular_sine_weight": .1, "frequency_hz": 10.0, "volume": .05}
        bounds = {"particle_count": (1, 12), "brush_size": (1, 50), "square_n": (1, 8), "square_m": (1, 8), "circular_order": (0, 8), "circular_root_index": (1, 8), "circular_cosine_weight": (-1., 1.), "circular_sine_weight": (-1., 1.), "frequency_hz": (60., 5000.), "volume": (0., 1.)}
        if field not in steps: return
        low, high = bounds[field]; value = max(low, min(high, values[field] + direction * steps[field])); self._stage(control, type(values[field])(value))

    def _activate(self, control: str) -> None:
        if control == "clear": clear_canvas(self._canvas); self._previous_positions = []; return
        if control == "drawing_enabled": self._drawing = not self._drawing; return
        if control == "microphone_enabled": self._commit_settings(self._settings.with_updates(microphone_enabled=not self._settings.microphone_enabled)); return
        if control in PRESETS: self._stage(control, PRESETS[control]); self._commit_pending(); return
        if control in ("brush_color", "brush_style", "plate_shape"):
            if control == "brush_color": value = PALETTE[(PALETTE.index(self._settings.brush_color) + 1) % len(PALETTE)] if self._settings.brush_color in PALETTE else PALETTE[0]
            elif control == "brush_style": value = "square" if self._settings.brush_style == "round" else "round"
            else: value = "circular" if self._settings.plate_shape == "square" else "square"
            self._stage(control, value); self._commit_pending(); return
        if control in ("particle_count", "brush_size", "square_n", "square_m", "circular_order", "circular_root_index", "circular_cosine_weight", "circular_sine_weight", "frequency", "volume"): self._commit_pending()

    def _key(self, event, name: str) -> bool: return getattr(self.pygame, name, object()) == getattr(event, "key", None)
    def handle_event(self, event) -> None:
        if event.type == getattr(self.pygame, "QUIT", "QUIT"): self._shutdown_requested = True; return
        if event.type == getattr(self.pygame, "KEYDOWN", "KEYDOWN"):
            if self._key(event, "K_TAB"):
                order = self._focusable_order(); current = order.index(self._focused()); delta = -1 if getattr(event, "mod", 0) & getattr(self.pygame, "KMOD_SHIFT", 0) else 1
                self._focus_index = CONTROL_ORDER.index(order[(current + delta) % len(order)]); return
            if self._key(event, "K_ESCAPE"): self._cancel_pending(); return
            if self._key(event, "K_RETURN") or self._key(event, "K_SPACE"): self._activate(self._focused()); return
            if self._key(event, "K_e"):
                if self._pending_settings is None: self._drawing = not self._drawing
                return
            if self._key(event, "K_c"): self._activate("clear"); return
            if self._key(event, "K_RIGHT") or self._key(event, "K_UP"): self._adjust(1); return
            if self._key(event, "K_LEFT") or self._key(event, "K_DOWN"): self._adjust(-1); return
        if event.type == getattr(self.pygame, "MOUSEBUTTONDOWN", "MOUSEBUTTONDOWN") and getattr(event, "button", 1) == 1:
            x, y = event.pos
            for control, (left, top, width, height) in HITBOXES.items():
                if left <= x < left + width and top <= y < top + height:
                    self._focus_index = CONTROL_ORDER.index(control)
                    if self._settings.microphone_enabled and control in EQUATION_CONTROLS:
                        self._record_error("DISABLED WHILE MIC ON"); return
                    if control in ("frequency", "volume"):
                        t = max(0., min(1., (x - left) / max(1, width - 1))); self._stage(control, 60. + round(t * 4940.) if control == "frequency" else round(t * 20.) / 20.)
                    else: self._activate(control)
                    return

    def update(self, dt: float) -> None:
        if self._shutdown_requested: return
        if self._pending_layout is not None:
            return
        snapshot = self._audio.latest_snapshot() if self._audio is not None else None
        if snapshot is not None:
            self._audio_status = snapshot.status
            for particle in self._particles: particle.update_from_audio(snapshot)
        if not self._settings.microphone_enabled and self._settings.volume > 0.0:
            chunk = self._audio.next_playback_chunk() if self._audio is not None else None
            if chunk is not None and self._mixer_available:
                try:
                    if self._mixer is None:
                        self._mixer = self._mixer_factory(self.pygame)
                        self._mixer.initialize(chunk.sample_rate, chunk.channels, chunk.sample_width)
                    self._mixer.submit(chunk)
                except BaseException as exc: self._mixer_available = False; self._audio_diagnostic = "error"; self._record_error(exc)
        elif self._mixer is not None:
            try: self._mixer.stop()
            except BaseException as exc: self._record_error(exc)
        if self._pending_layout is None: self._snapshots = [p.snapshot() for p in self._particles]
        if self._drawing and len(self._previous_positions) == len(self._snapshots):
            for before, after in zip(self._previous_positions, self._snapshots): draw_stroke(self._canvas, [before, (round(after.position[0]), round(after.position[1]))], self._settings.brush_color, self._settings.brush_size, self._settings.brush_style)
        self._previous_positions = [(round(s.position[0]), round(s.position[1])) for s in self._snapshots]

    def render(self) -> None:
        if self._screen is None:
            self._screen = self.pygame.display.set_mode((self.width, self.height)); self.pygame.display.set_caption("Draw With Your Voice!")
            try: self._font = self.pygame.font.Font(None, 16)
            except BaseException as exc: self._record_error(exc)
        self._screen.blit(self._canvas, (0, 0))
        for snapshot in self._snapshots: draw_particle_marker(self._screen, (round(snapshot.position[0]), round(snapshot.position[1])), snapshot.color, 6)
        if self._font is not None:
            values = self._pending_settings or self._settings
            mic_label = {"none": "MIC OFF", "unavailable": "MIC UNAVAILABLE", "error": "MIC ERROR"}.get(self._audio_diagnostic, "MIC ON" if self._settings.microphone_enabled else "MIC OFF")
            pending = " PENDING" if self._pending_settings is not None else ""
            labels = (
                f"Particles: {values.particle_count}{pending} | Brush color: {values.brush_color} | Size: {values.brush_size} | Style: {values.brush_style}",
                f"Plate: {values.plate_shape} | Frequency: {values.frequency_hz:.0f} Hz | Volume: {values.volume:.2f} | Presets: 60 120 220 440 528 880 Hz",
                f"Square n: {values.square_n} | Square m: {values.square_m} | Circular order: {values.circular_order} | Circular root: {values.circular_root_index}",
                f"Circular cosine weight: {values.circular_cosine_weight:.1f} | Circular sine weight: {values.circular_sine_weight:.1f}",
                f"{mic_label} | {'DRAW ON' if self._drawing else 'DRAW OFF'} | Focus: {self._focused()}",
            )
            for row, label in enumerate(labels): self._screen.blit(self._font.render(label, True, (0, 0, 0)), (8, 2 + row * 18))
            if self._mic_icon is not None: self._screen.blit(self._mic_icon, (600, 2))
            focus_rect = HITBOXES.get(self._focused())
            if focus_rect: self.pygame.draw.rect(self._screen, (0, 0, 0), focus_rect, width=1)
            if self._settings.microphone_enabled: self._screen.blit(self._font.render("DISABLED WHILE MIC ON", True, (80, 80, 80)), (8, 92))
            if self._error_message: self._screen.blit(self._font.render(str(self._error_message)[:100], True, (180, 0, 0)), (300, 92))
        self.pygame.display.flip()

    def shutdown(self) -> None:
        if self._shutdown_requested and self._audio is None and not self._particles: return
        self._shutdown_requested = True
        if self._audio is not None:
            try: self._audio.stop()
            except BaseException as exc: self._record_error(exc)
            try:
                if not self._audio.join(1.0): self._record_error("audio worker did not stop")
            except BaseException as exc: self._record_error(exc)
        for particle in self._particles:
            try: particle.stop()
            except BaseException as exc: self._record_error(exc)
        for particle in self._particles:
            try:
                if not particle.join(1.0): self._record_error("particle worker did not stop")
            except BaseException as exc: self._record_error(exc)
        if self._mixer is not None:
            try: self._mixer.stop()
            except BaseException as exc: self._record_error(exc)
            try: self._mixer.close()
            except BaseException as exc: self._record_error(exc)
        self._particles, self._audio = [], None
        try: self.pygame.quit()
        except BaseException as exc: self._record_error(exc)

    def run(self) -> int:
        try:
            while not self._shutdown_requested:
                for event in self._event_source(): self.handle_event(event)
                self.update(1.0 / 60.0); self.render(); self._clock.tick(60)
        finally: self.shutdown()
        return 0

def main(*, pygame_api=None, audio_factory=AudioProducer, particle_factory=Particle, mixer_factory=None, frame_clock_factory=None, event_source=None, width=800, height=600) -> int:
    if pygame_api is None:
        import pygame as pygame_api
    pygame_api.init()
    return Application(pygame_api=pygame_api, audio_factory=audio_factory, particle_factory=particle_factory, mixer_factory=mixer_factory, frame_clock_factory=frame_clock_factory, event_source=event_source, width=width, height=height).run()

if __name__ == "__main__": main()
