"""Deterministic audio and mixer fakes for Task_005 tests."""

from __future__ import annotations


class FakeStream:
    def __init__(self, callback, *_args, start_error=None, stop_error=None, close_error=None, **_kwargs):
        self.callback = callback
        self.start_error = start_error
        self.stop_error = stop_error
        self.close_error = close_error
        self.started = False
        self.closed = False
        self.start_calls = 0
        self.stop_calls = 0
        self.close_calls = 0

    def start(self):
        self.start_calls += 1
        if self.start_error:
            raise self.start_error
        self.started = True

    def stop(self):
        self.stop_calls += 1
        if self.stop_error:
            raise self.stop_error
        self.started = False

    def close(self):
        self.close_calls += 1
        if self.close_error:
            raise self.close_error
        self.closed = True

    def emit(self, frame, status=None):
        self.callback(frame, getattr(frame, "shape", [len(frame)])[0], None, status)


class FakeMixer:
    def __init__(self, *, initialize_error=None, submit_error=None):
        self.initialize_error = initialize_error
        self.submit_error = submit_error
        self.initialized = []
        self.submitted = []
        self.stop_calls = 0
        self.close_calls = 0

    def initialize(self, sample_rate, channels, sample_width):
        if self.initialize_error:
            raise self.initialize_error
        self.initialized.append((sample_rate, channels, sample_width))

    def submit(self, chunk):
        if self.submit_error:
            raise self.submit_error
        self.submitted.append(chunk)

    def stop(self):
        self.stop_calls += 1

    def close(self):
        self.close_calls += 1
