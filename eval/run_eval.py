"""Evaluate the triage agent on the labelled tickets (Epic 3, story 1).

Usage: uv run python eval/run_eval.py
Logs one MLflow run in the triage-agent experiment, scored by four code
scorers. Escalations are auto-approved so the run never waits on a person.
"""

import asyncio
import csv
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "2")  # stay under free-tier rate limits

import mlflow  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from mlflow.entities import Feedback, SpanType  # noqa: E402
from mlflow.genai.scorers import scorer  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from agent import triage  # noqa: E402
from triage.schema import TriageDecision  # noqa: E402

LABELS = ROOT / "eval" / "labelled_tickets.csv"
TOOLS = ("get_ticket", "get_customer_history")

_escalations: list[dict] = []
_lock = threading.Lock()


def approve_automatically(request: dict) -> bool:
    """Evals never wait for a person: approve every escalation and count it."""
    with _lock:
        _escalations.append(request.get("args", {}))
    return True


@mlflow.trace(name="triage", span_type=SpanType.AGENT)
def predict(ticket_id: str) -> dict:
    """One trace per ticket, so an approved escalation's resumed call stays in
    the same trace as the tool calls."""
    return asyncio.run(triage(ticket_id, approve=approve_automatically))


def load_eval_set() -> list[dict]:
    """Build the mlflow.genai.evaluate dataset from the labelled tickets CSV."""
    with LABELS.open(newline="", encoding="utf-8") as handle:
        return [
            {
                "inputs": {"ticket_id": row["ticket_id"]},
                "expectations": {
                    "category": row["expected_category"],
                    "priority": row["expected_priority"],
                    "judge_notes": row["judge_notes"],
                },
            }
            for row in csv.DictReader(handle)
        ]


@scorer
def valid_schema(outputs) -> Feedback:
    """1 when the output validates against the Epic 1 triage-decision schema."""
    try:
        TriageDecision.model_validate(outputs)
        return Feedback(value=True)
    except ValidationError as error:
        return Feedback(value=False, rationale=str(error))


@scorer
def category_match(outputs, expectations) -> bool:
    """1 when the output's category equals the labelled expected_category."""
    return outputs.get("category") == expectations.get("category")


@scorer
def priority_match(outputs, expectations) -> bool:
    """1 when the output's priority equals the labelled expected_priority."""
    return outputs.get("priority") == expectations.get("priority")


@scorer
def tool_order(trace) -> Feedback:
    """1 when the trace shows get_ticket starting before get_customer_history."""
    spans = sorted(trace.data.spans, key=lambda span: span.start_time_ns)
    calls = [span.name for span in spans if span.span_type == SpanType.TOOL and span.name in TOOLS]
    in_order = TOOLS[0] in calls and TOOLS[1] in calls and calls.index(TOOLS[0]) < calls.index(TOOLS[1])
    return Feedback(value=in_order, rationale=f"Tool calls: {', '.join(calls) or 'none'}")


def main() -> None:
    load_dotenv(ROOT / ".env")
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("triage-agent")
    mlflow.langchain.autolog()
    _escalations.clear()

    scorers = [valid_schema, category_match, priority_match, tool_order]
    results = mlflow.genai.evaluate(data=load_eval_set(), predict_fn=predict, scorers=scorers)

    print(f"Eval run {results.run_id}")


if __name__ == "__main__":
    main()
