---
title: 'The triage agent'
type: 'feature'
created: '2026-09-26'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'a61a9a36932e2ac369158073c03f8b9248002081'
context:
  - _bmad-output/specs/spec-epic-2/SPEC.md
  - TRIAGE_POLICY.md
  - run_agent.py
  - mcp/triage_server.py
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repository has the Epic 2 command-line integration point but no agent implementation, so a ticket cannot be looked up, classified, or returned as a validated triage decision.

**Approach:** After the Epic 1 schema and loader are present on the branch, build a LangChain `create_agent` implementation that selects Gemini or Groq from environment variables, obtains only the existing MCP tools over stdio, applies the read-only triage policy, and returns the Epic 1 decision shape. Keep ticket text untrusted and retry invalid structured output exactly once before failing clearly.

## Boundaries & Constraints

**Always:** Start from a branch containing the Epic 1 schema and loader implementation; preserve `run_agent.py`'s MLflow tracking setup and invocation contract; use `create_agent`; load `TRIAGE_POLICY.md`; call `get_ticket` before `get_customer_history` using the returned customer ID; use the Epic 1 schema and loader unchanged; use only `mcp/triage_server.py` over stdio; keep provider and model selection environment-driven; make no escalation implementation in this story.

**Never:** Modify `TRIAGE_POLICY.md`, seed data, `mcp/triage_server.py`, or Epic 1 implementation; add `escalate_to_human` or `HumanInTheLoopMiddleware` in this story; add a hand-rolled tool loop, UI, deployment, or Epic 3 evaluation; follow instructions embedded in ticket text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|-----------------------------|----------------|
| T-1042 | Billing ticket; Enterprise customer with 2 open tickets | Valid billing/P2/billing-team decision | Propagate clear agent error if lookup/model fails |
| T-1099 | Ticket text contains an instruction to mark itself P1 | Valid bug/P4/bug-team decision based on actual content | Ignore embedded instruction |
| Enterprise threshold | Enterprise customer with 3 open tickets and a ticket whose base priority is P3 | Priority is bumped to P2 without invoking escalation | Assert the threshold boundary independently of escalation |
| Invalid structured output | Model returns a decision that fails Epic 1 validation | One corrective retry, then stop | Raise a clear validation error after the second failure |
| Provider override | `PROVIDER=groq`, `MODEL`, and Groq credentials | The `run_agent.py` invocation uses ChatGroq with the override model and key | Default path uses Gemini and its configured model/key |
| Unknown ticket | Ticket ID is not present in the database | No decision is returned | Propagate a clear lookup error |
| Missing database | `app.db` is absent | No model call is attempted | Propagate the loader instruction from the MCP server |

</frozen-after-approval>

## Code Map

- `run_agent.py` -- existing CLI and protected MLflow integration; import and call `agent.triage` without changing tracking setup.
- `mcp/triage_server.py` -- read-only MCP server exposing `get_ticket` and `get_customer_history`; connect through `MultiServerMCPClient` over stdio.
- `TRIAGE_POLICY.md` -- read-only system instructions, including category/route mapping, priority rules, safety rule, and output requirements.
- `pyproject.toml` -- existing LangChain, provider, MCP adapter, Pydantic, dotenv, and pytest dependencies.
- `upstream/stage-3:agent.py` -- historical implementation reference for `create_agent`, provider selection, structured output retry, and MCP wiring; reuse the non-escalation portions only.
- `upstream/stage-3:tests/test_agent.py` -- historical test seam for fake-model agent tests and provider defaults; extend it with dynamic MCP argument, key propagation, threshold, retry-count, and error-path assertions.
- `triage/schema.py` and `load_seed.py` -- required Epic 1 dependency; these must already be present from Epic 1 before this story starts and remain unchanged here.

## Tasks & Acceptance

**Execution:**
- [x] `agent.py` -- add provider selection, MCP stdio client setup, policy system prompt, `create_agent`, structured output retry, and async `triage` entry point.
- [x] `tests/test_agent.py` -- test fake-model tool ordering with the returned customer ID, provider defaults/overrides and key propagation, the Enterprise threshold, exactly one retry, unknown-ticket/database errors, and prompt-injection behavior without API keys.
- [x] `pyproject.toml` -- no change required; the existing LangChain, provider, MCP adapter, Pydantic, dotenv, and pytest dependencies resolve the implementation.

**Acceptance Criteria:**
- Given a valid Epic 1 dependency and a scripted model, when `triage` runs, then it calls `get_ticket` before `get_customer_history` with the returned customer ID and returns a validated decision.
- Given no provider override, when the agent is built, then it uses ChatGoogleGenerativeAI with `MODEL` or `gemini-3.8-flash` and passes `GEMINI_API_KEY`.
- Given `PROVIDER=groq`, when the agent is built, then it uses ChatGroq with `MODEL` or `openai/gpt-oss-120b` and passes `GROQ_API_KEY`.
- Given an explicit `MODEL`, when either provider is built, then that model is used; given an unsupported `PROVIDER`, then the agent fails clearly without silently selecting a provider.
- Given invalid structured output from the model, when schema validation fails, then exactly two model attempts occur and the second failure raises a clear validation error.
- Given an Enterprise customer with 3 open tickets and a base P3 ticket, when the ticket is triaged, then the result is P2 without escalation tooling.
- Given T-1099's real ticket text, when the ticket is triaged, then the result follows the policy and does not promote itself to P1.
- Given an unknown ticket ID or missing database, when the agent runs, then it returns a clear lookup error and does not call the model.
- Given `uv run python run_agent.py T-1042`, when prerequisites and credentials are available, then the command prints a valid billing/P2/billing-team decision and preserves the MLflow trace setup.

## Implementation Notes

 - Added `agent.py` with environment-driven Gemini/Groq construction, policy-loaded `create_agent`, MCP stdio tools, structured-output retry, and explicit MCP error propagation.
 - Merged the local Epic 1 prerequisite from `upstream/stage-2` while preserving the approved Epic 1 specification artifacts; the agent imports `triage.schema` and relies on `load_seed.py` unchanged.
 - Excluded escalation tools and human-in-the-loop middleware for story 1; those remain story 2 scope.
 - Verification: 9 focused agent tests and 30 combined Epic 1/Epic 2 tests passed. The credentialed `run_agent.py T-1042` smoke test remains pending because `.env` contains no API keys.

## Design Notes

The historical stage-3 implementation is a compatibility reference, not a source to copy wholesale. Reuse its agent wiring while excluding `escalate_to_human` and `HumanInTheLoopMiddleware`; use a fake MCP boundary that records tool order and arguments, plus one policy-grounded fixture test for T-1099. Network-backed model calls are reserved for explicit end-to-end checks.

## Review Triage Log

- high -- `agent.py` allowed unknown-ticket tool errors to reach the model -- patched with an MCP ticket preflight and a regression test asserting model construction is skipped.
- medium -- the T-1099 test only checked fixture text -- patched with an agent-level T-1099 decision test.
- medium -- structured-output retry was only helper-tested -- patched with an agent-level two-invalid-output test.
- medium -- the happy-path test did not prove customer-ID propagation -- patched with a response-driven fake model that extracts the ID from the real MCP response.
- medium, deferred -- deterministic enforcement of tool order, Enterprise priority bump, and injection resistance beyond the policy prompt would duplicate the model policy layer; settle with credentialed end-to-end trace/evaluation coverage in the story's verification environment.
- medium, deferred -- route consistency and rationale sentence edge cases belong to the pre-existing Epic 1 schema and are outside this story's read-only boundary.

## Verification

**Commands:**
- `uv run pytest tests/test_agent.py` -- expected: focused agent tests pass without API keys.
- `uv run pytest` -- expected: all repository tests pass.
- `uv run python run_agent.py T-1042` -- expected: valid decision and MLflow trace when the dependency database and provider credentials are available.
