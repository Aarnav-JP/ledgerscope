"""Tests for the FastAPI server endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import duckdb
import pandas as pd
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ledgerscope.ingest.zerodha import ZerodhaParser

FIXTURES = Path(__file__).parent / "fixtures"


def _create_test_db():
    """Create an in-memory DB with schema, views, and sample data."""
    conn = duckdb.connect(":memory:")

    migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
    for mig_file in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mig_file.read_text())

    views_path = Path(__file__).parent.parent / "ledgerscope" / "analytics" / "views.sql"
    sql = views_path.read_text()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(stmt)

    # Ingest sample data
    parser = ZerodhaParser()
    parser.to_transactions(FIXTURES / "zerodha_sample.csv", conn)

    # Insert mock prices
    random.seed(42)
    symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM transactions").fetchall()]
    for symbol in symbols:
        base_price = 150.0
        prices = []
        current = date(2023, 1, 1)
        for _ in range(300):
            if current.weekday() < 5:
                change = random.gauss(0.0003, 0.015)
                base_price *= (1 + change)
                prices.append({
                    "symbol": symbol,
                    "date": current,
                    "open": round(base_price * 0.998, 2),
                    "high": round(base_price * 1.01, 2),
                    "low": round(base_price * 0.99, 2),
                    "close": round(base_price, 2),
                    "adj_close": round(base_price, 2),
                    "volume": random.randint(1_000_000, 10_000_000),
                    "source": "test",
                })
            current += timedelta(days=1)

        df = pd.DataFrame(prices)
        conn.register("_p", df)
        conn.execute("INSERT OR IGNORE INTO prices SELECT * FROM _p")
        conn.unregister("_p")

    return conn


@pytest.fixture
def client():
    """Create a test client with mocked DB connection."""
    test_conn = _create_test_db()

    # Patch init_db to return our test connection
    with patch("ledgerscope.server.init_db", return_value=test_conn):
        from ledgerscope.server import app
        with TestClient(app) as c:
            yield c

    test_conn.close()


class TestAPIEndpoints:
    def test_holdings(self, client):
        """GET /api/holdings should return holdings data."""
        response = client.get("/api/holdings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "symbol" in data[0]
        assert "shares" in data[0]
        assert "avg_cost" in data[0]

    def test_risk(self, client):
        """GET /api/risk should return risk metrics."""
        response = client.get("/api/risk")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "sharpe" in data[0]
        assert "annual_vol" in data[0]

    def test_pnl(self, client):
        """GET /api/pnl should return P&L history."""
        response = client.get("/api/pnl")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_pnl_with_symbol_filter(self, client):
        """GET /api/pnl?symbol=RELIANCE should filter by symbol."""
        response = client.get("/api/pnl?symbol=RELIANCE")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for item in data:
            assert item["symbol"] == "RELIANCE"

    def test_drawdown(self, client):
        """GET /api/drawdown should return drawdown data."""
        response = client.get("/api/drawdown")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "max_drawdown" in data[0]

    def test_benchmark(self, client):
        """GET /api/benchmark should return benchmark comparison."""
        response = client.get("/api/benchmark")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_dividends(self, client):
        """GET /api/dividends should return dividend data."""
        response = client.get("/api/dividends")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_summary(self, client):
        """GET /api/summary should return portfolio summary."""
        response = client.get("/api/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "total_cost" in data
        assert "total_pnl" in data
        assert "num_holdings" in data
        assert data["num_holdings"] > 0

    def test_backtest_endpoint(self, client):
        """POST /api/backtest should run a strategy."""
        strategy = """
            SELECT date, 'RELIANCE' as symbol, 'HOLD' as signal
            FROM prices WHERE symbol = 'RELIANCE'
        """
        response = client.post("/api/backtest", json={
            "strategy_sql": strategy,
            "initial_capital": 10000,
        })
        assert response.status_code == 200
        data = response.json()
        assert "total_return_pct" in data
        assert "symbol" in data

    def test_backtest_invalid_sql(self, client):
        """POST /api/backtest with bad SQL should return 400."""
        response = client.post("/api/backtest", json={
            "strategy_sql": "SELECT * FROM nonexistent",
        })
        assert response.status_code == 400

    def test_report_pdf_stub(self, client):
        """GET /api/report/pdf should return 200 (PDF generation works)."""
        response = client.get("/api/report/pdf")
        assert response.status_code == 200
