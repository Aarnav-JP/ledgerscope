# Contributing to LedgerScope

Thank you for your interest in LedgerScope! As an open-source project, we rely on community contributions to support more brokers and add new analytics capabilities.

## Good First Issues
If you're looking to help out, try searching our GitHub issue tracker for labels titled `good first issue`! This is the fastest way to get your first pull request merged into LedgerScope.

## How to Add a New Broker Parser

Adding support for a new brokerage requires creating a simple parser class that inherits from `BrokerParser`. The data pipeline and SQL layer remain entirely unchanged.

1. **Create the Parser File:** Create a new file in `ledgerscope/ingest/mybroker.py`.
2. **Implement the Class:**
```python
import pandas as pd
from .base import BrokerParser

class MyBrokerParser(BrokerParser):
    def validate(self, df: pd.DataFrame) -> None:
        required = ["Date", "Ticker", "Qty", "Price", "Action"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
            
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        # Create a new normalized DataFrame mapped to LedgerScope schema
        normalized = pd.DataFrame()
        normalized["trade_date"] = pd.to_datetime(df["Date"])
        normalized["symbol"] = df["Ticker"]
        normalized["action"] = df["Action"].str.upper()
        normalized["quantity"] = df["Qty"].astype(float)
        normalized["price"] = df["Price"].astype(float)
        normalized["broker"] = "mybroker"
        return normalized
```
3. **Register the Parser:** Open `ledgerscope/ingest/__init__.py` and add logic to map your broker's name string to `MyBrokerParser`.
4. **Write Tests:** Add a test case with a sample CSV file to `tests/test_ingest.py` representing a fake brokerage export to ensure changes are stable over time.

## Setting Up Your Development Environment

1. Clone the repository: `git clone https://github.com/yourusername/ledgerscope.git`
2. Install dependencies with pip: `pip install -e ".[dev]"`
3. Install frontend Node modules: `cd web && npm install`
4. Make changes and verify tests pass with Pytest: `pytest tests/`
5. Submit a pull request on GitHub! Make sure your PR description clearly outlines the changes made.
