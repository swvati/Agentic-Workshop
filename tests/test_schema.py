import json

import pytest

from triage.schema import TriageDecision, TriageValidationError, validate_decision

VALID = {"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "A double charge is a money problem."}


def test_accepts_a_valid_decision_as_dict_or_json():
    assert validate_decision(VALID) == TriageDecision(**VALID)
    assert validate_decision(json.dumps(VALID)).priority == "P2"


@pytest.mark.parametrize(
    "change, field",
    [
        ({"category": "sales"}, "category"),
        ({"priority": "P5"}, "priority"),
        ({"route": "finance-team"}, "route"),
        ({"rationale": "   "}, "rationale"),
        ({"rationale": "First sentence. Second sentence."}, "rationale"),
        ({"extra": "field"}, "extra"),
    ],
)
def test_rejects_bad_fields_with_a_message_naming_the_field(change, field):
    with pytest.raises(TriageValidationError, match=field):
        validate_decision({**VALID, **change})


@pytest.mark.parametrize("field", ["category", "priority", "route", "rationale"])
def test_rejects_a_missing_field(field):
    payload = {k: v for k, v in VALID.items() if k != field}
    with pytest.raises(TriageValidationError, match=field):
        validate_decision(payload)


@pytest.mark.parametrize("payload", ["not json", b"\x80\x81", "[1, 2]", "42"])
def test_rejects_non_objects(payload):
    with pytest.raises(TriageValidationError):
        validate_decision(payload)


def test_decisions_are_immutable():
    decision = validate_decision(VALID)
    with pytest.raises(Exception, match="frozen"):
        decision.priority = "P1"
