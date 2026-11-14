# `/docs` — Project Living Memory

This folder is the project's **living memory and source of truth**. Every AI agent is required by `AGENTS.md` to read every file here at the start of every session before doing any work.

## The bar this folder must meet

The test for whether `/docs/` is good enough is a single sentence:

> **An agent who has read only `/docs/` should be able to make a commit with high confidence that it will not break an existing route, data contract, integration, or behavior.**

That is a much higher bar than "documentation that describes the project." It means the docs must be **complete enough** to enumerate everything an autonomous change could break, and **accurate enough** that nothing in them is a plausible-sounding guess. Both are enforced by the **Grounding & Completeness Protocol** in `AGENTS.md` § 6.0 — read it before drafting or reviewing any doc.

## Why this folder matters

Without it, every session starts cold. The agents re-derive architecture from grep, re-discover conventions by trial and error, re-invent the wheel each time, and — worst — invent **wrong** facts that look plausible. A confident agent acting on a wrong fact ships a confident, wrong commit. This folder prevents that — but only if it is grounded in real code and kept current with it.

## The Grounding & Completeness Protocol (summary)

Full version in `AGENTS.md` § 6.0. No agent may sign off on a doc unless it is:

- **Grounded, not guessed** — every claim traceable to a real file / route / schema / config / workflow; cite paths where practical.
- **Free of invented facts** — anything unconfirmed is written `UNKNOWN — needs human confirmation`, never as if settled.
- **Exhaustive where it's a contract** — routes, schemas, events, public signatures, env vars, flags, integrations are listed in full, not sampled. No "etc." in a contract inventory.
- **Explicit about invariants & blast radius** — each contract notes what must stay true and what depends on it.
- **Verified** — the drafting agent records how it checked the doc against the code; reviewers re-check against the source, not just the prose.
- **Self-dating** — each doc names the code paths that, when changed, require it to be updated.

Greenfield repo with little code yet? Mark the doc **forward-looking** (intended state) rather than **descriptive** (what exists). Never blur the two.

## Hard rule — unanimous consensus

**No file in this folder may be added, edited, or removed without sign-off from all 3 agents** defined in `AGENTS.md`. The Coordinator drives this process. One wrong fact here propagates into every future session, so the bar is deliberately high.

If a single agent BLOCKs a `/docs/*` change, the change does not land.

## What goes here

If `/docs/` is empty (which it is in this starter), the **first task of the first session** is to follow the coordinator instructions found in AGENTS.md

Recommended files — rename or omit anything that doesn't apply to your stack:

### Tier 1 — required before any feature work begins

Tier 1 includes the **contract-critical docs** (`contracts.md`, `api.md`, `data-model.md`) on purpose: the moment feature work begins, an agent must already have the full inventory of what it could break.

| File | Owner (lead author) | Purpose |
|------|---------------------|---------|
| architect.md | The Architect Agent |  System overview, services, data flow, trust boundaries, and security |
| engineer.md  | The Engineer Agent | **The exhaustive, code-grounded inventory** of every route/endpoint, request/response contract, event/message schema, public interface/signature. This is ultimately where all of the project decisions converge and is the most important document to get accurate. |
| QA.md        | The QA Agent | Test strategy, levels, coverage gates, test-data approach, and the **regression-safety check** an agent runs to prove a change didn't break a documented contract. |

### Tier 2 — required by end of the first feature sprint

| File | Owner (lead author) | Purpose |
|------|---------------------|---------|
|final_product.md | Coordinator | This is the end all be all for the project's history. As soon as the agents are finished with the full build of the project, the coordinator will update this file with the design choices that were made for the successful implementation of this project.

> **Tier 1 vs. Tier 2 is a discipline tool, not a license to skip.** Both tiers carry the unanimous 3-agent consensus rule. Tier 2 missing past the first sprint is a process failure that should be retrospected.

## How to use this folder during a session

**You are an agent.** At session start:

1. List every file under `/docs/`.
2. Read every file (or, for very large repos, at least the files relevant to the user's request — but ALWAYS read `architect.md`, `engineer.md`, `QA.md`, and `project_plan.md`').
3. Acknowledge to the user what you loaded — one line: *"Loaded N docs: architecture.md, contracts.md, domain.md, …"*
4. Proceed with the user's request, applying what you learned.

**You are a human reviewing a pull request.** Check that any `/docs/*` change has the review artifact attached and 3-of-3 sign-offs. If not, comment "blocked: needs unanimous consensus per AGENTS.md".

## Anti-patterns

- ❌ Editing a doc to match a code change without running the review cycle.
- ❌ Adding a "draft" doc that no one's signed off on — drafts live on a branch, not in `/docs/`.
- ❌ Leaving unreplaced `[insert … here]` placeholders. Either fill them in, remove the line, or open an Architectural Decision Record explaining why it's still undecided.
- ❌ Writing prescriptive style/lint rules here — those belong in tooling configs, not in living memory.
- ❌ **Inventing a fact because it sounds right.** If it isn't confirmed by the code or the human, it's `UNKNOWN`, not a sentence that reads as settled. A plausible guess in living memory is a landmine.
- ❌ **Letting /docs/ drift behind the code.** A change to a documented contract and its doc update are one atomic pull request, never "I'll update the docs later."