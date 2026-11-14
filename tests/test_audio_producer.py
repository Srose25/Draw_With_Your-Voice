import math
import threading

import numpy as np
import pytest

from audio_producer import AudioProducer, AudioSnapshot, PlaybackChunk
from settings import Settings
from tests.fakes import FakeMixer, FakeStream


class FakeClock:
    def __init__(self, value=1.0):
        self.value = value

    def __call__(self):
        return self.value


def sine_frame(bin_index=10, amplitude=0.8, size=512):
    return amplitude * np.sin(2.0 * np.pi * bin_index * np.arange(size) / size)


def make_producer(settings=None, stream=None, clock=None):
    stream = stream or FakeStream
    return AudioProducer(
        settings or Settings(),
        stream_factory=stream,
        clock=clock or FakeClock(),
    )


def test_snapshot_and_playback_types_are_immutable():
    producer = make_producer(Settings().with_updates(microphone_enabled=False))
    snapshot = producer.latest_snapshot()
    assert isinstance(snapshot, AudioSnapshot)
    assert snapshot.status == "manual"
    with pytest.raises(AttributeError):
        snapshot.frequency_hz = 1.0
    chunk = producer.next_playback_chunk()
    assert isinstance(chunk, PlaybackChunk)
    assert len(chunk.samples) == 512 * 2


def test_initial_microphone_state_is_silent():
    producer = make_producer(Settings())
    snapshot = producer.latest_snapshot()
    assert snapshot.status == "silent"
    assert snapshot.amplitude == 0.0
    assert snapshot.frequency_hz == 440.0


def test_latest_snapshot_lazily_publishes_stale_once_and_recovers():
    clock = FakeClock(1.0)
    producer = make_producer(Settings(), clock=clock)
    initial = producer.latest_snapshot()
    clock.value = 1.26
    stale = producer.latest_snapshot()
    assert stale.status == "stale"
    assert stale.sequence == initial.sequence + 1
    assert producer.latest_snapshot() == stale
    clock.value = 1.5
    assert producer.latest_snapshot() == stale
    producer._publish("ok", frequency=937.5, amplitude=0.8, volume=0.8)
    recovered = producer.latest_snapshot()
    assert recovered.status == "ok"
    assert recovered.sequence == stale.sequence + 1


def test_manual_snapshot_never_becomes_stale():
    clock = FakeClock(1.0)
    producer = make_producer(Settings().with_updates(microphone_enabled=False), clock=clock)
    clock.value = 100.0
    assert producer.latest_snapshot().status == "manual"


def test_fft_bin_mapping_and_amplitude():
    stream_holder = {}

    def factory(callback, sample_rate, channels, block_size):
        stream_holder["stream"] = FakeStream(callback, sample_rate, channels, block_size)
        return stream_holder["stream"]

    producer = make_producer(stream=factory)
    producer.start()
    stream_holder["stream"].emit(sine_frame())
    assert producer._pending_event.wait(1.0)
    for _ in range(100):
        snapshot = producer.latest_snapshot()
        if snapshot.status == "ok":
            break
        threading.Event().wait(0.01)
    assert snapshot.frequency_hz == pytest.approx(937.5, abs=1e-6)
    assert snapshot.amplitude == pytest.approx(0.8, abs=1e-6)
    assert snapshot.volume == pytest.approx(0.8, abs=1e-6)
    producer.stop()


def test_nonzero_dc_is_not_silence_and_is_rejected_as_out_of_range():
    producer = make_producer()
    producer._publish("ok", frequency=937.5, amplitude=0.25, volume=0.25)
    producer._process_frame(np.full(512, 0.25))
    snapshot = producer.latest_snapshot()
    assert snapshot.status == "device_error"
    assert snapshot.frequency_hz == pytest.approx(937.5)
    assert snapshot.amplitude == pytest.approx(0.25)
    assert snapshot.volume == pytest.approx(0.25)


def test_equal_magnitude_fft_tie_selects_lowest_bin():
    samples = sine_frame(bin_index=1, amplitude=0.4) + sine_frame(bin_index=2, amplitude=0.4)
    producer = make_producer()
    producer._process_frame(samples)
    snapshot = producer.latest_snapshot()
    assert snapshot.status == "ok"
    assert snapshot.frequency_hz == pytest.approx(93.75, abs=1e-6)


def test_fft_amplitude_clips_to_one():
    producer = make_producer()
    producer._process_frame(sine_frame(bin_index=10, amplitude=1.5))
    snapshot = producer.latest_snapshot()
    assert snapshot.status == "ok"
    assert snapshot.frequency_hz == pytest.approx(937.5, abs=1e-6)
    assert snapshot.amplitude == 1.0
    assert snapshot.volume == 1.0


def test_fft_dc_tie_silence_and_channel_average():
    holder = {}

    def factory(callback, sample_rate, channels, block_size):
        holder["stream"] = FakeStream(callback, sample_rate, channels, block_size)
        return holder["stream"]

    producer = make_producer(stream=factory)
    producer.start()
    holder["stream"].emit(np.zeros(512))
    threading.Event().wait(0.02)
    assert producer.latest_snapshot().status == "silent"
    holder["stream"].emit(np.column_stack((sine_frame(amplitude=0.8), sine_frame(amplitude=0.8))))
    threading.Event().wait(0.02)
    assert producer.latest_snapshot().status == "ok"
    producer.stop()


def test_latest_only_handoff_replaces_pending_frame():
    producer = make_producer()
    producer._started = True
    producer._callback(np.ones(512) * 0.1)
    producer._callback(np.ones(512) * 0.2)
    assert np.all(producer._pending_frame == 0.2)
    producer.stop()


def test_oversized_callback_is_rejected_before_copy():
    producer = make_producer()
    producer._started = True
    oversized = np.zeros(513)
    producer._callback(oversized)
    assert producer.latest_snapshot().status == "device_error"
    assert producer._pending_frame is None
    producer.stop()


def test_callback_handoff_is_bounded_and_nonblocking():
    producer = make_producer()
    producer._started = True
    frame = np.zeros(512)
    start = __import__("time").perf_counter()
    for _ in range(100):
        producer._callback(frame)
    elapsed = __import__("time").perf_counter() - start
    assert elapsed < 0.5
    assert producer._pending_frame is not None
    producer.stop()


@pytest.mark.parametrize("status,expected", [("input overflow", "overflow"), ("permission denied", "device_error")])
def test_callback_status_is_nonfatal(status, expected):
    producer = make_producer()
    producer._started = True
    producer._callback(np.zeros(512), status=status)
    assert producer.latest_snapshot().status == expected
    producer.stop()


@pytest.mark.parametrize("frame", [[], [math.nan] * 512, [math.inf] * 512, np.zeros((2, 2, 2))])
def test_malformed_frame_retains_last_valid_values(frame):
    producer = make_producer()
    producer._started = True
    producer._publish("ok", frequency=440.0, amplitude=0.5, volume=0.5)
    producer._callback(frame)
    snapshot = producer.latest_snapshot()
    assert snapshot.status == "device_error"
    assert (snapshot.frequency_hz, snapshot.amplitude, snapshot.volume) == (440.0, 0.5, 0.5)
    producer.stop()


def test_out_of_range_and_recovery():
    holder = {}

    def factory(callback, sample_rate, channels, block_size):
        holder["stream"] = FakeStream(callback, sample_rate, channels, block_size)
        return holder["stream"]

    producer = make_producer(stream=factory)
    producer.start()
    holder["stream"].emit(np.ones(512))
    threading.Event().wait(0.02)
    assert producer.latest_snapshot().status == "device_error"
    holder["stream"].emit(sine_frame())
    threading.Event().wait(0.02)
    assert producer.latest_snapshot().status == "ok"
    producer.stop()


def test_manual_playback_frequency_volume_and_stop_conditions():
    producer = make_producer(Settings().with_updates(microphone_enabled=False, frequency_hz=60.0, volume=1.0))
    chunk = producer.next_playback_chunk()
    assert chunk is not None
    assert (chunk.sample_rate, chunk.channels, chunk.sample_width, chunk.frequency_hz, chunk.volume) == (48000, 1, 2, 60.0, 1.0)
    assert producer.update_settings(Settings().with_updates(microphone_enabled=False, volume=0.0)) is None
    assert producer.next_playback_chunk() is None
    producer.update_settings(Settings())
    assert producer.next_playback_chunk() is None


def test_manual_playback_is_deterministic_and_nonduplicated():
    settings = Settings().with_updates(microphone_enabled=False, frequency_hz=440.0, volume=0.5)
    first = make_producer(settings).next_playback_chunk()
    second = make_producer(settings).next_playback_chunk()
    assert first is not None and second is not None
    assert first.samples == second.samples
    assert first.samples != first.samples[-2:] * 256


def test_start_stop_idempotence_and_callback_after_stop():
    holder = {}

    def factory(callback, sample_rate, channels, block_size):
        holder["stream"] = FakeStream(callback, sample_rate, channels, block_size)
        return holder["stream"]

    producer = make_producer(stream=factory)
    producer.start()
    producer.start()
    producer.stop()
    producer.stop()
    assert holder["stream"].close_calls == 1
    before = producer.latest_snapshot()
    holder["stream"].emit(sine_frame())
    assert producer.latest_snapshot() == before


def test_post_stop_pending_frame_is_released():
    producer = make_producer()
    producer._started = True
    producer._callback(np.zeros(512))
    assert producer._pending_frame is not None
    producer.stop()
    assert producer._pending_frame is None
    assert not producer._pending_event.is_set()


def test_start_after_completed_stop_is_rejected():
    producer = make_producer(Settings().with_updates(microphone_enabled=False))
    producer.start()
    producer.stop()
    with pytest.raises(RuntimeError):
        producer.start()


def test_device_failure_falls_back_without_raising():
    producer = make_producer(stream=lambda callback, sample_rate, channels, block_size: FakeStream(callback, sample_rate, channels, block_size, start_error=RuntimeError("no device")))
    producer.start()
    assert producer.latest_snapshot().status == "device_error"
    assert producer._settings.microphone_enabled is False
    assert producer.next_playback_chunk() is not None

    manual = AudioProducer(Settings().with_updates(microphone_enabled=False), clock=FakeClock())
    assert manual.next_playback_chunk() is not None


def test_worker_error_is_retained():
    producer = make_producer()
    producer._started = True
    producer._pending_frame = np.zeros(512)
    producer._pending_event.set()
    producer._process_frame = lambda _frame: (_ for _ in ()).throw(RuntimeError("fft failed"))
    thread = threading.Thread(target=producer._run)
    thread.start()
    thread.join(1.0)
    assert isinstance(producer.worker_error, RuntimeError)


def test_join_timeout_validation_and_non_daemon_cleanup():
    producer = make_producer()
    with pytest.raises(ValueError):
        producer.join(-1)
    with pytest.raises(ValueError):
        producer.join(float("inf"))
    with pytest.raises(ValueError):
        producer.join(True)

    holder = {}

    def factory(callback, sample_rate, channels, block_size):
        holder["stream"] = FakeStream(callback, sample_rate, channels, block_size)
        return holder["stream"]

    running = make_producer(stream=factory)
    running.start()
    assert running._thread is not None and running._thread.daemon is False
    running.stop()
    assert running.join(0.0) is True
    assert running._thread is None


@pytest.mark.parametrize("stop_error,close_error", [(RuntimeError("stop"), None), (None, RuntimeError("close"))])
def test_stream_stop_or_close_failure_is_retained_and_nonfatal(stop_error, close_error):
    holder = {}

    def factory(callback, sample_rate, channels, block_size):
        holder["stream"] = FakeStream(callback, sample_rate, channels, block_size, stop_error=stop_error, close_error=close_error)
        return holder["stream"]

    producer = make_producer(stream=factory)
    producer.start()
    producer.stop()
    assert producer.worker_error is not None
    assert producer.latest_snapshot().status == "device_error"
    assert producer._settings.microphone_enabled is False


def test_fake_mixer_adapter_records_ui_owned_calls():
    mixer = FakeMixer()
    chunk = make_producer(Settings().with_updates(microphone_enabled=False)).next_playback_chunk()
    assert chunk is not None
    mixer.initialize(48000, 1, 2)
    mixer.submit(chunk)
    mixer.stop()
    mixer.close()
    assert mixer.initialized == [(48000, 1, 2)]
    assert mixer.submitted == [chunk]
    assert mixer.stop_calls == mixer.close_calls == 1
