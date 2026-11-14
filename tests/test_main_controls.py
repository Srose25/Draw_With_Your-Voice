from __future__ import annotations

import os
import subprocess
import sys
import threading
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
import pytest

from audio_producer import AudioSnapshot, PlaybackChunk
from main import Application, CONTROL_ORDER, HITBOXES, apply_control_change
import main as main_module
from settings import Settings, SettingsValidationError


class FakeClock:
    def tick(self, _fps):
        return 16


class FakeAudio:
    def __init__(self, settings, log):
        self.settings = settings
        self.log = log
        self.log.append(("audio-create", settings.microphone_enabled))
    def start(self): self.log.append("audio-start")
    def stop(self): self.log.append("audio-stop")
    def join(self, _timeout=1.0): self.log.append("audio-join"); return True
    def latest_snapshot(self): return AudioSnapshot(self.settings.frequency_hz, 0.0, self.settings.volume, 1, 1.0, "manual")
    def next_playback_chunk(self): return None


class FakeParticle:
    def __init__(self, anchor, bounds, settings, log):
        self.anchor, self.bounds, self.settings, self.log = anchor, bounds, settings, log
        self.audio_updates = 0
        self.log.append(("particle-create", anchor))
    def start(self): self.log.append("particle-start")
    def stop(self): self.log.append("particle-stop")
    def join(self, _timeout=1.0): self.log.append("particle-join"); return True
    def update_settings(self, settings): self.settings = settings
    def update_from_audio(self, _snapshot): self.audio_updates += 1
    def snapshot(self):
        from particle import ParticleSnapshot
        return ParticleSnapshot(self.anchor, (0.0, 0.0), self.anchor, self.settings.brush_color, self.settings.brush_size, self.settings.brush_style, self.anchor, None)


class FakeMixer:
    def __init__(self, _pygame, log): self.log = log; self.initialized = []; self.thread_ids = []
    def initialize(self, *args): self.log.append("mixer-init"); self.initialized.append(args); self.thread_ids.append(threading.get_ident())
    def submit(self, _chunk): self.log.append("mixer-submit"); self.thread_ids.append(threading.get_ident())
    def stop(self): self.log.append("mixer-stop"); self.thread_ids.append(threading.get_ident())
    def close(self): self.log.append("mixer-close"); self.thread_ids.append(threading.get_ident())


class StopFailAudio(FakeAudio):
    def stop(self): self.log.append("audio-stop"); raise RuntimeError("audio stop failed")


class InitFailMixer(FakeMixer):
    def initialize(self, *_args): self.log.append("mixer-init"); raise RuntimeError("mixer init failed")


class SpyFont:
    def __init__(self): self.text = []
    def render(self, text, *_args):
        self.text.append(text)
        return pygame.Surface((2, 2))


@pytest.fixture
def app():
    pygame.init()
    log = []
    value = Application(
        pygame_api=pygame,
        audio_factory=lambda settings: FakeAudio(settings, log),
        particle_factory=lambda anchor, bounds, settings: FakeParticle(anchor, bounds, settings, log),
        mixer_factory=lambda api: FakeMixer(api, log),
        frame_clock_factory=FakeClock,
        settings=Settings(microphone_enabled=True),
    )
    value._test_log = log
    yield value
    value.shutdown()


def event(api, key, mod=0): return SimpleNamespace(type=api.KEYDOWN, key=key, mod=mod)


def test_import_main_has_no_runtime_side_effect():
    result = subprocess.run([sys.executable, "-c", "import pygame; import main; print(pygame.get_init())"], cwd=os.getcwd(), capture_output=True, text=True, env={**os.environ, "SDL_VIDEODRIVER": "dummy"}, check=True)
    assert result.stdout.strip().splitlines()[-1] == "False"


def test_initial_consent_is_off_and_ui_state_is_frozen(app):
    assert app.ui_state.settings.microphone_enabled is False
    assert app.ui_state.audio_status == "manual"
    with pytest.raises(Exception): app.ui_state.focus_control = "clear"


def test_focus_wrap_and_frequency_keyboard_edit(app):
    for _ in range(len(CONTROL_ORDER) - 1): app.handle_event(event(pygame, pygame.K_TAB))
    assert app.ui_state.focus_control == "clear"
    app.handle_event(event(pygame, pygame.K_TAB))
    assert app.ui_state.focus_control == "particle_count"
    app._focus_index = CONTROL_ORDER.index("frequency")
    app.handle_event(event(pygame, pygame.K_RIGHT))
    assert app.ui_state.pending_settings.frequency_hz == 450.0
    assert app.ui_state.settings.frequency_hz == 440.0
    app.handle_event(event(pygame, pygame.K_RETURN))
    assert app.ui_state.settings.frequency_hz == 450.0


def test_slider_endpoints_and_escape(app):
    left, top, width, _height = HITBOXES["frequency"]
    app.handle_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(left, top)))
    assert app.ui_state.pending_settings.frequency_hz == 60.0
    app.handle_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(left + width - 1, top)))
    assert app.ui_state.pending_settings.frequency_hz == 5000.0
    app.handle_event(event(pygame, pygame.K_ESCAPE))
    assert app.ui_state.settings.frequency_hz == 440.0
    assert app.ui_state.pending_settings is None


def test_settings_control_is_atomic_and_rejects_invalid():
    original = Settings()
    with pytest.raises(SettingsValidationError): apply_control_change(original, "frequency_hz", 5001.0)
    assert original.frequency_hz == 440.0
    assert apply_control_change(original, "frequency_preset", 528).frequency_hz == 528.0


@pytest.mark.parametrize("control,value", [
    ("brush_size", 10), ("brush_color", (1, 2, 3)), ("brush_style", "square"),
    ("particle_count", 2), ("microphone_enabled", False), ("frequency_hz", 500.0),
    ("volume", 0.7), ("plate_shape", "circular"), ("square_n", 3), ("square_m", 4),
    ("circular_order", 1), ("circular_root_index", 2), ("circular_cosine_weight", 0.5),
    ("circular_sine_weight", 0.5),
])
def test_every_settings_control_accepts_valid_value(control, value):
    assert apply_control_change(Settings(), control, value).to_dict()[control] == value


@pytest.mark.parametrize("control,value", [("brush_size", 0), ("frequency_hz", 5001.0), ("volume", 2.0), ("plate_shape", "triangle"), ("square_n", 9), ("circular_order", 9)])
def test_settings_controls_reject_invalid_values_without_mutation(control, value):
    original = Settings()
    with pytest.raises(SettingsValidationError): apply_control_change(original, control, value)
    assert original == Settings()


@pytest.mark.parametrize("control,value", [
    ("brush_size", 0), ("brush_color", (1, 2)), ("brush_style", "bad"), ("particle_count", 0),
    ("microphone_enabled", "yes"), ("frequency_hz", 59.0), ("volume", -0.1), ("plate_shape", "bad"),
    ("square_n", 0), ("square_m", 9), ("circular_order", 9), ("circular_root_index", 0),
    ("circular_cosine_weight", 2.0), ("circular_sine_weight", -2.0),
])
def test_each_settings_field_has_an_invalid_path(control, value):
    with pytest.raises(SettingsValidationError): apply_control_change(Settings(), control, value)


def test_particle_count_pending_commit_and_cancel(app):
    app._focus_index = CONTROL_ORDER.index("particle_count")
    app.handle_event(event(pygame, pygame.K_RIGHT))
    assert app.ui_state.pending_layout is not None
    app.handle_event(event(pygame, pygame.K_ESCAPE))
    assert app.ui_state.pending_layout is None
    app.handle_event(event(pygame, pygame.K_RIGHT))
    app.handle_event(event(pygame, pygame.K_RETURN))
    assert app.ui_state.settings.particle_count == 2
    assert len(app.particles) == 2


def test_drawing_clear_and_render_are_headless(app):
    app.handle_event(event(pygame, pygame.K_e))
    app.update(0.016)
    app.render()
    app.handle_event(event(pygame, pygame.K_c))
    assert app.ui_state.drawing_enabled is True


def test_microphone_on_skips_equation_controls_and_rejects_direct_edit(app):
    app._commit_settings(app.ui_state.settings.with_updates(microphone_enabled=True))
    assert app.ui_state.focus_control not in {"square_n", "square_m", "circular_order", "circular_root_index", "circular_cosine_weight", "circular_sine_weight"}
    app._stage("square_n", 4)
    assert app.ui_state.error_message == "DISABLED WHILE MIC ON"
    assert app.ui_state.pending_settings is None
    left, top, _width, _height = HITBOXES["square_n"]
    app.handle_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(left, top)))
    assert app.ui_state.error_message == "DISABLED WHILE MIC ON"


def test_pending_layout_pauses_audio_and_drawing_updates(app):
    app._focus_index = CONTROL_ORDER.index("particle_count")
    app.handle_event(event(pygame, pygame.K_RIGHT))
    before = [p.audio_updates for p in app.particles]
    app.update(0.016)
    assert [p.audio_updates for p in app.particles] == before


def test_e_is_ignored_during_pending_numeric_edit(app):
    app._focus_index = CONTROL_ORDER.index("frequency")
    app.handle_event(event(pygame, pygame.K_RIGHT))
    assert app.ui_state.pending_settings is not None
    app.handle_event(event(pygame, pygame.K_e))
    assert app.ui_state.drawing_enabled is False


def test_mixer_gets_at_most_one_chunk_and_icon_is_rendered(app):
    chunk = PlaybackChunk(b"\x00\x00" * 512, 48000, 1, 2, 440.0, 0.5, 1)
    app._audio.next_playback_chunk = lambda: chunk
    app.update(0.016)
    app.update(0.016)
    assert "mixer-init" in app._test_log
    assert app._mixer.initialized == [(48000, 1, 2)]
    assert set(app._mixer.thread_ids) == {threading.get_ident()}
    assert app._test_log.count("mixer-submit") == 2
    app.render()
    assert app._mic_icon is not None


def test_render_labels_pending_and_all_equation_values(app):
    app._font = SpyFont()
    app._screen = pygame.Surface((800, 600))
    pygame.display.set_mode((800, 600))
    app._mic_icon = pygame.Surface((8, 8))
    app._focus_index = CONTROL_ORDER.index("frequency")
    app.handle_event(event(pygame, pygame.K_RIGHT))
    app.render()
    rendered = " | ".join(app._font.text)
    assert "PENDING" in rendered
    assert "Presets" in rendered
    assert "Circular cosine weight" in rendered
    assert "Circular sine weight" in rendered


def test_mixer_failure_keeps_particles_running(app):
    app._audio.next_playback_chunk = lambda: PlaybackChunk(b"\x00\x00" * 512, 48000, 1, 2, 440.0, 0.5, 1)
    app._mixer_factory = lambda _api: (_ for _ in ()).throw(RuntimeError("mixer unavailable"))
    app.update(0.016)
    assert app.ui_state.mixer_available is False
    assert app.ui_state.error_message == "mixer unavailable"
    assert len(app.particles) == 1


def test_zero_volume_stops_existing_mixer(app):
    chunk = PlaybackChunk(b"\x00\x00" * 512, 48000, 1, 2, 440.0, 0.5, 1)
    app._audio.next_playback_chunk = lambda: chunk
    app.update(0.016)
    app._commit_settings(app.ui_state.settings.with_updates(volume=0.0))
    assert "mixer-stop" in app._test_log


def test_microphone_enable_stops_existing_mixer_and_shift_tab_wraps(app):
    chunk = PlaybackChunk(b"\x00\x00" * 512, 48000, 1, 2, 440.0, 0.5, 1)
    app._audio.next_playback_chunk = lambda: chunk
    app.update(0.016)
    app._commit_settings(app.ui_state.settings.with_updates(microphone_enabled=True))
    assert "mixer-stop" in app._test_log
    app.handle_event(event(pygame, pygame.K_TAB, pygame.KMOD_SHIFT))
    assert app.ui_state.focus_control == "clear"


def test_microphone_labels_and_recovery_diagnostic_are_rendered(app):
    app._font = SpyFont(); app._screen = pygame.Surface((800, 600)); pygame.display.set_mode((800, 600)); app._mic_icon = pygame.Surface((8, 8))
    for diagnostic in ("unavailable", "error"):
        app._audio_diagnostic = diagnostic
        app.render()
        assert any("MIC " + diagnostic.upper() in text for text in app._font.text)


def test_keyboard_and_mouse_paths_reach_presets_and_toggles(app):
    for name in ("preset_60", "preset_120", "preset_220", "preset_440", "preset_528", "preset_880"):
        left, top, width, height = HITBOXES[name]
        app.handle_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(left + width // 2, top + height // 2)))
        app.handle_event(event(pygame, pygame.K_RETURN))
    mic_left, mic_top, _mic_width, _mic_height = HITBOXES["microphone_enabled"]
    app.handle_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(mic_left, mic_top)))
    assert app.ui_state.settings.microphone_enabled is True


def test_all_hitbox_edges_and_focus_traversal(app):
    visited = set()
    for _ in range(len(CONTROL_ORDER)):
        visited.add(app.ui_state.focus_control)
        app.handle_event(event(pygame, pygame.K_TAB))
    assert visited == set(CONTROL_ORDER)
    for name, (left, top, width, height) in HITBOXES.items():
        app.handle_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(left, top)))
        assert app.ui_state.focus_control == name
        app.handle_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(left + width - 1, top + height - 1)))
        if name == "microphone_enabled": app._commit_settings(app.ui_state.settings.with_updates(microphone_enabled=False))


def test_actual_icon_and_marker_geometry_are_rendered(app, monkeypatch):
    class ScreenSpy:
        def __init__(self): self.blits = []
        def blit(self, source, pos): self.blits.append((source, pos))
    spy = ScreenSpy(); app._screen = spy; app._font = SpyFont(); app._mic_icon = pygame.Surface((8, 8))
    monkeypatch.setattr(main_module, "draw_particle_marker", lambda *_args: None)
    monkeypatch.setattr(pygame.draw, "rect", lambda *_args, **_kwargs: None)
    pygame.display.set_mode((800, 600)); app.render()
    assert any(source is app._mic_icon and pos == (600, 2) for source, pos in spy.blits)


def test_mixer_stop_failure_still_closes(app):
    class BadMixer(FakeMixer):
        def stop(self): self.log.append("mixer-stop"); raise RuntimeError("stop failed")
    app._mixer = BadMixer(pygame, app._test_log)
    app.shutdown()
    assert "mixer-close" in app._test_log


def test_all_presets_and_toggle_controls_are_reachable(app):
    for name, value in (("brush_color", None), ("brush_style", "square"), ("plate_shape", "circular")):
        app._activate(name)
        if value is not None: assert getattr(app.ui_state.settings, name) == value
    for preset, value in (("preset_60", 60.0), ("preset_120", 120.0), ("preset_220", 220.0), ("preset_440", 440.0), ("preset_528", 528.0), ("preset_880", 880.0)):
        app._activate(preset)
        assert app.ui_state.settings.frequency_hz == value
    assert all(name in CONTROL_ORDER for name in HITBOXES)


def test_audio_stop_failure_still_joins_and_quits():
    pygame.init(); log = []
    app = Application(pygame_api=pygame, audio_factory=lambda settings: StopFailAudio(settings, log),
                      particle_factory=lambda anchor, bounds, settings: FakeParticle(anchor, bounds, settings, log),
                      mixer_factory=lambda api: FakeMixer(api, log), frame_clock_factory=FakeClock)
    app.shutdown()
    assert "audio-join" in log


def test_mixer_init_failure_is_visible_and_particles_continue(app):
    app._audio.next_playback_chunk = lambda: PlaybackChunk(b"\x00\x00" * 512, 48000, 1, 2, 440.0, 0.5, 1)
    app._mixer_factory = lambda api: InitFailMixer(api, app._test_log)
    app.update(0.016)
    assert app.ui_state.mixer_available is False
    assert len(app.particles) == 1


def test_layout_commit_microphone_failure_syncs_new_particles():
    pygame.init(); log = []; calls = {"audio": 0}
    def audio_factory(settings):
        calls["audio"] += 1
        if calls["audio"] == 2:
            class BadAudio(FakeAudio):
                def start(self): raise RuntimeError("no microphone")
            return BadAudio(settings, log)
        return FakeAudio(settings, log)
    app = Application(pygame_api=pygame, audio_factory=audio_factory,
                      particle_factory=lambda anchor, bounds, settings: FakeParticle(anchor, bounds, settings, log),
                      mixer_factory=lambda api: FakeMixer(api, log), frame_clock_factory=FakeClock)
    app._pending_settings = app.ui_state.settings.with_updates(particle_count=2, microphone_enabled=True)
    app._pending_layout = __import__("helpers").begin_layout(2, 800, 600, app.ui_state.layout.generation)
    app._commit_pending()
    assert app.ui_state.settings.microphone_enabled is False
    assert all(p.settings.microphone_enabled is False for p in app.particles)
    app.shutdown()


def test_shutdown_is_idempotent_and_stops_workers(app):
    app.shutdown()
    app.shutdown()
    assert app.ui_state.shutdown_requested is True
    assert "audio-stop" in app._test_log
    assert "particle-stop" in app._test_log


def test_quit_event_ends_run(app):
    app._event_source = lambda: [SimpleNamespace(type=pygame.QUIT)]
    assert app.run() == 0
