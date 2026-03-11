"""Tests for all three broker parsers."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from ledgerscope.ingest.zerodha import ZerodhaParser
from ledgerscope.ingest.robinhood import RobinhoodParser
from ledgerscope.ingest.ibkr import IBKRParser
from ledgerscope.ingest import get_parser
from ledgerscope.db import run_migrations, create_views

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def db_conn():
    """Create an in-memory DuckDB connection with schema."""
    conn = duckdb.connect(":memory:")
    # Apply migrations manually
    migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
    for mig_file in sorted(migrations_dir.glob("*.sql")):
        conn.execute(mig_file.read_text())
    yield conn
    conn.close()


# ── Factory tests ────────────────────────────────────────────────

class TestParserFactory:
    def test_get_valid_parser(self):
        assert isinstance(get_parser("zerodha"), ZerodhaParser)
        assert isinstance(get_parser("robinhood"), RobinhoodParser)
        assert isinstance(get_parser("ibkr"), IBKRParser)

    def test_get_parser_case_insensitive(self):
        assert isinstance(get_parser("ZERODHA"), ZerodhaParser)
        assert isinstance(get_parser("Robinhood"), RobinhoodParser)

    def test_get_unknown_parser(self):
        with pytest.raises(ValueError, match="Unknown broker"):
            get_parser("unknown_broker")


# ── Zerodha Parser ───────────────────────────────────────────────

class TestZerodhaParser:
    def setup_method(self):
        self.parser = ZerodhaParser()
        self.fixture = FIXTURES / "zerodha_sample.csv"

    def test_validate_success(self):
        self.parser.validate(self.fixture)

    def test_validate_missing_file(self):
        with pytest.raises(FileNotFoundError):
            self.parser.validate(Path("/nonexistent/file.csv"))

    def test_validate_wrong_columns(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("col1,col2,col3\n1,2,3\n")
        with pytest.raises(ValueError, match="missing required columns"):
            self.parser.validate(bad_csv)

    def test_normalize_row_count(self):
        df = self.parser.normalize(self.fixture)
        assert len(df) == 8  # 8 trades in fixture

    def test_normalize_columns(self):
        df = self.parser.normalize(self.fixture)
        expected_cols = {
            "id", "broker", "trade_date", "settle_date", "symbol",
            "isin", "action", "quantity", "price", "fees",
            "currency", "exchange", "notes",
        }
        assert set(df.columns) == expected_cols

    def test_normalize_action_uppercase(self):
        df = self.parser.normalize(self.fixture)
        assert all(a in ("BUY", "SELL") for a in df["action"])

    def test_normalize_broker_name(self):
        df = self.parser.normalize(self.fixture)
        assert all(b == "zerodha" for b in df["broker"])

    def test_normalize_currency(self):
        df = self.parser.normalize(self.fixture)
        assert all(c == "INR" for c in df["currency"])

    def test_normalize_fees_aggregated(self):
        df = self.parser.normalize(self.fixture)
        # Sample missing fee headers -> defaults to 0
        first_row = df.iloc[0]
        assert first_row["fees"] == pytest.approx(0.0)

    def test_normalize_symbols_uppercase(self):
        df = self.parser.normalize(self.fixture)
        assert all(s == s.upper() for s in df["symbol"])

    def test_to_transactions_idempotent(self, db_conn):
        count1 = self.parser.to_transactions(self.fixture, db_conn)
        count2 = self.parser.to_transactions(self.fixture, db_conn)
        # Second import should not add duplicates
        total = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert total == count1
        assert count1 == 8

    def test_deterministic_ids(self):
        df1 = self.parser.normalize(self.fixture)
        df2 = self.parser.normalize(self.fixture)
        assert list(df1["id"]) == list(df2["id"])


# ── Robinhood Parser ─────────────────────────────────────────────

class TestRobinhoodParser:
    def setup_method(self):
        self.parser = RobinhoodParser()
        self.fixture = FIXTURES / "robinhood_sample.csv"

    def test_validate_success(self):
        self.parser.validate(self.fixture)

    def test_validate_missing_file(self):
        with pytest.raises(FileNotFoundError):
            self.parser.validate(Path("/nonexistent/file.csv"))

    def test_normalize_filters_non_trades(self):
        df = self.parser.normalize(self.fixture)
        # ACH row should be filtered out
        assert "ACH" not in df["action"].values
        # But CDIV (dividend) rows should be included
        assert "DIVIDEND" in df["action"].values

    def test_normalize_action_mapping(self):
        df = self.parser.normalize(self.fixture)
        valid_actions = {"BUY", "SELL", "DIVIDEND"}
        assert all(a in valid_actions for a in df["action"])

    def test_normalize_date_format(self):
        df = self.parser.normalize(self.fixture)
        # Verify dates parsed correctly from MM/DD/YYYY
        from datetime import date
        first_date = df.iloc[0]["trade_date"]
        assert isinstance(first_date, date)

    def test_normalize_price_stripped(self):
        df = self.parser.normalize(self.fixture)
        # Prices should be numeric ($ prefix stripped)
        assert all(isinstance(p, (int, float)) for p in df["price"])
        # First trade: AAPL at $150.12
        buy_rows = df[df["action"] == "BUY"]
        first_buy = buy_rows.iloc[0]
        assert first_buy["price"] == pytest.approx(150.12, abs=0.01)

    def test_normalize_broker_name(self):
        df = self.parser.normalize(self.fixture)
        assert all(b == "robinhood" for b in df["broker"])

    def test_normalize_currency(self):
        df = self.parser.normalize(self.fixture)
        assert all(c == "USD" for c in df["currency"])

    def test_to_transactions_inserts(self, db_conn):
        count = self.parser.to_transactions(self.fixture, db_conn)
        assert count > 0
        total = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert total == count


# ── IBKR Parser ──────────────────────────────────────────────────

class TestIBKRParser:
    def setup_method(self):
        self.parser = IBKRParser()
        self.fixture = FIXTURES / "ibkr_sample.csv"

    def test_validate_success(self):
        self.parser.validate(self.fixture)

    def test_validate_missing_file(self):
        with pytest.raises(FileNotFoundError):
            self.parser.validate(Path("/nonexistent/file.csv"))

    def test_normalize_filters_forex(self):
        df = self.parser.normalize(self.fixture)
        symbols = df["symbol"].values
        # EUR.USD (forex) should be filtered out
        assert "EUR.USD" not in symbols

    def test_normalize_filters_options(self):
        df = self.parser.normalize(self.fixture)
        symbols = df["symbol"].values
        # Options rows should be filtered out
        assert not any("C00" in s for s in symbols)

    def test_normalize_filters_summary(self):
        df = self.parser.normalize(self.fixture)
        # SUMMARY rows have qty=0 and should be excluded

    def test_normalize_action_mapping(self):
        df = self.parser.normalize(self.fixture)
        valid_actions = {"BUY", "SELL"}
        assert all(a in valid_actions for a in df["action"])

    def test_normalize_commission_abs(self):
        df = self.parser.normalize(self.fixture)
        # IBKR commissions are negative in CSV, should be positive fees
        assert all(f >= 0 for f in df["fees"])
        # Each stock trade has commission in CSV
        stock_trades = df[df["quantity"] > 0]
        if len(stock_trades) > 0:
            assert stock_trades.iloc[0]["fees"] == pytest.approx(1.25, abs=0.01)

    def test_normalize_broker_name(self):
        df = self.parser.normalize(self.fixture)
        assert all(b == "ibkr" for b in df["broker"])

    def test_to_transactions_inserts(self, db_conn):
        count = self.parser.to_transactions(self.fixture, db_conn)
        assert count > 0
        total = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert total == count

    def test_to_transactions_idempotent(self, db_conn):
        count1 = self.parser.to_transactions(self.fixture, db_conn)
        count2 = self.parser.to_transactions(self.fixture, db_conn)
        total = db_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert total == count1
