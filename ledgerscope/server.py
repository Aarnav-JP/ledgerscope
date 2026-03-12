"""FastAPI server exposing LedgerScope analytics as REST endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ledgerscope.config import get_config
from ledgerscope.currency import CurrencyConverter
from ledgerscope.db import init_db
from ledgerscope.logging import get_logger, get_log_path
from ledgerscope.analytics.risk import (
    get_holdings,
    get_risk_summary,
    get_pnl_history,
    get_drawdown,
    get_benchmark,
    get_dividends,
    get_portfolio_summary,
)
from ledgerscope.analytics.backtest import run_backtest

logger = get_logger(__name__)

app = FastAPI(
    title="LedgerScope API",
    description="SQL-native portfolio risk analytics",
    version="0.1.0",
)

# Allow CORS for the web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_conn():
    """Get an initialized DB connection."""
    return init_db(read_only=True)


# ── Holdings ─────────────────────────────────────────────────────

@app.get("/api/holdings")
def api_holdings():
    """Return current portfolio holdings."""
    conn = _get_conn()
    holdings = get_holdings(conn)
    return [
        {
            "symbol": h.symbol,
            "shares": h.shares,
            "avg_cost": h.avg_cost,
            "last_trade_date": h.last_trade_date,
        }
        for h in holdings
    ]


# ── Risk Summary ────────────────────────────────────────────────

@app.get("/api/risk")
def api_risk():
    """Return risk metrics for all holdings."""
    conn = _get_conn()
    metrics = get_risk_summary(conn)
    return [
        {
            "symbol": m.symbol,
            "shares": m.shares,
            "avg_cost": m.avg_cost,
            "sharpe": m.sharpe,
            "annual_vol": m.annual_vol,
            "worst_day": m.worst_day,
            "annual_return": m.annual_return,
            "trading_days": m.trading_days,
        }
        for m in metrics
    ]


# ── P&L History ──────────────────────────────────────────────────

@app.get("/api/pnl")
def api_pnl(symbol: Optional[str] = Query(None)):
    """Return P&L history, optionally filtered by symbol."""
    conn = _get_conn()
    records = get_pnl_history(conn, symbol=symbol)
    return [
        {
            "symbol": r.symbol,
            "date": r.date,
            "current_price": r.current_price,
            "shares": r.shares,
            "cost_basis": r.cost_basis,
            "unrealized_pnl": r.unrealized_pnl,
            "realized_pnl": r.realized_pnl,
            "market_value": r.market_value,
        }
        for r in records
    ]


# ── Drawdown ─────────────────────────────────────────────────────

@app.get("/api/drawdown")
def api_drawdown():
    """Return max drawdown per symbol."""
    conn = _get_conn()
    records = get_drawdown(conn)
    return [
        {
            "symbol": r.symbol,
            "max_drawdown": r.max_drawdown,
            "max_drawdown_date": r.max_drawdown_date,
        }
        for r in records
    ]


# ── Benchmark Comparison ────────────────────────────────────────

@app.get("/api/benchmark")
def api_benchmark():
    """Return benchmark comparison for all holdings."""
    conn = _get_conn()
    records = get_benchmark(conn)
    return [
        {
            "symbol": r.symbol,
            "correlation": r.correlation,
            "beta": r.beta,
            "alpha": r.alpha,
            "common_days": r.common_days,
        }
        for r in records
    ]


# ── Dividends ────────────────────────────────────────────────────

@app.get("/api/dividends")
def api_dividends():
    """Return dividend income history."""
    conn = _get_conn()
    records = get_dividends(conn)
    return [
        {
            "symbol": r.symbol,
            "year": r.year,
            "annual_dividend": r.annual_dividend,
            "cumulative_dividend": r.cumulative_dividend,
            "yield_on_cost_pct": r.yield_on_cost_pct,
        }
        for r in records
    ]


# ── Portfolio Summary ────────────────────────────────────────────

@app.get("/api/summary")
def api_summary():
    """Return portfolio-level summary statistics."""
    conn = _get_conn()
    s = get_portfolio_summary(conn)
    return {
        "total_value": s.total_value,
        "total_cost": s.total_cost,
        "total_pnl": s.total_pnl,
        "total_pnl_pct": s.total_pnl_pct,
        "portfolio_sharpe": s.portfolio_sharpe,
        "num_holdings": s.num_holdings,
    }


# ── Configuration ────────────────────────────────────────────────

@app.get("/api/config")
def api_config():
    """Return current configuration (excluding sensitive API keys)."""
    config = get_config()
    logger.info("Configuration requested via API")
    
    return {
        "general": {
            "base_currency": config.base_currency,
            "risk_free_rate": config.risk_free_rate,
            "log_level": config.log_level,
        },
        "data": {
            "cache_expiry_days": config.cache_expiry_days,
            "retry_attempts": config.retry_attempts,
        },
        "currency": {
            "auto_convert": config.auto_convert_currency,
        },
        "display": config.get_section("display"),
    }


@app.get("/api/currencies")
def api_currencies():
    """Return list of currencies in portfolio and exchange rates."""
    conn = _get_conn()
    config = get_config()
    
    try:
        # Check if exchange_rates table exists (read-only mode can't create it)
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'exchange_rates'"
        ).fetchall()
        
        if not tables:
            # Table doesn't exist, return empty response
            logger.warning("exchange_rates table does not exist. Run 'ledgerscope ingest' first.")
            return {
                "base_currency": config.base_currency,
                "currencies": [],
                "exchange_rates": {},
            }
        
        # Get currencies from portfolio
        currencies_query = conn.execute("""
            SELECT DISTINCT currency 
            FROM transactions 
            WHERE currency IS NOT NULL
            ORDER BY currency
        """).fetchall()
        currencies = [row[0] for row in currencies_query] if currencies_query else []
        
        # Get latest exchange rates for each currency
        rates = {}
        for currency in currencies:
            if currency != config.base_currency:
                try:
                    rate_query = conn.execute("""
                        SELECT rate FROM exchange_rates
                        WHERE from_currency = ? AND to_currency = ?
                        ORDER BY date DESC LIMIT 1
                    """, [currency, config.base_currency]).fetchone()
                    
                    if rate_query:
                        rates[currency] = rate_query[0]
                    else:
                        rates[currency] = None
                except Exception as e:
                    logger.error(f"Error fetching rate for {currency}: {e}")
                    rates[currency] = None
        
        return {
            "base_currency": config.base_currency,
            "currencies": currencies,
            "exchange_rates": rates,
        }
    except Exception as e:
        logger.error(f"Failed to fetch currencies: {e}")
        raise HTTPException(status_code=500, detail=f"Currency fetch error: {e}")


@app.get("/api/logs")
def api_logs(lines: int = Query(100, ge=1, le=1000)):
    """Return recent log entries."""
    try:
        log_path = get_log_path()
        if not log_path.exists():
            return {"logs": []}
        
        with open(log_path, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
        
        return {
            "log_file": str(log_path),
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
            "logs": [line.strip() for line in recent_lines]
        }
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        raise HTTPException(status_code=500, detail=f"Log read error: {e}")


# ── Backtest ─────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    strategy_sql: str
    initial_capital: float = 10_000.0
    start_date: Optional[str] = None


@app.post("/api/backtest")
def api_backtest(req: BacktestRequest):
    """Run a SQL-native backtest strategy."""
    conn = _get_conn()
    try:
        result = run_backtest(
            conn=conn,
            strategy_sql=req.strategy_sql,
            initial_capital=req.initial_capital,
            start_date=req.start_date,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest error: {e}")


# ── Report PDF ───────────────────────────────────────────────────

@app.get("/api/report/pdf")
def api_report_pdf():
    """Generate and stream a PDF portfolio report."""
    from fastapi.responses import FileResponse
    from ledgerscope.report.pdf import generate_pdf_report
    
    conn = _get_conn()
    try:
        pdf_path = generate_pdf_report(conn)
        return FileResponse(
            path=pdf_path, 
            filename="portfolio_report.pdf", 
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {e}",
        )
