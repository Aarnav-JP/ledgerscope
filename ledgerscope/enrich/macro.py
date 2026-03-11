"""Macroeconomic data enrichment via FRED API and yfinance."""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd
from rich.console import Console

from ledgerscope.enrich.cache import get_macro_cache_dir, cache_path

console = Console()

# Default FRED series to fetch
FRED_SERIES = {
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
    "UNRATE": "Unemployment Rate",
    "SP500": "S&P 500 Index",
}

# Series fetched via yfinance instead of FRED
YFINANCE_SERIES = {
    "NIFTY50": {"yf_symbol": "^NSEI", "name": "NIFTY 50 Index"},
}

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def _fetch_fred_series(series_id: str, start_date: str = "2010-01-01") -> pd.DataFrame | None:
    """Fetch a series from the FRED API (no API key needed for basic access)."""
    try:
        import requests

        # FRED provides CSV downloads without API key
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start_date}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        from io import StringIO
        df = pd.read_csv(StringIO(response.text))

        if df.empty:
            return None

        # FRED CSV columns are DATE and the series_id
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["date"])

        return df
    except Exception as e:
        console.print(f"[yellow]Warning: Could not fetch FRED series {series_id}: {e}[/]")
        return None


def _fetch_yfinance_series(yf_symbol: str) -> pd.DataFrame | None:
    """Fetch index data via yfinance."""
    try:
        import yfinance as yf

        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="max")

        if hist.empty:
            return None

        hist = hist.reset_index()
        df = pd.DataFrame()
        df["date"] = pd.to_datetime(hist["Date"]).dt.date
        df["value"] = hist["Close"]
        return df
    except Exception as e:
        console.print(f"[yellow]Warning: Could not fetch {yf_symbol}: {e}[/]")
        return None


def _insert_macro(
    conn: duckdb.DuckDBPyConnection,
    series_id: str,
    series_name: str,
    df: pd.DataFrame,
) -> None:
    """Insert macro data into DuckDB, ignoring duplicates."""
    df = df.copy()
    df["series_id"] = series_id
    df["series_name"] = series_name

    conn.register("_macro_staging", df)
    conn.execute("""
        INSERT OR IGNORE INTO macro_data (series_id, date, value, series_name)
        SELECT series_id, date, value, series_name
        FROM _macro_staging
    """)
    conn.unregister("_macro_staging")


def fetch_macro(
    conn: duckdb.DuckDBPyConnection, refresh: bool = False
) -> int:
    """Fetch macroeconomic data from FRED and yfinance.

    Returns:
        Number of series successfully fetched.
    """
    cache_dir = get_macro_cache_dir()
    fetched = 0

    # Fetch FRED series
    for series_id, series_name in FRED_SERIES.items():
        cp = cache_path(series_id, cache_dir)

        if not refresh and cp.exists():
            df = pd.read_parquet(cp)
        else:
            df = _fetch_fred_series(series_id)
            if df is not None and not df.empty:
                df.to_parquet(cp, index=False)

        if df is not None and not df.empty:
            _insert_macro(conn, series_id, series_name, df)
            fetched += 1
            console.print(f"  [dim]✓ {series_id}: {series_name}[/]")

    # Fetch yfinance series
    for series_id, info in YFINANCE_SERIES.items():
        cp = cache_path(series_id, cache_dir)

        if not refresh and cp.exists():
            df = pd.read_parquet(cp)
        else:
            df = _fetch_yfinance_series(info["yf_symbol"])
            if df is not None and not df.empty:
                df.to_parquet(cp, index=False)

        if df is not None and not df.empty:
            _insert_macro(conn, series_id, info["name"], df)
            fetched += 1
            console.print(f"  [dim]✓ {series_id}: {info['name']}[/]")

    total = len(FRED_SERIES) + len(YFINANCE_SERIES)
    console.print(
        f"[green]✓[/] Fetched {fetched}/{total} macro series"
    )
    return fetched
