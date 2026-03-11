"""Robinhood account activity CSV parser."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ledgerscope.ingest.base import BrokerParser, generate_tx_id

# Robinhood CSV expected columns
REQUIRED_COLUMNS = {
    "activity date",
    "trans code",
    "quantity",
    "price",
}

# Map Robinhood Trans Code values to unified actions
ACTION_MAP = {
    "Buy": "BUY",
    "Sell": "SELL",
    "BUY": "BUY",
    "SELL": "SELL",
    "CDIV": "DIVIDEND",
    "DIV": "DIVIDEND",
    "Dividend": "DIVIDEND",
    "SPL": "SPLIT",
    "Split": "SPLIT",
}

# Trans codes to skip (not actual trades)
SKIP_TRANS_CODES = {
    "ACH",
    "ACATS",
    "GLD",
    "GOLD",
    "INT",
    "MINT",
    "FEE",
    "JNL",
    "MFEE",
    "SLIP",
    "CONV",
    "MA",
}


class RobinhoodParser(BrokerParser):
    """Parser for Robinhood account activity CSV exports."""

    broker_name = "robinhood"

    def validate(self, path: Path) -> None:
        """Validate the Robinhood CSV has required columns."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        df = pd.read_csv(path, nrows=0)
        cols_lower = {c.strip().lower() for c in df.columns}

        missing = [r for r in REQUIRED_COLUMNS if r not in cols_lower]
        if "instrument" not in cols_lower and "symbol" not in cols_lower:
            missing.append("instrument or symbol")

        if missing:
            raise ValueError(
                f"Robinhood CSV missing required columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

    def normalize(self, path: Path) -> pd.DataFrame:
        """Normalize Robinhood CSV to the unified transaction schema."""
        raw = pd.read_csv(path)
        raw.columns = raw.columns.str.strip()

        # Find columns case-insensitively
        col_map = {}
        for col in raw.columns:
            col_map[col.lower()] = col

        date_col = col_map.get("activity date", "Activity Date")
        # Try 'symbol' first, fallback to 'instrument'
        symbol_col = col_map.get("symbol", col_map.get("instrument", "Instrument"))
        trans_col = col_map.get("trans code", "Trans Code")
        qty_col = col_map.get("quantity", "Quantity")
        price_col = col_map.get("price", "Price")
        amount_col = col_map.get("amount", None)

        # Filter out non-trade rows
        raw["_trans_upper"] = raw[trans_col].astype(str).str.strip()
        trade_mask = ~raw["_trans_upper"].isin(SKIP_TRANS_CODES)
        raw = raw[trade_mask].copy()

        if raw.empty:
            return pd.DataFrame(
                columns=[
                    "id", "broker", "trade_date", "settle_date", "symbol",
                    "isin", "action", "quantity", "price", "fees",
                    "currency", "exchange", "notes",
                ]
            )

        # Map actions
        raw["_action"] = raw["_trans_upper"].map(ACTION_MAP)
        # Drop rows with unmapped trans codes
        raw = raw[raw["_action"].notna()].copy()

        df = pd.DataFrame()
        df["symbol"] = raw[symbol_col].astype(str).str.strip().str.upper()
        # Robinhood uses MM/DD/YYYY format
        df["trade_date"] = pd.to_datetime(
            raw[date_col], format="mixed", dayfirst=False
        ).dt.date
        df["action"] = raw["_action"].values
        df["quantity"] = (
            pd.to_numeric(raw[qty_col], errors="coerce").fillna(0).abs()
        )
        # Robinhood price may have $ prefix
        price_series = raw[price_col].astype(str).str.replace(
            r"[\$,]", "", regex=True
        )
        df["price"] = pd.to_numeric(price_series, errors="coerce").fillna(0)

        df["fees"] = 0.0  # Robinhood is commission-free
        df["broker"] = self.broker_name
        df["settle_date"] = None
        df["isin"] = None
        df["currency"] = "USD"
        df["exchange"] = "US"
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
