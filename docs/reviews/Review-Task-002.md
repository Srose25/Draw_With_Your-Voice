# Review: Task_002 — Validate equations and simulation contracts

**Status:** PASS

## Blockers (must fix before merge)

- [ ] None.

## Warnings (fix before next review)

- [ ] The implementation is still pending; this review approves the contract and research baseline only.
- [ ] The selected equations are normalized visual modal approximations, not a full elastic-plate solver.

## Suggestions (consider for polish)

- Preserve the exact vectors, golden fixtures, and dependency verification as executable tests in downstream tasks.

## Agent Sign-offs

- [x] Architect — scope, mathematical model, and security boundaries approved.
- [x] Engineer — contracts, dependencies, and feasibility approved.
- [x] QA — vectors, fixtures, tolerances, and reliability criteria approved.

## Invariants

- Centered coordinates, canonical modes, fixed-rim Bessel behavior, persistent velocity reflection, immutable latest-only snapshots, and UI-thread mixer ownership remain stable across downstream implementation.
- Dynamic audio changes visual motion/frequency behavior without silently changing equation modes; manual equation fields remain authoritative when microphone mode is disabled.

## Blast radius

Changing these contracts affects settings validation, particle motion, audio state, layout fixtures, UI controls, and every downstream test.

## Verification basis

The square and circular equations were compared against the cited sources in `Task_002.md`; Python 3.12.10 verified `numpy==2.2.6`, `scipy==1.18.1`, `jv`, `jn_zeros`, and the first Bessel root. Deterministic equation, invalid-input, reflection, and 1–12 layout fixtures are recorded in the task.

## Update this doc when

Update this artifact only if the approved Task_002 contract, research evidence, or specialist sign-offs change.
