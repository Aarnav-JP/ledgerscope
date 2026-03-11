"""Disk caching utilities for market data parquet files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def get_cache_dir() -> Path:
    """Return (and create) the ~/.ledgerscope/cache/ directory."""
    cache_dir = Path.home() / ".ledgerscope" / "cache" / "prices"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_macro_cache_dir() -> Path:
    """Return (and create) the macro data cache directory."""
    cache_dir = Path.home() / ".ledgerscope" / "cache" / "macro"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def cache_path(symbol: str, cache_dir: Path | None = None) -> Path:
    """Return the parquet cache file path for a symbol."""
    if cache_dir is None:
        cache_dir = get_cache_dir()
    # Sanitize symbol for filename (e.g., ^NSEI -> _NSEI)
    safe_name = symbol.replace("^", "_").replace("/", "_").replace(".", "_")
    return cache_dir / f"{safe_name}.parquet"


def is_cached(symbol: str, cache_dir: Path | None = None) -> bool:
    """Check if a symbol has cached price data."""
    return cache_path(symbol, cache_dir).exists()


def read_cache(symbol: str, cache_dir: Path | None = None) -> pd.DataFrame:
    """Read cached parquet data for a symbol."""
    path = cache_path(symbol, cache_dir)
    if not path.exists():
        raise FileNotFoundError(f"No cached data for {symbol}")
    return pd.read_parquet(path)


def write_cache(
    symbol: str, df: pd.DataFrame, cache_dir: Path | None = None
) -> None:
    """Write DataFrame to parquet cache for a symbol."""
    path = cache_path(symbol, cache_dir)
    df.to_parquet(path, index=False)
