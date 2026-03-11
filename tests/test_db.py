"""Tests for database initialization and migration system."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest


@pytest.fixture
def db_conn():
    """Create a fresh in-memory DuckDB connection."""
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


class TestMigrations:
    def test_migration_creates_tables(self, db_conn):
        """Verify the initial migration creates all required tables."""
        migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
        sql = (migrations_dir / "001_initial.sql").read_text()
        db_conn.execute(sql)

        # Check transactions table exists
        tables = db_conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = {t[0] for t in tables}

        assert "transactions" in table_names
        assert "prices" in table_names
        assert "macro_data" in table_names

    def test_transactions_columns(self, db_conn):
        """Verify the transactions table has all required columns."""
        migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
        db_conn.execute((migrations_dir / "001_initial.sql").read_text())

        result = db_conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'transactions' ORDER BY ordinal_position"
        ).fetchall()
        cols = {r[0] for r in result}

        expected = {
            "id", "broker", "trade_date", "settle_date", "symbol",
            "isin", "action", "quantity", "price", "fees",
            "currency", "exchange", "notes", "imported_at",
        }
        assert expected.issubset(cols)

    def test_prices_columns(self, db_conn):
        """Verify the prices table has all required columns."""
        migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
        db_conn.execute((migrations_dir / "001_initial.sql").read_text())

        result = db_conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'prices'"
        ).fetchall()
        cols = {r[0] for r in result}

        expected = {"symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "source"}
        assert expected.issubset(cols)

    def test_migration_is_idempotent(self, db_conn):
        """Running migrations twice should not error."""
        migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
        sql = (migrations_dir / "001_initial.sql").read_text()
        db_conn.execute(sql)
        db_conn.execute(sql)  # Should not raise


class TestViews:
    def test_views_create_successfully(self, db_conn):
        """Verify all analytics views can be created."""
        migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
        views_path = Path(__file__).parent.parent / "ledgerscope" / "analytics" / "views.sql"

        db_conn.execute((migrations_dir / "001_initial.sql").read_text())

        sql = views_path.read_text()
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                db_conn.execute(stmt)

        # Check views exist
        views = db_conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_type = 'VIEW'"
        ).fetchall()
        view_names = {v[0] for v in views}

        expected_views = {
            "holdings", "risk_summary", "pnl_history",
            "drawdown", "benchmark_comparison", "dividend_income",
        }
        assert expected_views.issubset(view_names)

    def test_views_query_empty(self, db_conn):
        """Views should return empty results with no data."""
        migrations_dir = Path(__file__).parent.parent / "ledgerscope" / "migrations"
        views_path = Path(__file__).parent.parent / "ledgerscope" / "analytics" / "views.sql"

        db_conn.execute((migrations_dir / "001_initial.sql").read_text())
        sql = views_path.read_text()
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                db_conn.execute(stmt)

        # All views should be queryable even with no data
        for view in ["holdings", "risk_summary", "drawdown", "dividend_income"]:
            result = db_conn.execute(f"SELECT * FROM {view}").fetchall()
            assert isinstance(result, list)
