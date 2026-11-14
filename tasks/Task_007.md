# Task_007 — Final verification and product hardening

## Scope

Run automated and manual verification across simulation, UI, audio fallback, device failure, accessibility/usability, and clean shutdown. Update living-memory docs and final product history only after the implementation is stable.

## Acceptance criteria

- Full automated suite passes for settings, all 12 layouts, equations, particle lifecycle, audio fakes, UI controls, failure injection, and clean shutdown.
- Clean-install verification checks declared dependencies, imports, and launch instructions.
- Headless Pygame verification passes without display or microphone; hardware smoke testing is separately labeled and does not gate deterministic CI.
- Accessibility/usability checks pass for keyboard operation, visible labels, color-independent feedback, manual fallback, and help text.
- No worker, audio stream, window, or temporary resource remains after shutdown.
- Protected-path and Constitution safety checks pass; intended changes are documented with invariants, blast radius, verification basis, and freshness updates.
- `docs/final_product.md`, `README.md`, and task index are updated only after unanimous review.

## Invariants and blast radius

Feature completion requires deterministic automated coverage plus explicit hardware/manual limitations. Skipping either can ship a demo that passes locally but fails in CI or on a user device.

## Concrete final-gate contract pending owner approval

This section turns the Task_007 acceptance criteria into executable checks. It is a final-verification contract; it must not change feature behavior or previously approved contracts.

### Protected-path allowlist

Task_007 may change only `README.md`, `docs/final_product.md`, `tasks/index.md`, `tasks/Task_007.md`, `docs/reviews/Review-Task-007.md`, and the dedicated `tests/test_task007_verification.py` gate test. The safety check fails if `AGENTS.md`, the Project Constitution in `docs/project_plan.md`, prior task contracts, implementation modules, `requirements.txt`, or unrelated files change. Capture `git status --short --untracked-files=all` before and after verification, compare changed paths against this allowlist, and fail on every out-of-scope path.

### Clean-install and import gate

In a fresh Python 3.12 environment, run:

```powershell
$ErrorActionPreference = 'Stop'
try {
  py -3.12 -m venv .venv-clean
  if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
  .\.venv-clean\Scripts\python.exe -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
  .\.venv-clean\Scripts\python.exe -c "import pathlib, sys; repo=pathlib.Path.cwd().resolve(); sys.path=[p for p in sys.path if p not in ('', str(repo))]; import pygame, numpy, scipy, sounddevice; p=pathlib.Path(sounddevice.__file__).resolve(); vendored=repo/'sounddevice'; assert pygame.version.ver == '2.6.1'; assert numpy.__version__ == '2.2.6'; assert scipy.__version__ == '1.18.1'; assert sounddevice.__version__ == '0.5.6'; assert 'site-packages' in str(p); assert not p.is_relative_to(vendored); sys.path.insert(0, str(repo)); import main; assert pygame.get_init() is False"
  if ($LASTEXITCODE -ne 0) { throw "clean import assertions failed" }
} finally {
  if (Test-Path .venv-clean) { Remove-Item -Recurse -Force .venv-clean }
}
```

The check must confirm exact pins, external site-packages resolution for `sounddevice`, no resolution to the checked-in `sounddevice/` directory, and `pygame.get_init() is False` after importing `main`. The temporary `sys.path` isolation is required because the repository contains a checked-in `sounddevice/` source directory that would otherwise shadow the installed package during the assertion.

### Deterministic regression gate

Run `.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider -q` and record the exact count. The suite must cover all settings/equation vectors, all 1–12 layouts and alternate dimensions, particle reflection/lifecycle/error paths, audio FFT/latest-only/fallback/playback/lifecycle paths, all UI controls/focus/hitboxes/accessibility states, layout pause/commit/cancel, mixer ownership/failure, and ordered shutdown. The current baseline is 186 passing tests, including the four dedicated Task_007 gate tests.

### Headless launch and resource gate

Record `$previousSdl = $env:SDL_VIDEODRIVER`, then in a `try/finally` set `$env:SDL_VIDEODRIVER='dummy'`, run `.\.venv\Scripts\python.exe -m pytest -q tests/test_task007_verification.py -p no:cacheprovider`, check `$LASTEXITCODE` and throw on failure, and in `finally` restore `$previousSdl` or remove the variable when it was absent. The dedicated test constructs `Application` with fake audio/particle/mixer factories, a frame clock, and an event source returning one `QUIT` event. It asserts `run() == 0`; records an ordered call log proving `pygame.quit()` is last; asserts mixer stop/close, every audio and particle worker joined, repeated shutdown harmless, and no `audio-producer` or `particle-worker` remains in `threading.enumerate()`. Factory/start/stop/join/mixer failures must complete best-effort cleanup; no duplicate stream, raw audio array, queue/history, temporary resource, or network activity may remain.

### Manual smoke checklist (non-gating hardware evidence)

Run separately on the target Windows/Pygame environment and record each result as PASS, FAIL, or UNKNOWN:

- Install from `requirements.txt` and launch with `main.py`.
- Confirm the 800×600 window, header, microphone icon, labels, focus indicator, and visible hollow markers.
- Exercise all controls, six frequency presets, frequency/volume endpoints, particle counts 1–12, drawing, clear, both plate shapes, and manual equation fields.
- With MIC OFF, confirm audible sine playback and visual motion; with MIC ON, confirm playback stops and visual motion responds to input.
- Deny microphone permission or use no device; confirm visible fallback and continued manual operation.
- Confirm keyboard-only operation and readable non-color state labels.
- Close through the window close path and verify no traceback, stuck audio, or lingering process.

Hardware-dependent unknowns must remain explicitly labeled: permission UX/device selection across Windows hosts, PortAudio behavior on the demo machine, real output latency/clipping/quality, display contrast, and screen-reader semantics beyond visible labels and keyboard operation.

### Verification basis and freshness

The contract is grounded in `AGENTS.md`, the Project Constitution, completed Task_003–006 contracts/reviews, `requirements.txt`, `README.md`, `main.py`, and the current 186-test baseline. Update this task when a final-gate command, protected path, resource guarantee, manual checklist item, or unresolved hardware limitation changes.

## Final-gate corrections after execution

- The clean-install import assertion now isolates the external `sounddevice` package before restoring the repository path for `main`; this was required to verify the pinned installed dependency rather than the checked-in source directory.
- The deterministic regression baseline is 186 passing tests (182 pre-gate tests plus 4 Task_007 gate tests).
- The clean-install gate passed with Python 3.12, exact dependency pins, external `sounddevice`, and side-effect-free `main` import.
- Manual hardware smoke evidence remains `UNKNOWN`/non-gating in this environment.

## Verification

Run the full suite, clean-install/headless checks, manual checklist, and final three-agent review; record results and unresolved unknowns.

## Status

Complete. Owner-approved verification and hardening passed; deterministic manual-hardware unknowns remain explicitly labeled.
