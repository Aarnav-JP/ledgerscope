"""SQL-native backtesting engine.

Users write trading strategies as SQL queries that return
(date, symbol, signal) rows. LedgerScope simulates trading
and calculates performance statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import duckdb


@dataclass
class BacktestResult:
    """Results from a backtest run."""

    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: Optional[float]
    max_drawdown_pct: float
    win_rate_pct: float
    num_trades: int
    equity_curve: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_value": round(self.final_value, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "annualized_return_pct": round(self.annualized_return_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 4) if self.sharpe_ratio else None,
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "win_rate_pct": round(self.win_rate_pct, 2),
            "num_trades": self.num_trades,
            "equity_curve": self.equity_curve,
        }


def _calculate_sharpe(returns: list[float], risk_free_daily: float = 0.0) -> Optional[float]:
    """Calculate annualized Sharpe ratio from daily returns."""
    if len(returns) < 2:
        return None

    import statistics

    excess = [r - risk_free_daily for r in returns]
    mean_r = statistics.mean(excess)
    std_r = statistics.stdev(excess)

    if std_r == 0:
        return None

    return (mean_r / std_r) * (252 ** 0.5)


def _calculate_max_drawdown(equity_curve: list[float]) -> float:
    """Calculate maximum drawdown as a percentage from equity curve values."""
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (value - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd

    return max_dd * 100  # as percentage


def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    strategy_sql: str,
    initial_capital: float = 10_000.0,
    start_date: Optional[str] = None,
) -> BacktestResult:
    """Execute a SQL strategy and simulate trading.

    The strategy SQL must return rows with at minimum:
    - date: DATE — the trading date
    - symbol: VARCHAR — the ticker symbol
    - signal: VARCHAR — 'BUY', 'SELL', or 'HOLD'

    The simulation:
    - BUY: enter a full position at that day's closing price
    - SELL: exit the position at that day's closing price
    - HOLD: maintain current position

    Args:
        conn: DuckDB connection with prices table populated.
        strategy_sql: SQL query returning (date, symbol, signal).
        initial_capital: Starting capital for the simulation.
        start_date: Optional filter — only simulate from this date.

    Returns:
        BacktestResult with performance statistics and equity curve.
    """
    # Execute the strategy SQL
    try:
        result = conn.execute(strategy_sql)
        rows = result.fetchall()
        desc = result.description
    except Exception as e:
        raise ValueError(f"Strategy SQL error: {e}")

    if not rows:
        raise ValueError("Strategy SQL returned no rows.")

    # Map column indices
    cols = [d[0].lower() for d in desc]

    if "date" not in cols:
        raise ValueError("Strategy SQL must return a 'date' column.")
    if "symbol" not in cols:
        raise ValueError("Strategy SQL must return a 'symbol' column.")
    if "signal" not in cols:
        raise ValueError("Strategy SQL must return a 'signal' column.")

    date_idx = cols.index("date")
    symbol_idx = cols.index("symbol")
    signal_idx = cols.index("signal")

    # Sort by date
    signals = sorted(rows, key=lambda r: r[date_idx])

    # Apply start_date filter if provided
    if start_date:
        from datetime import datetime
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        signals = [s for s in signals if s[date_idx] >= start_dt]

    if not signals:
        raise ValueError("No signals after applying date filter.")

    # Get the symbol (use first row's symbol)
    symbol = str(signals[0][symbol_idx])

    # Simulate trading
    cash = initial_capital
    shares = 0.0
    position_entry_price = 0.0
    equity_values = []
    daily_returns = []
    trades = []
    prev_equity = initial_capital

    for row in signals:
        sig_date = row[date_idx]
        signal = str(row[signal_idx]).upper().strip()

        # Get close price for this date
        price_result = conn.execute(
            "SELECT close FROM prices WHERE symbol = ? AND date = ? LIMIT 1",
            [symbol, sig_date],
        ).fetchone()

        if price_result is None:
            # Try getting from the signal row itself if it has a close/price column
            if "close" in cols:
                close = float(row[cols.index("close")])
            elif "price" in cols:
                close = float(row[cols.index("price")])
            else:
                continue  # Skip days with no price data
        else:
            close = price_result[0]

        if close <= 0:
            continue

        # Execute signal
        if signal == "BUY" and shares == 0:
            # Enter position: buy as many shares as we can afford
            shares = cash / close
            position_entry_price = close
            cash = 0.0
        elif signal == "SELL" and shares > 0:
            # Exit position
            sell_value = shares * close
            profit = sell_value - (shares * position_entry_price)
            trades.append({
                "entry_price": position_entry_price,
                "exit_price": close,
                "profit": profit,
                "profitable": profit > 0,
            })
            cash = sell_value
            shares = 0.0
            position_entry_price = 0.0

        # Calculate current equity
        equity = cash + (shares * close)
        equity_values.append(equity)

        # Daily return
        if prev_equity > 0:
            daily_ret = (equity - prev_equity) / prev_equity
            daily_returns.append(daily_ret)
        prev_equity = equity

        # Record equity curve point
        equity_curve_point = {
            "date": str(sig_date),
            "equity": round(equity, 2),
            "signal": signal,
        }
        equity_values[-1] = equity  # update
        # We'll build the curve from equity_values at the end

    # Build final equity curve
    equity_curve = []
    for i, row in enumerate(signals):
        if i < len(equity_values):
            equity_curve.append({
                "date": str(row[date_idx]),
                "equity": round(equity_values[i], 2),
            })

    # Final equity (close any open position at last price)
    if shares > 0 and signals:
        last_row = signals[-1]
        last_date = last_row[date_idx]
        price_result = conn.execute(
            "SELECT close FROM prices WHERE symbol = ? AND date = ? LIMIT 1",
            [symbol, last_date],
        ).fetchone()
        if price_result:
            final_equity = cash + shares * price_result[0]
        else:
            final_equity = equity_values[-1] if equity_values else initial_capital
    else:
        final_equity = cash

    # Calculate statistics
    total_return = ((final_equity - initial_capital) / initial_capital) * 100

    # Annualized return
    if signals:
        first_date = signals[0][date_idx]
        last_date = signals[-1][date_idx]
        days = (last_date - first_date).days
        if days > 0:
            annual_return = ((final_equity / initial_capital) ** (365.0 / days) - 1) * 100
        else:
            annual_return = 0.0
    else:
        annual_return = 0.0

    # Sharpe ratio
    sharpe = _calculate_sharpe(daily_returns)

    # Max drawdown
    max_dd = _calculate_max_drawdown(equity_values) if equity_values else 0.0

    # Win rate
    num_trades = len(trades)
    if num_trades > 0:
        winning = sum(1 for t in trades if t["profitable"])
        win_rate = (winning / num_trades) * 100
    else:
        win_rate = 0.0

    return BacktestResult(
        symbol=symbol,
        start_date=str(signals[0][date_idx]) if signals else "",
        end_date=str(signals[-1][date_idx]) if signals else "",
        initial_capital=initial_capital,
        final_value=final_equity,
        total_return_pct=total_return,
        annualized_return_pct=annual_return,
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_dd,
        win_rate_pct=win_rate,
        num_trades=num_trades,
        equity_curve=equity_curve,
    )
