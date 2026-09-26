---
title: 'Human-gated escalation'
type: 'feature'
created: '2026-09-26'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'a4f810dac4c43065b0ed32919a0a3c4ec1bc178f'
context:
  - _bmad-output/specs/spec-epic-2/SPEC.md
  - TRIAGE_POLICY.md
  - agent.py
  - run_agent.py
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The story 1 agent applies the triage policy but never escalates, so a P1 ticket for an Enterprise customer is decided silently even though the policy requires a person's approval before escalation.

**Approach:** Add a local `escalate_to_human` tool the agent can call, gated end-to-end by LangChain's `HumanInTheLoopMiddleware` so every call pauses the run. Extend `run_agent.py` to resume an interrupted run with a terminal yes/no prompt: "yes" completes the run as escalated, "no" completes it without escalating. No run escalates without an explicit "yes".

## Boundaries & Constraints

**Always:** Keep story 1's provider selection, MCP-only lookup tools, policy prompt, and structured-output retry unchanged; add `escalate_to_human` as a local tool (not in `mcp/triage_server.py`, which stays read-only); gate it with `HumanInTheLoopMiddleware` and a checkpointer so the agent graph can pause and resume; preserve `run_agent.py`'s MLflow tracking setup, `<ticket_id>` invocation contract, and printed JSON decision.

**Never:** Modify `TRIAGE_POLICY.md`, seed data, `mcp/triage_server.py`, or the Epic 1 schema; let the agent escalate without an explicit terminal "yes"; add escalation logic inside the MCP server; change story 1's non-escalating behavior for tickets that do not meet the P1+Enterprise rule.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|-----------------------------|----------------|
| P1 + Enterprise, approved | Ticket resolves to P1 for an Enterprise customer; terminal answers "yes" | Run pauses for approval, then completes with the decision recorded as escalated | N/A |
| P1 + Enterprise, declined | Same setup; terminal answers "no" | Run pauses for approval, then completes with the same decision, not escalated | N/A |
| Not P1+Enterprise | Any ticket that does not meet the escalation rule | Run completes with no pause and no `escalate_to_human` call | N/A |
| Ambiguous terminal answer | Approval prompt receives blank input or an unrecognized answer | Treated as a decline (no escalation) | Never silently treated as approval |
| Test without a terminal | Automated tests must not block on real terminal input | An injectable approval callback resolves the pause deterministically | N/A |

</frozen-after-approval>

## Code Map

- `agent.py` -- story 1's `build_agent`/`triage`; add `escalate_to_human` tool, `HumanInTheLoopMiddleware` in `interrupt_on`, a checkpointer (e.g. `InMemorySaver`), and resume handling in `triage` for the interrupted state.
- `run_agent.py` -- existing CLI stub; add the terminal yes/no prompt function and pass it into `triage` so the CLI, not the agent module, owns the interactive I/O.
- `TRIAGE_POLICY.md` -- read-only; already states the P1+Enterprise escalation rule and that nothing escalates without approval.
- `upstream/stage-3:agent.py` -- historical reference for `HumanInTheLoopMiddleware`, `ask_at_terminal`, `Command(resume=...)`, and the `__interrupt__` loop in `triage`; reuse the resume-loop shape, adapted to story 1's current `agent.py`.
- `tests/test_agent.py` -- story 1's scripted-model tests; add escalation tests using an injectable approve/decline callback, no real terminal input.

## Tasks & Acceptance

**Execution:**
- [x] `agent.py` -- add `escalate_to_human(ticket_id, reason)` tool, wire `HumanInTheLoopMiddleware` with `interrupt_on={"escalate_to_human": {"allowed_decisions": ["approve", "reject"]}}`, add a checkpointer, and extend `triage` to accept an `approve` callback and resume the graph via `Command(resume=...)` until no interrupt remains.
- [x] `run_agent.py` -- add a terminal prompt function that asks yes/no and defaults unrecognized or non-interactive input to no; pass it as the `approve` callback into `triage`.
- [x] `tests/test_agent.py` -- test that a P1+Enterprise ticket pauses and calls the approval callback with the escalation reason; that "approve" completes as escalated and "reject" completes without escalating; that a non-P1+Enterprise ticket never calls `escalate_to_human` or the approval callback; that no escalation occurs without an explicit approve decision.

**Acceptance Criteria:**
- Given a ticket that resolves to P1 for an Enterprise customer, when `triage` runs with an approving callback, then `escalate_to_human` is called once and the run completes as escalated.
- Given the same setup with a declining callback, when `triage` runs, then the run pauses once and completes without escalation, still returning a valid decision.
- Given a ticket that does not meet the P1+Enterprise rule, when `triage` runs, then no pause occurs and the approval callback is never invoked.
- Given `run_agent.py` reaches an escalation pause, when the terminal receives blank or unrecognized input, then the run completes without escalating.
- Given the existing story 1 behavior (provider switch, tool order, retry, injection resistance), when this story's changes are applied, then all story 1 tests continue to pass unmodified in behavior.

## Implementation Notes

 - Added `escalate_to_human` tool, `HumanInTheLoopMiddleware`, and an `InMemorySaver` checkpointer to `build_agent`; extended `triage` with an `approve` callback and a `Command(resume=...)` loop over `state["__interrupt__"]`.
 - A story-1 error-scanning loop in `triage` was too broad: it treated a HITL-rejected `escalate_to_human` ToolMessage (status `"error"`) as a fatal error, breaking the decline path. Fixed by skipping only messages named `escalate_to_human` in that check, since preflight already covers the original unknown-ticket failure mode this loop was written for.
 - `run_agent.py`'s `ask_at_terminal` now catches `EOFError` (non-interactive stdin) and treats it as a decline, alongside blank/unrecognized input.
 - Verification: 17 tests in `tests/test_agent.py` (story 1 + story 2) pass, 4 in `tests/test_run_agent.py`, 26 across the Epic 1 prerequisite suites -- 47 total, no regressions.
 - Mutation-tested the approve/reject mapping in `triage()` by inverting it and confirming `test_approving_actually_calls_the_real_escalation_tool` / `test_declining_never_calls_the_real_escalation_tool` fail, then reverted.

## Review Triage Log

- high (verification gap) -- `test_escalation_pauses_and_waits_for_approval`/`test_declined_escalation_still_returns_a_decision` used a scripted model that ignores conversation content, so an inverted approve/reject mapping in `triage()` would still pass all tests -- patched by adding `test_approving_actually_calls_the_real_escalation_tool` and `test_declining_never_calls_the_real_escalation_tool`, which spy on the real `escalate_to_human` tool through the public API and were confirmed (via mutation) to catch an inverted mapping.
- medium -- `run_agent.py`'s `ask_at_terminal` called `input()` with no guard for non-interactive stdin (`EOFError`) -- patched to catch `EOFError` and decline, with a covering test.
- low, accepted -- the broad `status=="error"` skip for any message named `escalate_to_human` would also swallow a genuine failure if that tool is ever extended beyond its current string-return behavior; the tool cannot fail today, so no fix applied. Revisit if `escalate_to_human` gains real failure modes.
- false -- "escalation outcome isn't recorded in the returned decision (no `escalated` field)": the Epic 1 `TriageDecision` schema is frozen and out of this story's boundary, and the historical `upstream/stage-3` reference this story was told to follow returns the identical decision regardless of approve/reject -- escalation status is observed via the MLflow trace and tool execution, not the returned dict, by design.
- false / out of scope -- "checkpointer is request-scoped, no cross-process resume": the story's I/O matrix defines resume within one `run_agent.py` invocation only; cross-process durability is not part of CAP-5's accepted scope.
- false (unreachable given architecture) -- "`state["__interrupt__"][0]` only reads index 0, dropping later entries": `create_agent`'s single-threaded graph produces at most one interrupt entry per pause, whose `action_requests` list already holds every pending request from that pause; a fix here would add unused complexity for an unreachable state.
- medium, deferred -- code-level enforcement that `escalate_to_human` is actually called when the P1+Enterprise rule fires (rather than relying on prompt compliance) would duplicate the model policy layer, matching the same design boundary already deferred for story 1; settle with credentialed end-to-end/eval coverage.
- low, deferred -- no bound on the model re-attempting `escalate_to_human` after a decline (unbounded `while` loop); the historical `upstream/stage-3` reference this story reuses has the same unbounded loop and the spec's I/O matrix does not ask for a retry cap.

## Design Notes

The historical `upstream/stage-3:agent.py` already implements this exact shape (`ask_at_terminal`, `HumanInTheLoopMiddleware`, `Command(resume=...)` loop) but bundled with story 1 concerns already built in the current `agent.py`; adapt only the escalation-specific pieces onto the existing implementation rather than reintroducing already-built code.

## Verification

**Commands:**
- `uv run pytest tests/test_agent.py` -- expected: all story 1 and story 2 focused agent tests pass without API keys or real terminal input.
- `uv run pytest` -- expected: all repository tests pass.
- `uv run python run_agent.py T-1044` -- expected (credentialed): pauses for a yes/no prompt for a P1+Enterprise ticket; answering yes completes as escalated.
