- source_spec: `_bmad-output/implementation-artifacts/spec-2-1-triage-agent.md`
  summary: Add credentialed end-to-end trace and evaluation coverage for model-enforced tool order, Enterprise priority bump, and prompt-injection resistance.
  evidence: Local tests verify prompt wiring and response-dependent MCP arguments, but deterministic enforcement of model policy would duplicate the policy layer; settle with real-provider traces/evaluation.
  resolution: Verified 2026-09-26 with `GEMINI_API_KEY` set -- `run_agent.py T-1042` returned billing/P2/billing-team and `run_agent.py T-1099` returned bug/P4/bug-team, both recorded as MLflow traces. Enterprise threshold bump beyond T-1042's under-threshold case remains unexercised with a real model.
- source_spec: `_bmad-output/implementation-artifacts/spec-2-1-triage-agent.md`
  summary: Review route consistency and rationale sentence edge cases in the Epic 1 schema.
  evidence: These behaviors belong to the pre-existing Epic 1 implementation, which this story is required to leave unchanged.
