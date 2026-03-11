"""End-to-end tests: ingest → views → query risk_summary."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from ledgerscope.ingest.zerodha import ZerodhaParser
from ledgerscope.ingest.robinhood import RobinhoodParser

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def full_db():
    """Create an in-memory DB with schema, views, and sample transactions."""
    conn = duckdb.connect(":memory:")

    # Apply migrations
    migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
    for mig_file in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mig_file.read_text())

    # Apply views
    views_path = Path(__file__).parent.parent / "ledgerscope" / "analytics" / "views.sql"
    sql = views_path.read_text()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(stmt)

    yield conn
    conn.close()


def _insert_mock_prices(conn: duckdb.DuckDBPyConnection, symbol: str) -> None:
    """Insert fake price data for a symbol across 252 trading days."""
    import random
    random.seed(42)

    base_price = 150.0
    prices = []
    current = date(2023, 1, 1)

    for i in range(300):
        if current.weekday() < 5:  # Skip weekends
            change = random.gauss(0.0005, 0.02)  # slight upward drift
            base_price *= (1 + change)
            prices.append({
                "symbol": symbol,
                "date": current,
                "open": round(base_price * 0.998, 2),
                "high": round(base_price * 1.01, 2),
                "low": round(base_price * 0.99, 2),
                "close": round(base_price, 2),
                "adj_close": round(base_price, 2),
                "volume": random.randint(1000000, 10000000),
                "source": "test",
            })
        current += timedelta(days=1)

    df = pd.DataFrame(prices)
    conn.register("_mock_prices", df)
    conn.execute("""
        INSERT OR IGNORE INTO prices
        SELECT * FROM _mock_prices
    """)
    conn.unregister("_mock_prices")


class TestEndToEnd:
    def test_zerodha_ingest_to_holdings(self, full_db):
        """Ingest Zerodha CSV → verify holdings view has data."""
        parser = ZerodhaParser()
        count = parser.to_transactions(FIXTURES / "zerodha_sample.csv", full_db)
        assert count == 8

        # Check transactions table
        tx_count = full_db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert tx_count == 8

        # Check holdings view
        holdings = full_db.execute("SELECT * FROM holdings").fetchall()
        assert len(holdings) > 0

        # Verify known position: RELIANCE had 10 buys - 4 sells = 6 shares
        reliance = [h for h in holdings if h[0] == "RELIANCE"]
        assert len(reliance) == 1
        assert reliance[0][1] == 6  # shares

    def test_risk_summary_with_prices(self, full_db):
        """Ingest → insert mock prices → verify risk_summary returns data."""
        parser = ZerodhaParser()
        parser.to_transactions(FIXTURES / "zerodha_sample.csv", full_db)

        # Get symbols from holdings
        holdings = full_db.execute("SELECT symbol FROM holdings").fetchall()
        symbols = [h[0] for h in holdings]

        # Insert mock prices for each symbol
        for symbol in symbols:
            _insert_mock_prices(full_db, symbol)

        # Check risk_summary
        risk = full_db.execute("SELECT * FROM risk_summary").fetchall()
        assert len(risk) > 0

        # Verify Sharpe ratio is present (not null) for at least one symbol
        sharpe_values = [r[3] for r in risk]  # sharpe is 4th column
        assert any(s is not None for s in sharpe_values)

    def test_robinhood_ingest_with_dividends(self, full_db):
        """Ingest Robinhood CSV → verify dividend_income view."""
        parser = RobinhoodParser()
        count = parser.to_transactions(FIXTURES / "robinhood_sample.csv", full_db)
        assert count > 0

        # Check that dividend rows were imported
        divs = full_db.execute(
            "SELECT COUNT(*) FROM transactions WHERE action = 'DIVIDEND'"
        ).fetchone()[0]
        assert divs > 0

        # Check dividend_income view
        div_income = full_db.execute("SELECT * FROM dividend_income").fetchall()
        assert len(div_income) > 0

    def test_drawdown_view(self, full_db):
        """Verify drawdown view works with mock price data."""
        parser = ZerodhaParser()
        parser.to_transactions(FIXTURES / "zerodha_sample.csv", full_db)

        holdings = full_db.execute("SELECT symbol FROM holdings").fetchall()
        for (symbol,) in holdings:
            _insert_mock_prices(full_db, symbol)

        drawdown = full_db.execute("SELECT * FROM drawdown").fetchall()
        assert len(drawdown) > 0

        # Max drawdown should be negative or zero
        for row in drawdown:
            assert row[1] <= 0  # max_drawdown column

    def test_idempotent_double_import(self, full_db):
        """Importing the same file twice should not create duplicates."""
        parser = ZerodhaParser()
        parser.to_transactions(FIXTURES / "zerodha_sample.csv", full_db)
        parser.to_transactions(FIXTURES / "zerodha_sample.csv", full_db)

        tx_count = full_db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert tx_count == 8

    def test_multiple_brokers(self, full_db):
        """Import from multiple brokers into the same database."""
        from ledgerscope.ingest.ibkr import IBKRParser

        zerodha = ZerodhaParser()
        robinhood = RobinhoodParser()
        ibkr = IBKRParser()

        z_count = zerodha.to_transactions(FIXTURES / "zerodha_sample.csv", full_db)
        r_count = robinhood.to_transactions(FIXTURES / "robinhood_sample.csv", full_db)
        i_count = ibkr.to_transactions(FIXTURES / "ibkr_sample.csv", full_db)

        total = full_db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert total == z_count + r_count + i_count

        # Check we have multiple brokers
        brokers = full_db.execute(
            "SELECT DISTINCT broker FROM transactions"
        ).fetchall()
        broker_names = {b[0] for b in brokers}
        assert "zerodha" in broker_names
        assert "robinhood" in broker_names
        assert "ibkr" in broker_names
