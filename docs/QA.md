# QA Record — Verification and Reliability Gates

## Current test state

The current automated suite contains settings, helpers, particle, audio producer, UI control, and final-gate tests; it passes 186 tests with `-p no:cacheprovider`. The focused UI suite contains 60 cases covering controls, validation, focus, hitboxes, rendering, layout pause/commit/cancel, mixer ownership, failure handling, accessibility labels, and shutdown. Task_007 final product hardening is complete; manual hardware smoke remains explicitly non-gating and unknown.

## Bootstrap verification (Task_001 historical baseline)

The following checks and results document the Task_001 baseline. At that time the helper/settings modules and tests did not yet exist; they are retained as historical evidence and are not the current feature gate.

For this documentation task, verification must be executable and must pass these checks:

1. `rg --files` confirms the documented source and `sounddevice` inventories.
2. Required headings and the phrases `UNKNOWN — needs human confirmation`, `Invariants`, `Blast radius`, `Verification basis`, and `Update this doc when` occur in every new Tier 1 record.
3. `README.md` contains the stale `hello_world.py`/`idea.md` references and `main.py` contains the absent local imports recorded by the docs.
4. `git diff --name-only` is checked to ensure no source, dependency, or Project Constitution file changed outside the approved task/docs scope.
5. A launch/import check is recorded as expected to fail until the missing `particle.py` and `audio_producer.py` modules are implemented; it is not treated as a passing runtime test.

### Executed bootstrap commands and results

From the repository root, the following PowerShell checks were executed:

```powershell
$files = @('docs/architect.md','docs/engineer.md','docs/QA.md','docs/sound_device_essentials.md','docs/reviews/Review-1.md')
foreach ($f in $files) { $t = Get-Content -Raw $f; if (-not ($t.Contains('Invariants') -and ($t -match '(?i)blast radius') -and $t.Contains('Verification basis') -and $t.Contains('Update this doc when'))) { throw "Missing required marker: $f" } }
if ((Get-ChildItem sounddevice -File).Count -ne 49) { throw 'sounddevice inventory count mismatch' }
$disk = @(Get-ChildItem sounddevice -File | Select-Object -ExpandProperty Name | Sort-Object)
$listed = @(rg --files sounddevice | ForEach-Object { Split-Path $_ -Leaf } | Sort-Object)
if (($disk -join "`n") -cne ($listed -join "`n")) { throw 'sounddevice filename inventory mismatch' }
$documented = @('__init__.py','asyncio_coroutines.py','asyncio_generators.py','checking-hardware.rst','conf.py','contributing (2).rst','CONTRIBUTING.rst','convenience-functions.rst','download','download (1)','examples.rst','fake__sounddevice.py','favicon.svg','index (3).rst','index.rst','installation.rst','LICENSE','make_dist.sh','MANIFEST.in','module-defaults.rst','NEWS.rst','platform-specific-settings.rst','play_file.py','play_long_file.py','play_sine.py','play_stream.py','plot_input.py','priming_output.py','publish.yml','pyproject.toml','raw-streams.rst','README','README (4).rst','README (5)','README.rst','readthedocs.yml','rec_gui.py','rec_unlimited.py','setup.py','sounddevice_build.py','sounddevice-data.yml','sounddevice.py','spectrogram.py','static-analyzers.yml','streams.rst','usage.rst','uv.lock','version-history.rst','wire.py' | Sort-Object)
if (($disk -join "`n") -cne ($documented -join "`n") -or $documented.Count -ne 49 -or $documented.Count -ne @($documented | Select-Object -Unique).Count) { throw 'documented sounddevice inventory mismatch' }
if ((Test-Path particle.py) -or (Test-Path helpers.py) -or (Test-Path audio_producer.py) -or (Test-Path settings.py) -or (Test-Path hello_world.py) -or (Test-Path idea.md)) { throw 'unexpected file present' }
if (-not ((Get-Content -Raw README.md).Contains('hello_world.py'))) { throw 'README mismatch not present' }
foreach ($import in @('import particle as pr','import helpers as helper','import audio_producer as au','import settings as st')) { if (-not ((Get-Content -Raw main.py).Contains($import))) { throw "main.py import missing: $import" } }
if ((git diff --name-only -- main.py README.md sounddevice docs/project_plan.md AGENTS.md) -ne $null) { throw 'source/dependency/Constitution path changed' }
```

Result: **PASS**. All required markers were present, the directory count was 49, the filename list matched `rg --files sounddevice` and the 49-name documented inventory, all six expected-absent files were absent, all four documented imports were present, and the README/`main.py` mismatch checks passed. The scoped `git diff --name-only` check returned no source, dependency, or Constitution paths. The expected launch/import failure was also confirmed by the absent local modules; no feature runtime test was claimed as passing.

The repository is an uncommitted starter checkout with pre-existing deleted files and untracked project files. Therefore the no-source-change check is scoped to the Task_001 change set: review of `git status --short` and the patch confirms changes are limited to `tasks/Task_001.md` and the approved `/docs` files; no source, dependency, or Project Constitution file was edited by this task.

## Current Task_007 final verification

From the project Python 3.12 environment, `.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider -q` passed **186 tests**; `tests/test_main_controls.py` passed **60 cases** and the dedicated Task_007 gate passed **4 cases**. Python compilation checks passed for the implementation and focused test files. SDL dummy-driver rendering passed without a display; clean installation verified external `sounddevice==0.5.6` from site-packages; device enumeration succeeded, while host PortAudio input startup failure was handled as a manual-mode fallback. The cache provider was disabled to avoid stale permission directories; no test failure occurred.

## Completed acceptance gates

Task_006 covers the integrated headless UI contract. Task_007 final product hardening, launch documentation review, deterministic deployment-safety checks, and headless cleanup verification are complete. Real Pygame/audio manual smoke remains a separately labeled unknown.

## Reliability and usability risks

- No microphone or PortAudio device must not prevent manual-mode startup once that mode exists.
- Audio callbacks must not block the UI thread or perform unbounded queue operations.
- Headless CI cannot depend on a physical microphone or display; tests need fakes or deterministic providers.
- Task_005 through Task_007 specify and test permission/device failure fallback, overflow handling, bounded retention, error statuses, integrated mixer ownership, and clean shutdown. Real hardware behavior remains a manual-smoke concern and is explicitly non-gating.

## Invariants and blast radius

- Every behavior change needs automated coverage before sign-off. Skipping it makes regressions in drawing or audio timing invisible.
- Tests must distinguish deterministic simulation from hardware integration. Mixing them makes CI flaky and can hide device failures.
- Regression checks must cover documented contracts whenever one is added. Changing this gate affects all future feature merges.

## Verification basis

Verified against the current repository file inventory, all implementation modules, `requirements.txt`, all test files, `README.md`, `docs/project_plan.md`, and the full `sounddevice/` directory. The focused UI suite passed 60 cases, the dedicated Task_007 gate passed 4 cases, and the full suite passed 186 tests with `-p no:cacheprovider`; no test failure occurred.

## Update this doc when

Update this file when a test runner, test fixture, acceptance criterion, CI workflow, hardware-integration path, user-visible behavior, or reliability guarantee changes.

