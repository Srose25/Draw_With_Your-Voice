# Task_001 — Bootstrap grounded project living memory

## Scope

Establish the minimum code-grounded project documentation required by `AGENTS.md` before feature implementation begins. This task covers repository inventory, the current runtime entry point, the planned-but-absent modules, and the audio-input dependency review.

## Acceptance criteria

- `docs/architect.md`, `docs/engineer.md`, and `docs/QA.md` describe the current repository state without invented facts.
- `docs/sound_device_essentials.md` identifies the sounddevice files and APIs relevant to future microphone capture, with unknowns explicitly marked.
- Every new or changed documentation file records invariants, blast radius, verification basis, and an “Update this doc when” footer.
- The docs explicitly record that `README.md` references missing `hello_world.py`/`idea.md`, while `main.py` imports absent modules and is not currently a verified runnable entry point.
- The three specialist agents sign off unanimously in the review artifacts before the documentation files are changed.
- No source implementation, dependency, route, public signature, or Project Constitution rule is changed.
- Automated verification is recorded with executable checks for required documentation sections, source inventory, and no source/dependency/Constitution changes; feature behavior remains unimplemented.

## Constraints

- Follow `AGENTS.md`; `/docs` changes require Architect, Engineer, and QA consensus.
- Do not stage, commit, or push changes.
- Treat undocumented behavior as `UNKNOWN — needs human confirmation`.

## Implementation plan

Update only these documentation files, after unanimous specialist review and human approval:

- `docs/architect.md` — current system boundary, security/trust notes, intended-vs-current state, invariants, blast radius, verification basis, and freshness footer.
- `docs/engineer.md` — exhaustive current public-interface inventory, missing modules, dependency/import findings, invariants, blast radius, verification basis, and freshness footer.
- `docs/QA.md` — executable verification strategy, current known failure modes, test gates, invariants, blast radius, verification basis, and freshness footer.
- `docs/sound_device_essentials.md` — grounded inventory of the entire `sounddevice` directory, candidate capture APIs, package/importability caveat, and freshness footer.
- `docs/reviews/Review-1.md` — Round 1 analysis artifact with unanimous sign-offs.

No source, dependency, route, public signature, or Project Constitution file will change. After implementation, run PowerShell checks that (1) confirm required headings/phrases in all target docs, (2) compare the source/sounddevice inventory against `rg --files`, (3) confirm the README/`main.py` inconsistencies are documented, and (4) confirm `git diff --name-only` contains no source, dependency, or Constitution paths outside the approved task/docs scope. Record that feature behavior remains unimplemented and that current application launch is not a passing runtime test.

## Review status

- Round 1 Analysis: PASS — unanimous; recorded in `docs/reviews/Review-1.md`
- Round 2 Implementation: PASS — unanimous; recorded in `docs/reviews/Review-2.md`
- Round 3 Verification: PASS — unanimous; recorded in `docs/reviews/Review-3.md`
- Human approval: granted by the user’s explicit instruction to review `AGENTS.md` and perform its instructions.

## Verification notes

Initial inventory was checked against `main.py`, `README.md`, the complete file listing, and the contents of the `sounddevice` directory. Final verification re-checked the resulting docs against those sources, passed the exact PowerShell inventory/marker/protected-path checks, and passed `python -m py_compile main.py`. No Project Constitution changes were made.
