"""Zerodha tradebook CSV parser."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ledgerscope.ingest.base import BrokerParser, generate_tx_id

REQUIRED_COLUMNS = {
    "symbol",
    "trade_date",
    "trade_type",
    "quantity",
    "price",
}

# Alternative column names Zerodha may use
COLUMN_ALIASES = {
    "trade_type": ["trade_type", "type", "transaction type"],
    "price": ["price", "trade_price", "avg_price", "average price"],
    "symbol": ["symbol", "tradingsymbol", "trading_symbol", "trading symbol"],
    "trade_date": ["trade_date", "order_execution_time", "date", "order execution time"],
    "quantity": ["quantity", "filled_quantity", "filled quantity"],
}


class ZerodhaParser(BrokerParser):
    """Parser for Zerodha tradebook CSV exports."""

    broker_name = "zerodha"

    def _resolve_column(self, df: pd.DataFrame, key: str) -> str | None:
        """Find the actual column name from possible aliases."""
        aliases = COLUMN_ALIASES.get(key, [key])
        for alias in aliases:
            # Case-insensitive match
            for col in df.columns:
                if col.strip().lower() == alias.lower():
                    return col
        return None

    def validate(self, path: Path) -> None:
        """Validate the Zerodha CSV has required columns."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        df = pd.read_csv(path, nrows=0)
        # Normalize column names for checking
        cols_lower = {c.strip().lower() for c in df.columns}

        missing = []
        for required in REQUIRED_COLUMNS:
            aliases = COLUMN_ALIASES.get(required, [required])
            if not any(a.lower() in cols_lower for a in aliases):
                missing.append(required)

        if missing:
            raise ValueError(
                f"Zerodha CSV missing required columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

    def normalize(self, path: Path) -> pd.DataFrame:
        """Normalize Zerodha CSV to the unified transaction schema."""
        raw = pd.read_csv(path)
        raw.columns = raw.columns.str.strip()

        # Resolve actual column names
        symbol_col = self._resolve_column(raw, "symbol")
        date_col = self._resolve_column(raw, "trade_date")
        action_col = self._resolve_column(raw, "trade_type")
        qty_col = self._resolve_column(raw, "quantity")
        price_col = self._resolve_column(raw, "price")

        # Calculate fees: sum of brokerage + taxes + charges if available
        fee_cols = []
        for fc in ["brokerage", "taxes", "charges", "stt", "stamp_duty"]:
            for col in raw.columns:
                if col.strip().lower() == fc:
                    fee_cols.append(col)
                    break

        df = pd.DataFrame()
        df["symbol"] = raw[symbol_col].astype(str).str.strip().str.upper()
        df["trade_date"] = pd.to_datetime(raw[date_col]).dt.date
        df["action"] = raw[action_col].astype(str).str.strip().str.upper()
        df["quantity"] = pd.to_numeric(raw[qty_col], errors="coerce").fillna(0)
        df["price"] = pd.to_numeric(raw[price_col], errors="coerce").fillna(0)

        if fee_cols:
            df["fees"] = sum(
                pd.to_numeric(raw[fc], errors="coerce").fillna(0)
                for fc in fee_cols
            )
        else:
            df["fees"] = 0.0

        df["broker"] = self.broker_name
        df["settle_date"] = None
        df["isin"] = None
        df["currency"] = "INR"
        df["exchange"] = "NSE"
        df["notes"] = None

        # Generate deterministic IDs
        df["id"] = df.apply(
            lambda r: generate_tx_id(
                self.broker_name,
                str(r["trade_date"]),
                r["symbol"],
                r["quantity"],
                r["price"],
            ),
            axis=1,
        )

        return df[
            [
                "id", "broker", "trade_date", "settle_date", "symbol",
                "isin", "action", "quantity", "price", "fees",
                "currency", "exchange", "notes",
            ]
        ]
