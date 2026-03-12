"""Abstract base class for broker CSV parsers."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

import duckdb
import pandas as pd

from ledgerscope.errors import DataIngestionError, ValidationError
from ledgerscope.logging import get_logger

logger = get_logger(__name__)


def generate_tx_id(
    broker: str,
    trade_date: str,
    symbol: str,
    quantity: float,
    price: float,
) -> str:
    """Generate a deterministic transaction ID from key fields.

    Uses SHA256 hash to ensure re-importing the same file
    produces no duplicates.
    """
    raw = f"{broker}|{trade_date}|{symbol}|{quantity}|{price}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class BrokerParser(ABC):
    """Abstract base class that every broker adapter must implement."""

    broker_name: str = ""

    @abstractmethod
    def validate(self, path: Path) -> None:
        """Validate that the CSV file has the expected columns.

        Raises:
            ValueError: If required columns are missing.
            FileNotFoundError: If the file does not exist.
        """
        ...

    @abstractmethod
    def normalize(self, path: Path) -> pd.DataFrame:
        """Read the CSV and return a DataFrame with the unified schema.

        Returns a DataFrame with columns:
            id, broker, trade_date, settle_date, symbol, isin, action,
            quantity, price, fees, currency, exchange, notes
        """
        ...

    def to_transactions(
        self, path: Path, conn: duckdb.DuckDBPyConnection
    ) -> int:
        """Validate, normalize, and write transactions to DuckDB.

        Returns the number of rows inserted.
        """
        logger.info(f"Processing {self.broker_name} file: {path}")
        
        try:
            self.validate(path)
        except Exception as e:
            logger.error(f"Validation failed for {path}: {e}")
            raise ValidationError(f"Failed to validate {self.broker_name} file") from e
        
        try:
            df = self.normalize(path)
        except Exception as e:
            logger.error(f"Normalization failed for {path}: {e}")
            raise DataIngestionError(f"Failed to normalize {self.broker_name} file") from e

        if df.empty:
            logger.warning(f"No transactions found in {path}")
            return 0

        logger.debug(f"Normalized {len(df)} transactions from {path}")

        try:
            # Use INSERT OR IGNORE for idempotent inserts
            # Register the DataFrame as a temporary view and insert
            conn.register("_staging", df)
            conn.execute("""
                INSERT OR IGNORE INTO transactions
                SELECT
                    id, broker, trade_date, settle_date, symbol, isin,
                    action, quantity, price, fees, currency, exchange,
                    notes, NOW() as imported_at
                FROM _staging
            """)
            conn.unregister("_staging")
            
            logger.info(f"Successfully inserted {len(df)} transactions from {path}")
            return len(df)
        except Exception as e:
            logger.error(f"Failed to insert transactions into database: {e}")
            raise DataIngestionError(f"Database insertion failed") from e
