"""Market price enrichment via yfinance with parquet caching."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pandas as pd
from rich.console import Console
from rich.progress import Progress

from ledgerscope.enrich.cache import (
    get_cache_dir,
    is_cached,
    read_cache,
    write_cache,
)

console = Console()


def _get_symbols_to_fetch(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    """Get distinct symbols from transactions with their metadata."""
    result = conn.execute("""
        SELECT DISTINCT
            symbol,
            exchange,
            MIN(trade_date) as earliest_date
        FROM transactions
        GROUP BY symbol, exchange
    """).fetchall()

    symbols = []
    for row in result:
        symbol, exchange, earliest = row
        # For NSE stocks, append .NS suffix for yfinance
        yf_symbol = symbol
        if exchange and exchange.upper() in ("NSE", "BSE"):
            if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
                yf_symbol = f"{symbol}.NS"
        symbols.append({
            "symbol": symbol,
            "yf_symbol": yf_symbol,
            "earliest_date": earliest,
        })
    return symbols


def _download_prices(yf_symbol: str, start_date: date) -> pd.DataFrame | None:
    """Download OHLCV data from yfinance for a single symbol."""
    try:
        import yfinance as yf

        # Fetch from a bit before the earliest trade to ensure coverage
        start = start_date - timedelta(days=30)
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(start=start.isoformat(), end=date.today().isoformat())

        if hist.empty:
            return None

        hist = hist.reset_index()
        df = pd.DataFrame()
        df["date"] = pd.to_datetime(hist["Date"]).dt.date
        df["open"] = hist["Open"]
        df["high"] = hist["High"]
        df["low"] = hist["Low"]
        df["close"] = hist["Close"]
        # Use Close as adj_close if not available
        if "Adj Close" in hist.columns:
            df["adj_close"] = hist["Adj Close"]
        else:
            df["adj_close"] = hist["Close"]
        df["volume"] = hist["Volume"].astype("int64")
        df["source"] = "yfinance"

        return df
    except Exception as e:
        console.print(f"[yellow]Warning: Could not fetch {yf_symbol}: {e}[/]")
        return None


def _insert_prices(
    conn: duckdb.DuckDBPyConnection, symbol: str, df: pd.DataFrame
) -> None:
    """Insert price data into DuckDB, ignoring duplicates."""
    df = df.copy()
    df["symbol"] = symbol

    conn.register("_price_staging", df)
    conn.execute("""
        INSERT OR IGNORE INTO prices (symbol, date, open, high, low, close, adj_close, volume, source)
        SELECT symbol, date, open, high, low, close, adj_close, volume, source
        FROM _price_staging
    """)
    conn.unregister("_price_staging")


def fetch_prices(
    conn: duckdb.DuckDBPyConnection, refresh: bool = False
) -> int:
    """Fetch historical prices for all symbols in the transactions table.

    Args:
        conn: DuckDB connection.
        refresh: If True, re-fetch even if cached data exists.

    Returns:
        Number of symbols successfully fetched.
    """
    symbols = _get_symbols_to_fetch(conn)
    if not symbols:
        console.print("[dim]No symbols found in transactions table.[/]")
        return 0

    fetched = 0
    cache_dir = get_cache_dir()

    with Progress() as progress:
        task = progress.add_task(
            "[teal]Fetching prices...", total=len(symbols)
        )

        for sym_info in symbols:
            symbol = sym_info["symbol"]
            yf_symbol = sym_info["yf_symbol"]
            earliest = sym_info["earliest_date"]

            if not refresh and is_cached(yf_symbol, cache_dir):
                # Load from cache
                df = read_cache(yf_symbol, cache_dir)
                _insert_prices(conn, symbol, df)
                fetched += 1
            else:
                # Download fresh data
                df = _download_prices(yf_symbol, earliest)
                if df is not None and not df.empty:
                    write_cache(yf_symbol, df, cache_dir)
                    _insert_prices(conn, symbol, df)
                    fetched += 1

            progress.advance(task)

    console.print(
        f"[green]✓[/] Fetched prices for {fetched}/{len(symbols)} symbols"
    )
    return fetched
