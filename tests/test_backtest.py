"""Tests for the SQL-native backtesting engine."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import duckdb
import pandas as pd
import pytest

from ledgerscope.analytics.backtest import run_backtest, BacktestResult

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def bt_db():
    """Create an in-memory DB with schema, views, and 1 year of mock price data."""
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

    # Insert mock AAPL prices for 2023 (252 trading days with realistic movement)
    random.seed(42)
    base_price = 150.0
    prices = []
    current = date(2023, 1, 1)

    for _ in range(365):
        if current.weekday() < 5:
            change = random.gauss(0.0003, 0.015)
            base_price *= (1 + change)
            prices.append({
                "symbol": "AAPL",
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
    conn.execute("INSERT INTO prices SELECT * FROM _p")
    conn.unregister("_p")

    yield conn
    conn.close()


class TestBacktestEngine:
    def test_simple_buy_and_hold(self, bt_db):
        """A strategy that buys on day 1 and never sells should track the price."""
        strategy = """
            SELECT date, 'AAPL' as symbol,
                CASE WHEN ROW_NUMBER() OVER (ORDER BY date) = 1 THEN 'BUY'
                     ELSE 'HOLD'
                END as signal
            FROM prices WHERE symbol = 'AAPL'
        """
        result = run_backtest(bt_db, strategy)

        assert isinstance(result, BacktestResult)
        assert result.symbol == "AAPL"
        assert result.num_trades == 0  # no completed round-trips
        assert result.final_value > 0
        assert len(result.equity_curve) > 200  # ~252 trading days

    def test_always_hold(self, bt_db):
        """A HOLD-only strategy should keep capital unchanged."""
        strategy = """
            SELECT date, 'AAPL' as symbol, 'HOLD' as signal
            FROM prices WHERE symbol = 'AAPL'
        """
        result = run_backtest(bt_db, strategy, initial_capital=10000)

        assert result.final_value == pytest.approx(10000, abs=0.01)
        assert result.total_return_pct == pytest.approx(0, abs=0.01)
        assert result.num_trades == 0

    def test_moving_average_crossover(self, bt_db):
        """Test a classic MA crossover strategy returns valid metrics."""
        strategy = """
            SELECT date, 'AAPL' as symbol,
                CASE
                    WHEN AVG(close) OVER (ORDER BY date ROWS 9 PRECEDING) >
                         AVG(close) OVER (ORDER BY date ROWS 29 PRECEDING)
                    THEN 'BUY'
                    ELSE 'SELL'
                END as signal
            FROM prices WHERE symbol = 'AAPL'
            ORDER BY date
        """
        result = run_backtest(bt_db, strategy)

        assert isinstance(result, BacktestResult)
        assert result.num_trades > 0
        assert 0 <= result.win_rate_pct <= 100
        assert result.max_drawdown_pct <= 0  # drawdown is zero or negative
        assert result.sharpe_ratio is not None

    def test_backtest_result_to_dict(self, bt_db):
        """BacktestResult.to_dict() should return a serializable dict."""
        strategy = """
            SELECT date, 'AAPL' as symbol, 'HOLD' as signal
            FROM prices WHERE symbol = 'AAPL'
        """
        result = run_backtest(bt_db, strategy)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "symbol" in d
        assert "total_return_pct" in d
        assert "equity_curve" in d
        assert isinstance(d["equity_curve"], list)

    def test_invalid_strategy_no_signal(self, bt_db):
        """Strategy missing 'signal' column should raise ValueError."""
        strategy = "SELECT date, 'AAPL' as symbol FROM prices WHERE symbol = 'AAPL'"
        with pytest.raises(ValueError, match="signal"):
            run_backtest(bt_db, strategy)

    def test_invalid_strategy_bad_sql(self, bt_db):
        """Invalid SQL should raise ValueError."""
        with pytest.raises(ValueError, match="Strategy SQL error"):
            run_backtest(bt_db, "SELECT * FROM nonexistent_table")

    def test_start_date_filter(self, bt_db):
        """Start date filter should limit the simulation period."""
        strategy = """
            SELECT date, 'AAPL' as symbol,
                CASE WHEN ROW_NUMBER() OVER (ORDER BY date) = 1 THEN 'BUY'
                     ELSE 'HOLD'
                END as signal
            FROM prices WHERE symbol = 'AAPL'
        """
        result_full = run_backtest(bt_db, strategy)
        result_late = run_backtest(bt_db, strategy, start_date="2023-06-01")

        # Late start should have fewer equity curve points
        assert len(result_late.equity_curve) < len(result_full.equity_curve)

    def test_custom_capital(self, bt_db):
        """Custom initial capital should be reflected in results."""
        strategy = """
            SELECT date, 'AAPL' as symbol, 'HOLD' as signal
            FROM prices WHERE symbol = 'AAPL'
        """
        result = run_backtest(bt_db, strategy, initial_capital=50000)
        assert result.initial_capital == 50000
        assert result.final_value == pytest.approx(50000, abs=0.01)
