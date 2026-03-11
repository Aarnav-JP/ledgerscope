"""Python wrappers around the SQL analytics views.

Provides typed dataclasses and convenience functions to consume
view data from Python code (used by TUI, web dashboard, PDF).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import duckdb


@dataclass
class Holding:
    symbol: str
    shares: float
    avg_cost: float
    last_trade_date: str


@dataclass
class RiskMetric:
    symbol: str
    shares: float
    avg_cost: float
    sharpe: Optional[float]
    annual_vol: Optional[float]
    worst_day: Optional[float]
    annual_return: Optional[float]
    trading_days: Optional[int]


@dataclass
class PnLRecord:
    symbol: str
    date: str
    current_price: float
    shares: float
    cost_basis: float
    unrealized_pnl: float
    realized_pnl: float
    market_value: float


@dataclass
class DrawdownRecord:
    symbol: str
    max_drawdown: float
    max_drawdown_date: Optional[str]


@dataclass
class BenchmarkRecord:
    symbol: str
    correlation: Optional[float]
    beta: Optional[float]
    alpha: Optional[float]
    common_days: int


@dataclass
class DividendRecord:
    symbol: str
    year: int
    annual_dividend: float
    cumulative_dividend: float
    yield_on_cost_pct: Optional[float]


@dataclass
class PortfolioSummary:
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    portfolio_sharpe: Optional[float]
    num_holdings: int


def get_holdings(conn: duckdb.DuckDBPyConnection) -> list[Holding]:
    """Get current portfolio holdings."""
    rows = conn.execute("SELECT * FROM holdings").fetchall()
    desc = conn.description
    cols = [d[0] for d in desc] if desc else []
    return [
        Holding(
            symbol=row[cols.index("symbol")],
            shares=row[cols.index("shares")],
            avg_cost=row[cols.index("avg_cost")] or 0,
            last_trade_date=str(row[cols.index("last_trade_date")]),
        )
        for row in rows
    ]


def get_risk_summary(conn: duckdb.DuckDBPyConnection) -> list[RiskMetric]:
    """Get risk metrics for all holdings."""
    rows = conn.execute("SELECT * FROM risk_summary").fetchall()
    desc = conn.description
    cols = [d[0] for d in desc] if desc else []
    return [
        RiskMetric(
            symbol=row[cols.index("symbol")],
            shares=row[cols.index("shares")],
            avg_cost=row[cols.index("avg_cost")] or 0,
            sharpe=row[cols.index("sharpe")],
            annual_vol=row[cols.index("annual_vol")],
            worst_day=row[cols.index("worst_day")],
            annual_return=row[cols.index("annual_return")],
            trading_days=row[cols.index("trading_days")],
        )
        for row in rows
    ]


def get_pnl_history(
    conn: duckdb.DuckDBPyConnection, symbol: str | None = None
) -> list[PnLRecord]:
    """Get P&L history, optionally filtered by symbol."""
    query = "SELECT * FROM pnl_history"
    params = []
    if symbol:
        query += " WHERE symbol = ?"
        params.append(symbol)
    query += " ORDER BY date DESC"

    rows = conn.execute(query, params).fetchall()
    desc = conn.description
    cols = [d[0] for d in desc] if desc else []
    return [
        PnLRecord(
            symbol=row[cols.index("symbol")],
            date=str(row[cols.index("date")]),
            current_price=row[cols.index("current_price")] or 0,
            shares=row[cols.index("shares")] or 0,
            cost_basis=row[cols.index("cost_basis")] or 0,
            unrealized_pnl=row[cols.index("unrealized_pnl")] or 0,
            realized_pnl=row[cols.index("realized_pnl")] or 0,
            market_value=row[cols.index("market_value")] or 0,
        )
        for row in rows
    ]


def get_drawdown(conn: duckdb.DuckDBPyConnection) -> list[DrawdownRecord]:
    """Get max drawdown per symbol."""
    rows = conn.execute("SELECT * FROM drawdown").fetchall()
    desc = conn.description
    cols = [d[0] for d in desc] if desc else []
    return [
        DrawdownRecord(
            symbol=row[cols.index("symbol")],
            max_drawdown=row[cols.index("max_drawdown")] or 0,
            max_drawdown_date=str(row[cols.index("max_drawdown_date")])
            if row[cols.index("max_drawdown_date")] else None,
        )
        for row in rows
    ]


def get_benchmark(conn: duckdb.DuckDBPyConnection) -> list[BenchmarkRecord]:
    """Get benchmark comparison for all holdings."""
    rows = conn.execute("SELECT * FROM benchmark_comparison").fetchall()
    desc = conn.description
    cols = [d[0] for d in desc] if desc else []
    return [
        BenchmarkRecord(
            symbol=row[cols.index("symbol")],
            correlation=row[cols.index("correlation")],
            beta=row[cols.index("beta")],
            alpha=row[cols.index("alpha")],
            common_days=row[cols.index("common_days")],
        )
        for row in rows
    ]


def get_dividends(conn: duckdb.DuckDBPyConnection) -> list[DividendRecord]:
    """Get dividend income history."""
    rows = conn.execute("SELECT * FROM dividend_income").fetchall()
    desc = conn.description
    cols = [d[0] for d in desc] if desc else []
    return [
        DividendRecord(
            symbol=row[cols.index("symbol")],
            year=int(row[cols.index("year")]),
            annual_dividend=row[cols.index("annual_dividend")] or 0,
            cumulative_dividend=row[cols.index("cumulative_dividend")] or 0,
            yield_on_cost_pct=row[cols.index("yield_on_cost_pct")],
        )
        for row in rows
    ]


def get_portfolio_summary(conn: duckdb.DuckDBPyConnection) -> PortfolioSummary:
    """Calculate portfolio-level summary statistics."""
    holdings = get_holdings(conn)

    if not holdings:
        return PortfolioSummary(
            total_value=0, total_cost=0, total_pnl=0,
            total_pnl_pct=0, portfolio_sharpe=None, num_holdings=0,
        )

    # Get latest prices for each holding
    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        result = conn.execute(
            "SELECT close FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            [h.symbol],
        ).fetchone()
        latest_price = result[0] if result else h.avg_cost
        total_value += h.shares * latest_price
        total_cost += h.shares * h.avg_cost

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    # Portfolio-level Sharpe (weighted average of individual Sharpes)
    risk_metrics = get_risk_summary(conn)
    weighted_sharpe = None
    if risk_metrics and total_value > 0:
        weighted_sum = 0.0
        weight_total = 0.0
        for rm in risk_metrics:
            if rm.sharpe is not None:
                result = conn.execute(
                    "SELECT close FROM prices WHERE symbol = ? ORDER BY date DESC LIMIT 1",
                    [rm.symbol],
                ).fetchone()
                price = result[0] if result else rm.avg_cost
                weight = rm.shares * price / total_value
                weighted_sum += rm.sharpe * weight
                weight_total += weight
        if weight_total > 0:
            weighted_sharpe = round(weighted_sum / weight_total, 4)

    return PortfolioSummary(
        total_value=round(total_value, 2),
        total_cost=round(total_cost, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        portfolio_sharpe=weighted_sharpe,
        num_holdings=len(holdings),
    )
