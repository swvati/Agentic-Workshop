import importlib.util
from pathlib import Path

import pytest

import load_seed

SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp" / "triage_server.py"


@pytest.fixture
def server(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("triage_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    db = tmp_path / "app.db"
    load_seed.load(db_path=db)
    monkeypatch.setattr(module, "DB_PATH", db)
    return module


def test_get_ticket_returns_the_customer_id(server):
    assert server.get_ticket("T-1042")["customer_id"] == "C-77"


def test_get_customer_history_lists_their_tickets(server):
    history = server.get_customer_history("C-77")
    assert history["plan"] == "Enterprise"
    assert history["ticket_ids"] == ["T-1042", "T-1047"]


def test_unknown_ids_raise_a_clear_error(server):
    with pytest.raises(ValueError, match="T-0000"):
        server.get_ticket("T-0000")
