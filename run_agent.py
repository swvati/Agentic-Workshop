"""Triage one support ticket with the agent and print the decision.

Usage: uv run python run_agent.py T-1042
"""

import asyncio
import json
import sys

import mlflow
from dotenv import load_dotenv


def ask_at_terminal(request: dict) -> bool:
    """Ask the person at the terminal to approve one escalation. Blank,
    unrecognized, or non-interactive (no stdin) input is treated as a decline."""
    args = request.get("args", {})
    try:
        answer = input(
            f"\nEscalate {args.get('ticket_id')} to a person? Reason: {args.get('reason')}\nApprove? [y/N] "
        )
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: uv run python run_agent.py <ticket_id>")
    ticket_id = sys.argv[1]

    load_dotenv()
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("triage-agent")
    mlflow.langchain.autolog()

    try:
        from agent import triage
    except ImportError:
        raise SystemExit("The agent isn't built yet. That's Epic 2: _bmad-output/specs/spec-epic-2/SPEC.md")

    with mlflow.start_span(name="triage", span_type="AGENT") as span:
        span.set_inputs({"ticket_id": ticket_id})
        decision = asyncio.run(triage(ticket_id, approve=ask_at_terminal))
        span.set_outputs(decision)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
