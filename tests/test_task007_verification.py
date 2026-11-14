"""Final headless launch, cleanup, and resource-gate verification."""

from __future__ import annotations

import subprocess
import sys
import threading
from types import SimpleNamespace

import pygame

from audio_producer import AudioSnapshot, PlaybackChunk
from main import Application
from particle import ParticleSnapshot
from settings import Settings


class GateClock:
    def tick(self, _fps):
        return 16


class GateAudio:
    def __init__(self, settings, log, chunk=False):
        self.settings, self.log, self.chunk = settings, log, chunk
        self._stop = threading.Event()
        self._worker = None
        self.log.append("audio-create")
    def start(self):
        self.log.append("audio-start")
        self._worker = threading.Thread(target=self._stop.wait, name="audio-producer")
        self._worker.start()
    def stop(self): self.log.append("audio-stop"); self._stop.set()
    def join(self, _timeout=1.0):
        self.log.append("audio-join")
        if self._worker is not None: self._worker.join(_timeout)
        return self._worker is None or not self._worker.is_alive()
    def latest_snapshot(self): return AudioSnapshot(440.0, 0.0, self.settings.volume, 1, 0.0, "manual")
    def next_playback_chunk(self):
        if not self.chunk: return None
        return PlaybackChunk(b"\x00\x00" * 512, 48000, 1, 2, 440.0, self.settings.volume, 1)


class GateParticle:
    def __init__(self, anchor, _bounds, settings, log):
        self.anchor, self.settings, self.log = anchor, settings, log
        self._stop = threading.Event()
        self._worker = None
    def start(self):
        self.log.append("particle-start")
        self._worker = threading.Thread(target=self._stop.wait, name="particle-worker")
        self._worker.start()
    def stop(self): self.log.append("particle-stop"); self._stop.set()
    def join(self, _timeout=1.0):
        self.log.append("particle-join")
        if self._worker is not None: self._worker.join(_timeout)
        return self._worker is None or not self._worker.is_alive()
    def update_settings(self, settings): self.settings = settings
    def update_from_audio(self, _snapshot): pass
    def snapshot(self): return ParticleSnapshot(self.anchor, (0.0, 0.0), self.anchor, self.settings.brush_color, self.settings.brush_size, self.settings.brush_style, self.anchor, None)


class GateMixer:
    def __init__(self, _pygame, log): self.log = log
    def initialize(self, *_args): self.log.append("mixer-init")
    def submit(self, _chunk): self.log.append("mixer-submit")
    def stop(self): self.log.append("mixer-stop")
    def close(self): self.log.append("mixer-close")


def make_app(log, *, chunk=False, mixer_factory=None):
    pygame.init()
    return Application(
        pygame_api=pygame,
        settings=Settings(microphone_enabled=False),
        audio_factory=lambda settings: GateAudio(settings, log, chunk=chunk),
        particle_factory=lambda anchor, bounds, settings: GateParticle(anchor, bounds, settings, log),
        mixer_factory=mixer_factory or (lambda api: GateMixer(api, log)),
        frame_clock_factory=GateClock,
        event_source=lambda: [SimpleNamespace(type=pygame.QUIT)],
    )


def test_headless_quit_orders_cleanup_and_returns_zero(monkeypatch):
    log = []
    original_quit = pygame.quit
    def quit_with_log():
        log.append("pygame-quit")
        original_quit()
    monkeypatch.setattr(pygame, "quit", quit_with_log)
    app = make_app(log, chunk=True)
    app.update(0.016)
    assert app.run() == 0
    assert "pygame-quit" == log[-1]
    assert log.index("audio-stop") < log.index("particle-stop") < log.index("mixer-stop") < log.index("mixer-close") < log.index("pygame-quit")
    assert "audio-join" in log and "particle-join" in log
    assert not {thread.name for thread in threading.enumerate()} & {"audio-producer", "particle-worker"}
    app.shutdown()


def test_repeated_shutdown_is_harmless():
    log = []
    app = make_app(log)
    app.shutdown()
    app.shutdown()
    assert log.count("audio-stop") == 1
    assert log.count("particle-stop") == 1


def test_factory_start_stop_join_and_mixer_failures_are_best_effort():
    log = []
    class FaultAudio(GateAudio):
        def start(self): super().start(); raise RuntimeError("audio start failure")
        def stop(self): super().stop(); raise RuntimeError("audio stop failure")
        def join(self, _timeout=1.0): super().join(_timeout); raise RuntimeError("audio join failure")
    class FaultParticle(GateParticle):
        def stop(self): super().stop(); raise RuntimeError("particle stop failure")
        def join(self, _timeout=1.0): super().join(_timeout); raise RuntimeError("particle join failure")
    audio_instances = iter((FaultAudio(Settings(microphone_enabled=False), log), GateAudio(Settings(microphone_enabled=False), log)))
    def failing_audio(_settings):
        try: return next(audio_instances)
        except StopIteration: raise RuntimeError("audio factory failure")
    class FaultMixer(GateMixer):
        def stop(self): super().stop(); raise RuntimeError("mixer stop failure")
        def close(self): super().close(); raise RuntimeError("mixer close failure")
    app = Application(
        pygame_api=pygame,
        settings=Settings(microphone_enabled=False),
        audio_factory=failing_audio,
        particle_factory=lambda anchor, bounds, settings: FaultParticle(anchor, bounds, settings, log),
        mixer_factory=lambda api: FaultMixer(api, log),
        frame_clock_factory=GateClock,
        event_source=lambda: [SimpleNamespace(type=pygame.QUIT)],
    )
    app.update(0.016)
    assert len(app.particles) == 1
    app.shutdown()
    assert not {thread.name for thread in threading.enumerate()} & {"audio-producer", "particle-worker"}
    mixer_log = []
    mixer_app = make_app(mixer_log, chunk=True, mixer_factory=lambda api: FaultMixer(api, mixer_log))
    mixer_app.update(0.016)
    mixer_app.shutdown()
    assert mixer_log.count("mixer-stop") == 1 and mixer_log.count("mixer-close") == 1


def test_importing_main_is_side_effect_free_and_manual_mode_avoids_input_stream():
    result = subprocess.run(
        [sys.executable, "-c", "import main, pygame; assert pygame.get_init() is False"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    app = make_app([])
    assert app.ui_state.settings.microphone_enabled is False
    app.shutdown()
