---
title: 'The eval run and the four code scorers'
type: 'feature'
created: '2026-09-26'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '118b2c0ad9d70890f4a47c29bb41cfedac0ea98b'
context:
  - _bmad-output/specs/spec-epic-3/SPEC.md
  - agent.py
  - triage/schema.py
  - mcp/triage_server.py
  - eval/labelled_tickets.csv
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Epic 2 agent decides, but nothing in the repo measures how well or drives it over the labelled fixture set; there is no `eval/run_eval.py`.

**Approach:** Build `eval/run_eval.py`'s eval harness: one `mlflow.trace`-wrapped `predict` function that calls the existing `agent.triage` with an auto-approving escalation callback, a 20-row dataset built from `eval/labelled_tickets.csv`, and four code scorers (`valid_schema`, `category_match`, `priority_match`, `tool_order`) driven through `mlflow.genai.evaluate`. Track every auto-approved escalation for story 2 to report later.

## Boundaries & Constraints

**Always:** Build with `mlflow.genai.evaluate`, not a hand-rolled scoring loop; call `agent.triage` unchanged -- no edits to its decision logic, prompts, or policy handling; keep `eval/labelled_tickets.csv` and `TRIAGE_POLICY.md` read-only; wrap each ticket's prediction in one `mlflow.trace` so an approved escalation's resumed call stays in the same trace; auto-approve every escalation raised during the run so it never blocks on terminal input; log exactly one MLflow run to `sqlite:///mlflow.db` under the `triage-agent` experiment.

**Never:** Add the `rationale_judge` scorer, printed score/token/escalation output, or `eval/latest_report.json` -- those are story 2's CAP-6/CAP-7; change a normal `run_agent.py` invocation's escalation behavior (it must still pause for a person); make network calls beyond the agent's own model call.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|-----------------------------|----------------|
| Full run | All 20 rows of `eval/labelled_tickets.csv` | `mlflow.genai.evaluate` logs one run scored by all four scorers | N/A |
| Escalating ticket (e.g. T-1044) | P1 + Enterprise ticket | Escalation is auto-approved without terminal input; the run continues in the same trace | N/A |
| Valid decision | Agent output matches the Epic 1 schema | `valid_schema` scores 1 | N/A |
| Invalid decision | Agent output fails Epic 1 validation | `valid_schema` scores 0 with a rationale | Never raises out of the scorer |
| Category/priority mismatch | Output differs from `expected_category`/`expected_priority` | `category_match`/`priority_match` score 0 | N/A |
| Tool order violated or missing | Trace lacks `get_ticket` before `get_customer_history` | `tool_order` scores 0 with a rationale naming the calls seen | N/A |

</frozen-after-approval>

## Code Map

- `agent.py` -- `triage(ticket_id, model=None, approve=None)`; call as-is with an `approve` callback that always returns `True` and records the request.
- `triage/schema.py` -- `TriageDecision`; used by `valid_schema` to validate scorer `outputs`.
- `mcp/triage_server.py` -- tool names `get_ticket`/`get_customer_history`; `tool_order` matches spans by these names.
- `eval/labelled_tickets.csv` -- columns `ticket_id,expected_category,expected_priority,expected_tools,judge_notes`; read-only fixture, 20 rows including P1+Enterprise tickets T-1044/T-1048/T-1057.
- `upstream/stage-4:eval/run_eval.py` -- historical reference implementing both stories in one file (predict, dataset, all five scorers, report/print); reuse only the CAP-1..CAP-5/CAP-8 portions (predict, `load_eval_set`, the four code scorers, `approve_automatically`) and leave `rationale_judge`/report/print for story 2.
- `upstream/stage-4:tests/test_eval.py` -- historical test pattern: loads `eval/run_eval.py` via `importlib`, reuses `tests/test_agent.py`'s `scripted` model, and asserts on `mlflow.genai.evaluate`'s `results.metrics`.
- `tests/test_agent.py` -- `scripted(ticket_id, customer_id, decision, escalate=False)`; reuse to build a scripted agent for eval tests without API keys.

## Tasks & Acceptance

**Execution:**
- [x] `eval/run_eval.py` -- add `load_eval_set()` (dataset rows with `inputs.ticket_id` and `expectations.category/priority`), `approve_automatically(request)` (always approves, appends to an escalations list), a `predict(ticket_id)` function decorated with `mlflow.trace` that calls `agent.triage(ticket_id, approve=approve_automatically)`, the four scorers (`valid_schema`, `category_match`, `priority_match`, `tool_order`), and a `main()` that sets the MLflow tracking URI/experiment/autolog and calls `mlflow.genai.evaluate` with those four scorers over all 20 rows.
- [x] `tests/test_eval.py` -- test `load_eval_set` returns all 20 rows with the right shape; test each of the four scorers directly against fabricated outputs/expectations/trace-like input; test `predict` with a scripted model drives `agent.triage` and records an auto-approved escalation for an escalating ticket without blocking; test `mlflow.genai.evaluate` over a small scripted subset logs one run and scores tickets correctly.

**Acceptance Criteria:**
- Given `eval/labelled_tickets.csv`'s 20 rows, when `load_eval_set()` runs, then it returns 20 entries each with `ticket_id` and the expected category/priority.
- Given a valid Epic 1 decision, when `valid_schema` scores it, then it returns 1; given an invalid one, then it returns 0 with a rationale.
- Given an output category/priority, when `category_match`/`priority_match` score it against `expectations`, then they return 1 only on an exact match.
- Given a trace with `get_ticket` before `get_customer_history`, when `tool_order` scores it, then it returns 1; given the reverse order or a missing call, then it returns 0.
- Given a scripted P1+Enterprise ticket, when `predict` runs it through `agent.triage`, then the escalation is auto-approved, recorded, and the resumed call stays inside the same trace.
- Given a small scripted subset of the eval set, when `mlflow.genai.evaluate` runs with the four scorers, then it logs exactly one MLflow run and the returned metrics match the scripted expectations.

## Implementation Notes

 - Added `eval/run_eval.py`: `load_eval_set`, `approve_automatically`, `mlflow.trace`-wrapped `predict`, the four code scorers, and `main()` calling `mlflow.genai.evaluate` with only those four scorers (no `rationale_judge`, no printed scores/report -- story 2 scope).
 - Reused `upstream/stage-4:eval/run_eval.py`'s shape for the CAP-1/CAP-2..CAP-5/CAP-8 pieces per Design Notes.
 - Verification: 10 tests in `tests/test_eval.py`, 26 in the Epic 1/run_agent suites, 17 in `tests/test_agent.py` (unaffected, unmodified) -- 53 total, no regressions.
 - Mutation-tested `predict()`'s `approve=` keyword forwarding by dropping it and confirming `test_predict_forwards_the_auto_approve_callback_to_triage` fails, then reverted.

## Review Triage Log

- high (self-caught bad_spec violation) -- `main()`'s original `print(f"Escalations auto-approved: ...")` violated this story's own frozen "Never" boundary reserving escalation output for story 2's CAP-7 -- removed; `main()` now prints only the run id.
- high (verification gap) -- no test called the real `predict()` function; `test_evaluate_scores_a_scripted_subset` built its own local `fake_predict` instead, so a broken `approve=` forwarding in `predict()` would ship undetected -- patched by adding `test_predict_forwards_the_auto_approve_callback_to_triage`, which stubs `run_eval.triage` and calls `run_eval.predict` directly; confirmed via mutation to catch a dropped `approve=` keyword.
- medium -- `category_match`/`priority_match` indexed `expectations[...]` directly, raising `KeyError` instead of scoring a malformed row 0 -- patched to use `.get(...)` on both `outputs` and `expectations`, consistent with `valid_schema`'s error handling.
- low -- `approve_automatically` accessed `request["args"]` unconditionally -- patched to `request.get("args", {})`, matching `run_agent.py`'s established defensive pattern.
- low -- `_escalations` module-global state was never reset at the start of `main()`, so a second in-process call would carry over a prior run's escalations -- patched with `_escalations.clear()` at the top of `main()`; the real CLI (fresh subprocess per invocation) was never affected.
- false -- "print of `_escalations` count read without the lock is a race": `mlflow.genai.evaluate` blocks until all worker threads finish before `main()` reaches the print line (now removed anyway), so no concurrent write can be in flight at read time.
- false / not this story's problem -- "`mlflow.langchain.autolog()` may not instrument MCP tool spans, silently scoring `tool_order` false": this is the same autolog call already proven working in `run_agent.py`'s credentialed runs earlier this session (traces with tool spans were confirmed in `mlflow.db`); not a risk introduced by this diff.
- false / out of scope -- "`load_eval_set()` should read the CSV's `expected_tools` column instead of a hardcoded `TOOLS` tuple": every row's `expected_tools` value is identical (`get_ticket,get_customer_history`), and the frozen Code Map and Epic 3's CAP-5 both specify this exact hardcoded pair; there is no per-row variation to honor.
- low, accepted -- `tool_order`'s `.index()`-based check only looks at each tool's first occurrence, so a duplicate out-of-order call after the first pair would go undetected; matches the historical `upstream/stage-4` reference verbatim and the policy prompt only calls each tool once.
- low, accepted -- no test asserts on trace/span structure directly to prove an approved escalation's resumed call stays in the same trace (beyond the escalation being recorded and the decision returned correctly); deferred as a nice-to-have strengthening, not a story-1 blocker.

## Design Notes

The historical `upstream/stage-4:eval/run_eval.py` is a complete, working reference but merges both stories into one file. Reuse its shape for the CAP-1/CAP-2..CAP-5/CAP-8 pieces only; do not add `rationale_judge`, the printed report, or `eval/latest_report.json` here -- those belong to story 2 and would need reworking once story 2's report format is designed.

## Verification

**Commands:**
- `uv run pytest tests/test_eval.py` -- expected: eval scorer and harness tests pass without API keys (Gemini/Groq) beyond what `tests/test_agent.py` already requires.
- `uv run pytest` -- expected: all repository tests pass, no regressions in Epic 1/Epic 2 suites.
- `uv run python eval/run_eval.py` -- expected (credentialed): logs one MLflow run in the `triage-agent` experiment, no terminal prompts even for escalating tickets.
