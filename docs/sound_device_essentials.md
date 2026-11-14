# Sounddevice Essentials — Repository Review

## Scope and provenance

Every file under the checked-in `sounddevice/` directory was inventoried for Task_001. The directory contains 49 files: Python examples/scripts (`__init__.py`, `asyncio_coroutines.py`, `asyncio_generators.py`, `fake__sounddevice.py`, `play_file.py`, `play_long_file.py`, `play_sine.py`, `play_stream.py`, `plot_input.py`, `priming_output.py`, `rec_gui.py`, `rec_unlimited.py`, `setup.py`, `sounddevice_build.py`, `spectrogram.py`, `wire.py`), reStructuredText documentation (`checking-hardware.rst`, `convenience-functions.rst`, `CONTRIBUTING.rst`, `contributing (2).rst`, `examples.rst`, `index.rst`, `index (3).rst`, `installation.rst`, `module-defaults.rst`, `platform-specific-settings.rst`, `raw-streams.rst`, `streams.rst`, `usage.rst`, `version-history.rst`), metadata/configuration (`MANIFEST.in`, `NEWS.rst`, `pyproject.toml`, `readthedocs.yml`, `sounddevice-data.yml`, `static-analyzers.yml`, `uv.lock`, `conf.py`, `publish.yml`), and other files (`LICENSE`, `README`, `README.rst`, `README (4).rst`, `README (5)`, `download`, `download (1)`, `favicon.svg`, `make_dist.sh`, `sounddevice.py`).

The checked-in directory remains an inventory of examples/documentation and is not the runtime package. The project uses external `sounddevice==0.5.6`, verified from site-packages with `InputStream` and device enumeration, plus pinned NumPy/SciPy dependencies. Host PortAudio input-start failure is handled by the application’s manual fallback.

## Candidate microphone-capture essentials

The examples show the following upstream patterns that may inform a future implementation:

- `sd.InputStream(callback=..., channels=..., device=..., samplerate=..., blocksize=...)` for callback-based input.
- `sd.RawInputStream` for raw buffers.
- Callback parameters named `indata`, `frames`/`frame_count`, `time`/`time_info`, and `status`.
- `sd.query_devices()` and `sd.query_hostapis()` for device discovery.
- `sd.check_input_settings()` is referenced by the documentation inventory and should be verified against the installed package before use.
- `plot_input.py` and `README (5)` demonstrate NumPy-backed input processing; the project now pins NumPy and SciPy in `requirements.txt`.
- `rec_gui.py` demonstrates copying callback data before placing it on a queue and tracking input overflow; this is a candidate concurrency pattern, not an approved project implementation.

## Required future safeguards

The callback must not block on GUI or filesystem work, and audio data must be copied or transferred through a bounded/thread-safe handoff before FFT processing. Device absence, PortAudio errors, overflow/underflow, permission behavior, sample rate, channel count, block size, and retention policy require explicit decisions and tests before integration.

## Invariants and blast radius

- The directory’s examples must remain distinct from the installed dependency. Treating them as the package can break imports at startup.
- Candidate APIs must be verified against the actual chosen dependency version before coding. API drift can break microphone startup and callback signatures.
- Audio callbacks must remain lightweight and non-blocking. Violating this can cause dropouts or freeze the drawing loop.

## Verification basis

The file list was obtained from the repository, and the Python/RST/config contents were inspected for import paths, stream classes, callbacks, device queries, and dependency metadata. The external sounddevice installation and version were verified separately for Task_005; Task_006 verified the UI’s failure-tolerant integration boundary.

## Update this doc when

Update this file when the vendored audio directory changes, the selected sounddevice/PortAudio/NumPy versions are verified, microphone APIs are integrated, or callback/threading/error-handling behavior is decided.

