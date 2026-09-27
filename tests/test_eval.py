"""Tests for eval/run_eval.py's dataset, scorers, and scripted harness run."""

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import mlflow
import pytest
from mlflow.entities import SpanType

import agent
import load_seed
from test_agent import scripted

RUN_EVAL_PATH = Path(__file__).resolve().parent.parent / "eval" / "run_eval.py"


@pytest.fixture(scope="module")
def run_eval():
    spec = importlib.util.spec_from_file_location("run_eval", RUN_EVAL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module", autouse=True)
def app_db():
    load_seed.load()


def _span(name, span_type, start):
    return SimpleNamespace(name=name, span_type=span_type, start_time_ns=start)


def _trace(spans):
    return SimpleNamespace(data=SimpleNamespace(spans=spans))


def test_load_eval_set_returns_all_twenty_rows_with_expected_shape(run_eval):
    rows = run_eval.load_eval_set()
    assert len(rows) == 20
    row = next(r for r in rows if r["inputs"]["ticket_id"] == "T-1042")
    assert row["expectations"]["category"] == "billing"
    assert row["expectations"]["priority"] == "P2"


def test_valid_schema_scores_a_valid_decision(run_eval):
    result = run_eval.valid_schema(
        outputs={"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "x"}
    )
    assert result.value is True


def test_valid_schema_scores_an_invalid_decision(run_eval):
    result = run_eval.valid_schema(outputs={"category": "not-a-category"})
    assert result.value is False
    assert result.rationale


def test_category_and_priority_match(run_eval):
    outputs = {"category": "billing", "priority": "P2"}
    assert run_eval.category_match(outputs=outputs, expectations={"category": "billing"}) is True
    assert run_eval.category_match(outputs=outputs, expectations={"category": "bug"}) is False
    assert run_eval.priority_match(outputs=outputs, expectations={"priority": "P2"}) is True
    assert run_eval.priority_match(outputs=outputs, expectations={"priority": "P4"}) is False


def test_tool_order_scores_correct_order_as_true(run_eval):
    trace = _trace(
        [
            _span("get_ticket", SpanType.TOOL, 1),
            _span("get_customer_history", SpanType.TOOL, 2),
        ]
    )
    result = run_eval.tool_order(trace=trace)
    assert result.value is True


def test_tool_order_scores_reversed_order_as_false(run_eval):
    trace = _trace(
        [
            _span("get_customer_history", SpanType.TOOL, 1),
            _span("get_ticket", SpanType.TOOL, 2),
        ]
    )
    result = run_eval.tool_order(trace=trace)
    assert result.value is False


def test_tool_order_scores_a_missing_call_as_false(run_eval):
    trace = _trace([_span("get_ticket", SpanType.TOOL, 1)])
    result = run_eval.tool_order(trace=trace)
    assert result.value is False


def test_predict_forwards_the_auto_approve_callback_to_triage(run_eval, monkeypatch):
    captured = {}

    async def stub_triage(ticket_id, model=None, approve=None):
        captured["ticket_id"] = ticket_id
        captured["approve"] = approve
        return {"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "stub"}

    monkeypatch.setattr(run_eval, "triage", stub_triage)
    decision = run_eval.predict("T-1042")
    assert decision == {"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "stub"}
    assert captured["ticket_id"] == "T-1042"
    assert captured["approve"] is run_eval.approve_automatically


def test_predict_auto_approves_an_escalation_without_blocking(run_eval, monkeypatch):
    monkeypatch.setattr(run_eval, "_escalations", [])
    outage = {
        "category": "access",
        "priority": "P1",
        "route": "access-team",
        "rationale": "A whole team locked out is an outage for an Enterprise customer.",
    }
    model = scripted("T-1044", "C-91", outage, escalate=True)
    decision = asyncio.run(agent.triage("T-1044", model, approve=run_eval.approve_automatically))
    assert decision == outage
    assert run_eval._escalations == [{"ticket_id": "T-1044", "reason": "P1 for an Enterprise customer"}]


def test_evaluate_scores_a_scripted_subset(run_eval, tmp_path, monkeypatch):
    monkeypatch.setattr(run_eval, "_escalations", [])
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")
    mlflow.set_experiment("triage-agent-test")
    mlflow.langchain.autolog()

    billing = {
        "category": "billing",
        "priority": "P2",
        "route": "billing-team",
        "rationale": "A double charge is a money problem.",
    }
    wrong_priority = {
        "category": "billing",
        "priority": "P3",
        "route": "billing-team",
        "rationale": "Wrong on purpose.",
    }

    def fake_predict(ticket_id):
        answers = {"T-1042": ("C-77", billing), "T-1047": ("C-05", wrong_priority)}
        customer_id, decision = answers[ticket_id]
        model = scripted(ticket_id, customer_id, decision)
        return asyncio.run(agent.triage(ticket_id, model, approve=run_eval.approve_automatically))

    traced_predict = mlflow.trace(name="triage", span_type="AGENT")(fake_predict)

    rows = [row for row in run_eval.load_eval_set() if row["inputs"]["ticket_id"] in {"T-1042", "T-1047"}]
    scorers = [run_eval.valid_schema, run_eval.category_match, run_eval.priority_match, run_eval.tool_order]
    results = mlflow.genai.evaluate(data=rows, predict_fn=traced_predict, scorers=scorers)

    assert results.metrics["valid_schema/mean"] == 1.0
    assert results.metrics["category_match/mean"] == 1.0
    assert results.metrics["priority_match/mean"] == 0.5
    assert results.metrics["tool_order/mean"] == 1.0
