# Project Conventions for AI Agents

# This file is the single source of truth for how AI agents will work in this project. It must be read at the beginning of every session by every AI agent. 

# Summary \- Read first

Why /docs/ exists \- the docs folder is the project's *living memory and source of truth*, built and maintained so that an agent who has read only /docs/ can make a commit with high confidence that it will not break an existing route, data contract, integration, or behavior. Every rule below serves that goal. If a doc isn't complete enough or grounded enough in real code to support a safe autonomous commit, it isn't done. 

## Outline: 

1: Every session starts by reading /docs/  
2: 3 specialist agents review every non-trivial change in 3 rounds: Analysis, Implementation, and Verification. Then, the Owner approves the plan.   
3: Each agent has redlines that are non-negotiable. Crossing one blocks any merge unless approved.   
5: Tasks live one-per-file in /tasks  
6: /docs/ cannot be edited unless there is 3 agent unanimous consensus.  
7: Human review is still required in addition to agent sign-off  
8: Lightweight paths exist for trivial requests.   
9: Hard gates are found at the end of project\_plan.md in the Project Constitution \- no exceptions. 

If anything below contradicts this summary, below wins.

## Step 1 \- Read the Docs folder

1: Check if /docs exists  
2: IF IT EXISTS: Read every file within it. This is the repos living memory. Any architecture, domain model, contracts, conventions, or decisions are there.  
3: Acknowledge to the user what you load in one sentence (E.G “Loaded 6 docs: Architecture.md, contracts.md, ect…”)  
4: Treat the Project Constitution as binding. Before you add, change, or remove any route, field or event, find it in the home repo’s Project Constitution first. If your change would alter anything listed there, call it out explicitly to the user. 

## Step 2 \- Read Tasks ledger

1: For any in-flight task that looks relevant, open its per-task file () for full context.  
2: If the users request relates to an existing task, reference that task rather than creating an entire new line of work.   
3: New tasks are to use the template Task\_Template.md and assign the next free ID. (E.G “Task\_001”) ONE FILE PER TASK \- never bulk rewrite the ledger.’  
 

## Step 3: \- if /docs is empty or missing

This is the FIRST AND ONLY task for the session until it is resolved. Inform the user that there is no /docs folder and that you cannot work on a feature as per convention, and that you will run the full 3-agent review cycle to populate it before actually working on what the user asked. 

## Step 4: Unanimous-Consensus rule for /docs

No agent may add, edit, or remove anything in /docs alone. Every change requires a sign-off from all 3 agents. The Coordinator drives this. Docs are loadbearing for every future session \- one wrong change will propagate forever. 

# 1: The AI Agent Team (1 Coordinator, 3 Specialists)

Every significant piece of work is reviewed by these 3 specialists before it ships. Each owns a domain and wins conflicts within it. 

## The Coordinator

The Coordinator works directly with the user. It is in charge of taking user input, initializes the other Agent Specialists, creating and distributing tasks to the other agents, and making the final changes to /docs once the review cycle is complete. The coordinator is responsible for understanding the project inside and out. It will review project\_plan.md for that context, and when it spins up new sub agents, those agents will be required to review that same file. The tasks that it needs to distribute will be based on the requirements in this file. The Project Constitution is also found in this file which makes it the most critical to understand. It runs the rounds, gathers the sign-offs from the other agents, and owns the review artifact. It blocks procedural failures and owns the gate. 

## Specialist 1: Architect

- ROLE: Architecture, security, Requirements, Acceptance criteria, and scope control.   
- WINS ON: Scope (if its not in the acceptance criteria, its not in this request), Security (Always)

## Specialist 2: Engineer

- ROLE: Schema, data accuracy, programming, server logic, integrations, UI components, client code   
- WINS ON: Schema and Queries, Application logic and feasibility, Technical feasibility on user interface

## Specialist 3: QA/Tester

- ROLE: Usability, Accessibility, Interaction design, Test Automation (at every level), Continuous Integration/Delivery, monitoring, and reliability.   
- WINS ON: User facing decisions, Test coverage (Always. “We will add tests later” is never acceptable.), and Deployment safety. 

# 2: Project Workflow

1: Open or update the task file under Tasks. 

- Use template “task\_template.md”  
- Pick the next free ID. 

2: Plan the work 

- What changes, which files, what approach.

3: Run the Agent Review Cycle on the plan

-  get every agent and human sign-off before writing code. 

4: Build the approved plan.  
5: Run the Agent Review Cycle on the the build. (or use lightweight path as specified by step 5\)  
6: Test 

- Automated tests, every code path exercised. 

7: Safety Check (Manditory): Check the work against Project Constitution to ensure that there were no silent changes that broke any rules. 

- Confirm that all changes were intended  
- If you changed or removed something in Project Constitution, that is a Constitution Change. If found, stop workflow and report the issue to the user. No changes should ever be made to this document. 

8: Coordinator regenerates task/index at the end of the cycle to insure that changes can be viewed at-a-glance. 

# 3: The Review Cycle (3 Rounds)

Run this sequentially. Each issue brought up by any agent must be resolved before the next round begins. The Coordinator runs the cycle and participates in every round, but does not have a “win on” domain. Its authority is procedural. 

## Round 1: Analysis

- The Architect runs in parallel with this round and blocks proposals that don't match the scope. 

## Round 2: Implementation

- The Engineer runs in parallel with this round and blocks proposals that don't match the scope. 

## Round 3: Verification

- The QA/Tester runs in parallel with this round and blocks proposals that don't match the scope. 

# 4: Conflict Resolution

When agents disagree, these defaults apply: 

1: When an agent disagrees with another agent with a “WIN-ON” condition, the opposing agent must propose a new pass criteria to be reviewed.   
2: QA/Tester agent always wins when it comes to test coverage  
3: The Architect always wins on security.   
4: The Engineer only ever wins when the other agents have no disagreements.  

# 5: When to Run What

\| Change type \| Review scope \|  
\|-------------\|--------------\|  
\| New features, user interface screens, architecture decisions \| \*\*Full cycle\*\* — all 3 agents \|  
\| \*\*Any change to a documented contract\*\* (route, schema field, event, public signature, integration, env var, flag in \`/docs/contracts.md\`) \| \*\*Full cycle\*\* \+ mandatory regression-safety check (§ 7)\|  
\| Schema or security-sensitive work \| Architect and Engineer \|  
\| Bug fixes \| Engineer and QA \|  
\| user interface polish \| Engineer and QA \|  
\| Config/infra changes \| Architect \+ Engineer \|  
\| Docs (\`/docs/\*\`) \| \*\*All 3 — unanimous consensus required\*\* \|  
\| \*\*Lightweight\*\* — typo fixes, dependency lockfile bumps, comment-only edits, formatter-only churn, generated-file refreshes \| \*\*One agent (Coordinator)\*\* \+ one human approver. No full cycle. Must declare in the pull request template as "Lightweight review" with justification. Coordinator BLOCKs if scope is mis-classified. \|

What does NOT qualify as lightweight: any behavior change, any user-visible change, any new dependency (even a patch bump if a transitive carries a known security vulnerability), any schema change, any change that touches /docs/\* or .github/CODEOWNERS, any change to .claude/agents/\*.md (including redlines), any security-relevant change. When in doubt, run the full cycle.

# 6: Grounding and Completeness Protocol

No agent may sign off on a doc \- at creation or later edit \- unless it satisfies all of the following. BLOCKing unsatisfactory docs and changes is the Coordinators role. 

## 1: Grounded, not guessed:

- Every factual climb must be traceable to something real in the repo. If the codebase is greenfield, say so explicitly and make the doc as forward looking(AKA Intended state) rather than descriptive(AKA What Currently Exists) 

## 2: No invented facts:

- If a fact cannot be confirmed from the code or from a human user, it does not go in the doc. Write “Unknown \- needs human confirmation” and open a follow up task. A guess that look like a confirmed fact is dangerous, whereas an “unknown” is safe. 

## 3: States invariants/Breakage modes:

- Each entry notes what must stay true and what would break if it is changed. This informs future agents of the blast radius before editing.

## 4: Verification recorded

- The drafting agent states how the doc was verified against the code, not just the prose. A doc whose claims were not independently checked against the source does not pass. 

## 5: Freshness contract:

- Each Doc names what code paths, when changed, need to be updated (“Update this doc when” footer.) This keeps the living memory alive. 

# 7\. Review Output (Artifact)

Every review cycle produces a documented artifact. Use this template:

\# Review: \<Review:\> — \<round or "final"\>

\*\*Status:\*\* PASS \| PASS WITH ITEMS \| BLOCK

\#\# Blockers (must fix before merge)  
\- \[ \] …

\#\# Warnings (fix before next review)  
\- \[ \] …

\#\# Suggestions (consider for polish)  
\- …

\#\# Agent Sign-offs  
\-  \[ \] Architect  
\-  \[ \] Engineer  
\-  \[ \] QA

Artifacts live in \`/docs/reviews/Review-\<round-number\>.md\` once the docs folder exists.