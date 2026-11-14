# Review: Task_004 — Implement threaded particle simulation

**Status:** PASS

## Blockers (must fix before merge)

- [ ] None.

## Warnings (fix before next review)

- [ ] `AudioSnapshot` runtime ownership remains in Task 005; Task 004 uses the approved structural protocol boundary.
- [ ] Pygame UI integration and microphone producer behavior remain unimplemented.

## Suggestions (consider for polish)

- Preserve the no-Pygame worker boundary and fake-clock tests during integration.

## Agent Sign-offs

- [x] Architect — particle scope, mapping, concurrency, and safety approved.
- [x] Engineer — implementation and lifecycle contracts approved.
- [x] QA — concurrency, failure, and deterministic verification approved.

## Invariants

- Particle state is lock-protected and snapshots are immutable; worker threads never call Pygame.
- Motion uses persistent velocity, volume-only gain, explicit equation selection, deterministic reflected boundaries, and last-valid fallback.
- Worker shutdown is bounded and observable; first worker errors remain retrievable.

## Blast radius

Changing particle state, mapping, motion, audio precedence, or worker lifecycle affects equations, settings, rendering, audio integration, and application shutdown.

## Verification basis

The full test suite passed 92 tests with `-p no:cacheprovider`; compilation checks passed. The implementation was reviewed against Task_002, Task_003, and the project plan by all three specialists.

## Update this doc when

Update this artifact when Task_004 behavior, lifecycle guarantees, verification evidence, or specialist sign-offs change.
