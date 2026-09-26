import sqlite3

import load_seed


def _dump(db_path):
    with sqlite3.connect(db_path) as conn:
        return {table: conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() for table in load_seed.TABLES}


def test_loads_every_row(tmp_path):
    counts = load_seed.load(db_path=tmp_path / "app.db")
    assert counts == {"tickets": 24, "customers": 20}


def test_loading_twice_gives_the_same_database(tmp_path):
    db = tmp_path / "app.db"
    load_seed.load(db_path=db)
    first = _dump(db)
    load_seed.load(db_path=db)
    assert _dump(db) == first


def test_tables_match_what_the_mcp_server_queries(tmp_path):
    db = tmp_path / "app.db"
    load_seed.load(db_path=db)
    with sqlite3.connect(db) as conn:
        ticket = conn.execute("SELECT ticket_id, customer_id, created_at, text FROM tickets WHERE ticket_id = 'T-1042'").fetchone()
        customer = conn.execute("SELECT customer_id, name, plan, open_tickets FROM customers WHERE customer_id = 'C-77'").fetchone()
    assert ticket[1] == "C-77"
    assert customer[2:] == ("Enterprise", 2)
