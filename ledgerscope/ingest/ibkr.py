"""Interactive Brokers (IBKR) Flex Query CSV parser."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ledgerscope.ingest.base import BrokerParser, generate_tx_id

# IBKR Trades section expected columns
REQUIRED_COLUMNS = {
    "symbol",
    "quantity",
}

# Asset categories to include (skip forex, options, etc.)
VALID_ASSET_CATEGORIES = {"STK", "STOCK", "EQUITY"}

# IBKR action/side mapping
ACTION_MAP = {
    "BOT": "BUY",
    "SLD": "SELL",
    "BUY": "BUY",
    "SELL": "SELL",
}


class IBKRParser(BrokerParser):
    """Parser for IBKR Flex Query CSV exports."""

    broker_name = "ibkr"

    def _extract_trades_section(self, path: Path) -> pd.DataFrame:
        """Extract only the Trades section from the IBKR CSV.

        IBKR CSVs have multiple sections with header rows.
        We look for rows where the first column is 'Trades' and
        the second column is 'Data'.
        """
        rows = []
        header = None

        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3:
                    continue

                section = parts[0].strip().strip('"')
                row_type = parts[1].strip().strip('"')

                if section == "Trades" and row_type == "Header":
                    header = [
                        p.strip().strip('"') for p in parts[2:]
                    ]
                elif section == "Trades" and row_type == "Data" and header:
                    values = [p.strip().strip('"') for p in parts[2:]]
                    # Pad or trim to match header length
                    if len(values) < len(header):
                        values.extend([""] * (len(header) - len(values)))
                    elif len(values) > len(header):
                        values = values[: len(header)]
                    rows.append(values)

        if header and rows:
            return pd.DataFrame(rows, columns=header)

        # Fallback: try reading as a plain CSV (simpler IBKR exports)
        return pd.read_csv(path)

    def validate(self, path: Path) -> None:
        """Validate the IBKR CSV has trade data."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        df = self._extract_trades_section(path)
        cols_lower = {c.strip().lower() for c in df.columns}

        missing = [r for r in REQUIRED_COLUMNS if r not in cols_lower]
        if "datetime" not in cols_lower and "tradedate" not in cols_lower:
            missing.append("datetime or tradedate")
        if "tradeprice" not in cols_lower and "price" not in cols_lower and "t. price" not in cols_lower:
            missing.append("tradeprice or price")

        if missing:
            raise ValueError(
                f"IBKR CSV missing required columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

    def normalize(self, path: Path) -> pd.DataFrame:
        """Normalize IBKR CSV to the unified transaction schema."""
        raw = self._extract_trades_section(path)
        raw.columns = raw.columns.str.strip()

        # Build case-insensitive column map
        col_map = {}
        for col in raw.columns:
            col_map[col.lower()] = col

        symbol_col = col_map.get("symbol", "Symbol")
        date_col = col_map.get("datetime", col_map.get("tradedate", "DateTime"))
        qty_col = col_map.get("quantity", "Quantity")
        price_col = col_map.get("tradeprice", col_map.get("t. price", col_map.get("price", "TradePrice")))
        comm_col = col_map.get("ibcommission", col_map.get("commission", None))
        currency_col = col_map.get("currencyprimary", col_map.get("currency", None))
        asset_col = col_map.get("assetcategory", col_map.get("asset category", col_map.get("assetclass", None)))
        side_col = col_map.get("buysell", col_map.get("buy/sell", col_map.get("side", None)))

        # Filter to stock trades only
        if asset_col and asset_col in raw.columns:
            raw = raw[
                raw[asset_col].astype(str).str.strip().str.upper().isin(
                    VALID_ASSET_CATEGORIES
                )
            ].copy()

        # Exclude summary/total rows
        if "levelofdetail" in col_map:
            ld_col = col_map["levelofdetail"]
            raw = raw[raw[ld_col].astype(str).str.strip() != "SUMMARY"].copy()

        if raw.empty:
            return pd.DataFrame(
                columns=[
                    "id", "broker", "trade_date", "settle_date", "symbol",
                    "isin", "action", "quantity", "price", "fees",
                    "currency", "exchange", "notes",
                ]
            )

        df = pd.DataFrame()
        df["symbol"] = raw[symbol_col].astype(str).str.strip().str.upper()
        df["trade_date"] = pd.to_datetime(
            raw[date_col], format="mixed"
        ).dt.date
        df["quantity"] = (
            pd.to_numeric(raw[qty_col], errors="coerce").fillna(0).abs()
        )
        df["price"] = pd.to_numeric(
            raw[price_col], errors="coerce"
        ).fillna(0)

        # Determine action from buy/sell column or qty sign
        if side_col and side_col in raw.columns:
            df["action"] = (
                raw[side_col]
                .astype(str)
                .str.strip()
                .str.upper()
                .map(ACTION_MAP)
                .fillna("BUY")
            )
        else:
            # Positive qty = BUY, negative = SELL
            raw_qty = pd.to_numeric(raw[qty_col], errors="coerce").fillna(0)
            df["action"] = raw_qty.apply(
                lambda q: "BUY" if q >= 0 else "SELL"
            )

        # Fees from commission column (IBKR commissions are negative)
        if comm_col and comm_col in raw.columns:
            df["fees"] = (
                pd.to_numeric(raw[comm_col], errors="coerce")
                .fillna(0)
                .abs()
            )
        else:
            df["fees"] = 0.0

        # Currency
        if currency_col and currency_col in raw.columns:
            df["currency"] = raw[currency_col].astype(str).str.strip().str.upper()
        else:
            df["currency"] = "USD"

        df["broker"] = self.broker_name
        df["settle_date"] = None
        df["isin"] = None
        df["exchange"] = None
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
