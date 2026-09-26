---
id: SPEC-epic-1
companions:
  - ../../../mcp/triage_server.py
  - ../../../seed/tickets.csv
  - ../../../seed/customers.csv
sources:
  - ../../../INTENT.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability; consult them only if narrative rationale is needed.

# Epic 1: triage data and schema

## Why

Epic 1 establishes the data and decision contract for the workshop's triage workflow. Decisions need a clear validated shape, and the existing triage server expects a local `app.db` populated from the workshop's ticket and customer data. A repeatable, offline loader gives later work stable inputs without changing the server's database interface.

## Capabilities

- **CAP-1**
  - **intent:** A triage decision can be represented and validated as a JSON object with the required category, priority, route, and rationale.
  - **success:** Valid decisions use category `billing`, `bug`, `access`, `performance`, or `how-to`; priority `P1` through `P4`; a route from `billing-team`, `bug-team`, `access-team`, `performance-team`, or `how-to-team`; and a one-sentence rationale. Decisions outside this contract are rejected with a clear error.

- **CAP-2**
  - **intent:** A developer can load the supplied ticket and customer data into the local database used by the triage workflow.
  - **success:** Running `uv run python load_seed.py` loads `seed/tickets.csv` and `seed/customers.csv` into `app.db` tables named `tickets` and `customers`, with columns matching their respective CSV files. Running the command again leaves the same database.

## Constraints

- Use Python 3.12 or newer and `uv`.
- Treat both files under `seed/` as read-only.
- Make no network calls and require no API keys.
- Keep the `app.db` table and column names compatible with the existing `mcp/triage_server.py` queries.

## Non-goals

- The triage agent, MCP tools, evals, and any user interface.

## Success signal

A developer can run the loader once to create the local database expected by the existing triage server, and run it again without changing the resulting data. Triage decisions conform to the declared JSON contract, while invalid decisions produce a clear error.

## Open Questions

- Must each category map to one specific route, or is any listed route valid with any listed category?