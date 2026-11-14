import math
import sys
import threading

import pytest

import particle as particle_module
from particle import Particle, ParticleSnapshot, circular_value, square_value
from settings import Settings


BOUNDS = (38.0, 118.0, 762.0, 578.0)


def make_particle(**changes):
    return Particle((400.0, 206.0), BOUNDS, Settings().with_updates(**changes))


class Audio:
    def __init__(self, *, frequency_hz=440.0, amplitude=1.0, volume=0.5, sequence=1, timestamp_monotonic=0.0, status="ok"):
        self.frequency_hz = frequency_hz
        self.amplitude = amplitude
        self.volume = volume
        self.sequence = sequence
        self.timestamp_monotonic = timestamp_monotonic
        self.status = status


class FakeClock:
    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value


def test_snapshot_is_typed_immutable_and_initial_state():
    particle = make_particle()
    snap = particle.snapshot()
    assert isinstance(snap, ParticleSnapshot)
    assert snap.position == (400.0, 206.0)
    assert snap.velocity == (0.0, 0.0)
    assert snap.last_valid_position == snap.position
    with pytest.raises(AttributeError):
        snap.position = (1.0, 1.0)


@pytest.mark.parametrize("x,y,n,m,expected", [(0, 0, 1, 2, 0.0), (0.5, 0.5, 1, 2, 0.0), (-0.75, -0.5, 1, 2, -0.5), (0, 0.5, 1, 2, -math.sqrt(0.5))])
def test_square_vectors(x, y, n, m, expected):
    assert square_value(x, y, n, m) == pytest.approx(expected, abs=1e-10)


def test_square_canonicalization_and_equal_modes():
    assert square_value(0.2, -0.4, 2, 1) == square_value(0.2, -0.4, 1, 2)
    assert square_value(0.2, -0.4, 3, 3) == 0.0


@pytest.mark.parametrize("args", [(0, 0, 0, 1, 1, 0), (0, 0, 1, 9, 1, 0), (0, 0, 1, 1, 0, 0), (2, 0, 1, 1, 1, 0), (0, math.nan, 1, 1, 1, 0)])
def test_equation_invalid_inputs(args):
    with pytest.raises((ValueError, RuntimeError)):
        if args[2] == 0:
            square_value(*args[:2], args[2], args[3])
        else:
            circular_value(*args)


def test_circular_vectors_and_normalized_weights():
    assert circular_value(0, 0, 0, 1, 1, 0) == pytest.approx(1.0, abs=1e-10)
    assert circular_value(1, 0, 0, 1, 1, 0) == pytest.approx(0.0, abs=1e-10)
    assert circular_value(0.5, 0, 0, 1, 1, 0) == pytest.approx(0.669929739, abs=1e-8)
    assert circular_value(0.5, 0, 0, 1, 0.5, 0) == pytest.approx(circular_value(0.5, 0, 0, 1, 1, 0), abs=1e-10)


def test_particle_mapping_vectors_and_sine_signs():
    particle = make_particle(plate_shape="circular", circular_order=1, circular_cosine_weight=0.0, circular_sine_weight=1.0)
    assert particle._field(762.0, 348.0) == pytest.approx(0.0, abs=1e-10)
    assert particle._field(38.0, 348.0) == pytest.approx(0.0, abs=1e-10)
    assert particle._field(400.0, 118.0) > 0
    assert particle._field(400.0, 578.0) < 0

    cosine_particle = make_particle(
        plate_shape="circular",
        circular_order=1,
        circular_cosine_weight=1.0,
        circular_sine_weight=0.0,
    )
    assert cosine_particle._field(762.0, 348.0) > 0
    assert cosine_particle._field(38.0, 348.0) < 0


def test_manual_precedence_and_stale_audio_fallback():
    clock = lambda: 1.0
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=clock)
    particle.update_from_audio(Audio(frequency_hz=5000.0, volume=1.0, timestamp_monotonic=1.0))
    assert particle._inputs() == (5000.0, 1.0)
    particle.update_from_audio(Audio(frequency_hz=60.0, volume=1.0, timestamp_monotonic=0.0, status="stale"))
    assert particle._inputs() == (5000.0, 1.0)
    particle.update_from_audio(Audio(frequency_hz=60.0, volume=1.0, timestamp_monotonic=-1.0))
    assert particle._inputs() == (5000.0, 1.0)
    particle.update_settings(Settings().with_updates(microphone_enabled=False, frequency_hz=60.0, volume=0.25))
    assert particle._inputs() == (60.0, 0.25)


def test_audio_sequence_precedence_errors_and_recovery():
    clock = lambda: 10.0
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=clock)
    valid = Audio(frequency_hz=5000.0, volume=1.0, sequence=4, timestamp_monotonic=10.0)
    particle.update_from_audio(valid)
    particle.update_from_audio(Audio(frequency_hz=60.0, volume=0.1, sequence=3, timestamp_monotonic=10.0))
    particle.update_from_audio(Audio(frequency_hz=60.0, volume=0.1, sequence=4, timestamp_monotonic=10.0))
    assert particle._inputs() == (5000.0, 1.0)

    for status in ("overflow", "device_error"):
        particle.update_from_audio(Audio(frequency_hz=60.0, volume=0.1, sequence=5, timestamp_monotonic=10.0, status=status))
        assert particle._inputs() == (5000.0, 1.0)
    particle.update_from_audio(object())
    assert particle._inputs() == (5000.0, 1.0)

    particle.update_from_audio(Audio(frequency_hz=60.0, volume=0.25, sequence=6, timestamp_monotonic=10.0))
    assert particle._inputs() == (60.0, 0.25)


def test_concurrent_audio_updates_and_snapshots_are_coherent():
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=lambda: 1.0)
    pairs = ((60.0, 0.1), (440.0, 0.5), (5000.0, 1.0), (220.0, 0.25))
    sequence_lock = threading.Lock()
    next_sequence = 0
    failures = []
    barrier = threading.Barrier(8)

    def updater(index):
        nonlocal next_sequence
        try:
            barrier.wait()
            for _ in range(100):
                with sequence_lock:
                    next_sequence += 1
                    sequence = next_sequence
                frequency, volume = pairs[index % len(pairs)]
                particle.update_from_audio(
                    Audio(
                        frequency_hz=frequency,
                        amplitude=float(index % 2),
                        volume=volume,
                        sequence=sequence,
                        timestamp_monotonic=1.0,
                    )
                )
        except BaseException as exc:  # expose thread failures to the test
            failures.append(exc)

    def reader():
        try:
            barrier.wait()
            for _ in range(200):
                snapshot = particle.snapshot()
                frequency, volume = particle._inputs()
                assert (frequency, volume) in pairs
                assert snapshot.error is None
        except BaseException as exc:
            failures.append(exc)

    threads = [threading.Thread(target=updater, args=(i,)) for i in range(4)]
    threads += [threading.Thread(target=reader) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    assert particle._inputs() in pairs


def test_amplitude_is_metadata_only_and_not_motion_gain():
    first = Particle((400.0, 206.0), BOUNDS, Settings(), clock=lambda: 1.0)
    second = Particle((400.0, 206.0), BOUNDS, Settings(), clock=lambda: 1.0)
    first.update_from_audio(Audio(amplitude=0.0, volume=1.0, sequence=1, timestamp_monotonic=1.0))
    second.update_from_audio(Audio(amplitude=1.0, volume=1.0, sequence=1, timestamp_monotonic=1.0))
    assert first.step(0.05) == second.step(0.05)


def test_motion_is_persistent_and_dt_is_clamped():
    particle = make_particle(frequency_hz=5000.0, volume=1.0)
    first = particle.step(1.0)
    assert first.position == (400.0, 206.0)
    second = particle.step(0.1)
    assert second.position != first.position
    assert second.velocity == first.velocity
    assert all(BOUNDS[i] <= second.position[i // 2] <= BOUNDS[i + 2] for i in (0, 1))


def test_reflection_handles_overshoot_and_corner():
    particle = make_particle(volume=0.0)
    particle._position = (760.0, 576.0)
    particle._velocity = (200.0, 240.0)
    snap = particle.step(0.05)
    assert snap.position == pytest.approx((754.0, 568.0))
    assert snap.velocity[0] < 0 and snap.velocity[1] < 0


def test_multi_period_reflection_stays_in_bounds():
    position, velocity = particle_module._reflect(3000.0, 20000.0, 38.0, 762.0)
    assert 38.0 <= position <= 762.0
    assert velocity == 20000.0


def test_frequency_and_volume_endpoints():
    particle = Particle(
        (400.0, 206.0),
        BOUNDS,
        Settings().with_updates(microphone_enabled=False, frequency_hz=60.0, volume=1.0),
    )
    assert particle._inputs() == (60.0, 1.0)


def test_nonfinite_field_retains_last_valid_state(monkeypatch):
    particle = make_particle()
    before = particle.snapshot()
    monkeypatch.setattr(particle, "_field", lambda *_: math.nan)
    after = particle.step(0.1)
    assert after.position == before.position
    assert after.velocity == before.velocity
    assert after.error is not None


def test_settings_update_is_atomic_and_snapshot_coherent():
    particle = make_particle()
    particle.update_settings(Settings().with_updates(brush_size=12, brush_style="square"))
    snap = particle.snapshot()
    assert (snap.brush_size, snap.brush_style) == (12, "square")


def test_worker_lifecycle_is_idempotent_and_bounded():
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=FakeClock())
    assert particle.join() is True
    particle.start()
    particle.start()
    particle.stop()
    assert particle.join(1.0) is True
    with pytest.raises(RuntimeError):
        particle.start()


def test_worker_exception_is_retained_and_join_does_not_raise(monkeypatch):
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=FakeClock())
    error = RuntimeError("boom")
    monkeypatch.setattr(particle, "step", lambda _dt: (_ for _ in ()).throw(error))
    particle.start()
    assert particle.join(1.0) is True
    assert particle.worker_error is error
    assert particle.join(0.0) is True


def test_join_returns_false_for_still_running_worker(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=FakeClock())

    def blocked_step(_dt):
        entered.set()
        release.wait()
        return particle.snapshot()

    monkeypatch.setattr(particle, "step", blocked_step)
    particle.start()
    assert entered.wait(1.0)
    particle.stop()
    assert particle.join(0.0) is False
    release.set()
    assert particle.join(1.0) is True


def test_join_rejects_invalid_timeout():
    particle = make_particle()
    with pytest.raises(ValueError):
        particle.join(-1)
    with pytest.raises(ValueError):
        particle.join(math.inf)


def test_worker_has_no_pygame_dependency():
    assert "pygame" not in particle_module.__dict__


def test_worker_execution_spy_proves_no_pygame_calls(monkeypatch):
    calls = []

    class ForbiddenPygame:
        def __getattr__(self, name):
            raise AssertionError(f"worker accessed pygame.{name}")

    monkeypatch.setitem(sys.modules, "pygame", ForbiddenPygame())
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=FakeClock())
    original_step = particle.step

    def spy(dt):
        calls.append(dt)
        return original_step(dt)

    monkeypatch.setattr(particle, "step", spy)
    particle.start()
    particle.stop()
    assert particle.join(1.0) is True
    assert calls


def test_worker_audio_integration_uses_updated_snapshot_without_sleep():
    clock = FakeClock()
    particle = Particle((400.0, 206.0), BOUNDS, Settings(), clock=clock)
    first_step = threading.Event()
    audio_seen = threading.Event()
    original_inputs = particle._inputs

    def observed_inputs():
        result = original_inputs()
        if result == (5000.0, 1.0):
            audio_seen.set()
        return result

    original_step = particle.step

    def observed_step(dt):
        first_step.set()
        return original_step(dt)

    particle._inputs = observed_inputs
    particle.step = observed_step
    particle.start()
    assert first_step.wait(1.0)
    particle.update_from_audio(
        Audio(frequency_hz=5000.0, volume=1.0, sequence=1, timestamp_monotonic=0.0)
    )
    assert audio_seen.wait(1.0)
    particle.stop()
    assert particle.join(1.0) is True


def test_circular_mode_reports_scipy_unavailable(monkeypatch):
    monkeypatch.setattr(particle_module, "_SCIPY_IMPORT_ERROR", ImportError("blocked"))
    monkeypatch.setattr(particle_module, "jv", None)
    monkeypatch.setattr(particle_module, "jn_zeros", None)
    with pytest.raises(RuntimeError, match="SciPy is unavailable"):
        circular_value(0.5, 0.0, 0, 1, 1.0, 0.0)
