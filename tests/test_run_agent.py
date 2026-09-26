"""Tests for run_agent.py's terminal approval prompt."""

import run_agent


def test_ask_at_terminal_approves_only_on_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    approved = run_agent.ask_at_terminal({"args": {"ticket_id": "T-1044", "reason": "outage"}})
    assert approved is True


def test_ask_at_terminal_shows_the_ticket_and_reason(monkeypatch):
    seen_prompt = {}

    def fake_input(prompt):
        seen_prompt["text"] = prompt
        return "yes"

    monkeypatch.setattr("builtins.input", fake_input)
    run_agent.ask_at_terminal({"args": {"ticket_id": "T-1044", "reason": "outage"}})
    assert "T-1044" in seen_prompt["text"]
    assert "outage" in seen_prompt["text"]


def test_ask_at_terminal_declines_on_blank_or_unrecognized_input(monkeypatch):
    for answer in ["", "   ", "n", "no", "sure"]:
        monkeypatch.setattr("builtins.input", lambda _, answer=answer: answer)
        assert run_agent.ask_at_terminal({"args": {"ticket_id": "T-1044", "reason": "r"}}) is False


def test_ask_at_terminal_declines_when_stdin_is_not_interactive(monkeypatch):
    def raise_eof(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    assert run_agent.ask_at_terminal({"args": {"ticket_id": "T-1044", "reason": "r"}}) is False
