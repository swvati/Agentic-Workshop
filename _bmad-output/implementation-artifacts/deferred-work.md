- source_spec: `_bmad-output/implementation-artifacts/spec-2-1-triage-agent.md`
  summary: Add credentialed end-to-end trace and evaluation coverage for model-enforced tool order, Enterprise priority bump, and prompt-injection resistance.
  evidence: Local tests verify prompt wiring and response-dependent MCP arguments, but deterministic enforcement of model policy would duplicate the policy layer; settle with real-provider traces/evaluation.
- source_spec: `_bmad-output/implementation-artifacts/spec-2-1-triage-agent.md`
  summary: Review route consistency and rationale sentence edge cases in the Epic 1 schema.
  evidence: These behaviors belong to the pre-existing Epic 1 implementation, which this story is required to leave unchanged.
