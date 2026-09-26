- source_spec: `_bmad-output/implementation-artifacts/spec-2-1-triage-agent.md`
  summary: Add credentialed end-to-end trace and evaluation coverage for model-enforced tool order, Enterprise priority bump, and prompt-injection resistance.
  evidence: Local tests verify prompt wiring and response-dependent MCP arguments, but deterministic enforcement of model policy would duplicate the policy layer; settle with real-provider traces/evaluation.
  resolution: Verified 2026-09-26 with `GEMINI_API_KEY` set -- `run_agent.py T-1042` returned billing/P2/billing-team and `run_agent.py T-1099` returned bug/P4/bug-team, both recorded as MLflow traces. Enterprise threshold bump beyond T-1042's under-threshold case remains unexercised with a real model.
- source_spec: `_bmad-output/implementation-artifacts/spec-2-1-triage-agent.md`
  summary: Review route consistency and rationale sentence edge cases in the Epic 1 schema.
  evidence: These behaviors belong to the pre-existing Epic 1 implementation, which this story is required to leave unchanged.
- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-human-gated-escalation.md`
  summary: Add code-level or eval verification that escalate_to_human is actually called whenever the P1+Enterprise rule fires, rather than relying solely on prompt compliance.
  evidence: Enforcing this in code would duplicate the model policy layer, matching the same boundary already deferred for story 1; settle with credentialed end-to-end/eval coverage.
- source_spec: `_bmad-output/implementation-artifacts/spec-2-2-human-gated-escalation.md`
  summary: Bound the number of times the model may retry escalate_to_human after a declined approval.
  evidence: The resume loop in agent.py's triage() is unbounded, matching the historical upstream/stage-3 reference this story reuses; the spec's I/O matrix does not require a retry cap, but a misbehaving model could loop indefinitely in production.
