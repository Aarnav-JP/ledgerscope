"""Tests for multi-currency support."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import duckdb
import pytest

from ledgerscope.currency import CurrencyConverter


@pytest.fixture
def in_memory_db():
    """Create an in-memory DuckDB connection with sample data."""
    conn = duckdb.connect(":memory:")
    
    # Create transactions table
    conn.execute("""
        CREATE TABLE transactions (
            id VARCHAR PRIMARY KEY,
            broker VARCHAR,
            trade_date DATE,
            settle_date DATE,
            symbol VARCHAR,
            isin VARCHAR,
            action VARCHAR,
            quantity DOUBLE,
            price DOUBLE,
            fees DOUBLE,
            currency VARCHAR,
            exchange VARCHAR,
            notes TEXT,
            imported_at TIMESTAMP
        )
    """)
    
    # Insert sample transactions in different currencies
    conn.execute("""
        INSERT INTO transactions VALUES
        ('tx1', 'test', '2024-01-01', '2024-01-03', 'AAPL', NULL, 'BUY', 10, 150.0, 1.0, 'USD', 'NASDAQ', NULL, NOW()),
        ('tx2', 'test', '2024-01-02', '2024-01-04', 'RELIANCE', NULL, 'BUY', 5, 2500.0, 10.0, 'INR', 'NSE', NULL, NOW()),
        ('tx3', 'test', '2024-01-03', '2024-01-05', 'SAP', NULL, 'BUY', 3, 120.0, 2.0, 'EUR', 'XETRA', NULL, NOW())
    """)
    
    yield conn
    conn.close()


def test_currency_converter_init(in_memory_db):
    """Test CurrencyConverter initialization."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    assert converter.base_currency == "USD"
    
    # Check that exchange_rates table was created
    result = in_memory_db.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'exchange_rates'
    """).fetchone()
    
    assert result[0] == 1


def test_get_portfolio_currencies(in_memory_db):
    """Test retrieving unique currencies from portfolio."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    currencies = converter.get_portfolio_currencies()
    
    assert set(currencies) == {"USD", "INR", "EUR"}


def test_same_currency_conversion(in_memory_db):
    """Test converting amount in same currency returns original amount."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    result = converter.convert(100.0, "USD", "USD")
    
    assert result == 100.0


def test_manual_exchange_rate(in_memory_db):
    """Test conversion with manually inserted exchange rate."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    # Manually insert exchange rate
    in_memory_db.execute("""
        INSERT INTO exchange_rates (date, from_currency, to_currency, rate, source)
        VALUES ('2024-01-01', 'EUR', 'USD', 1.08, 'manual')
    """)
    
    result = converter.convert(100.0, "EUR", "USD", on_date=date(2024, 1, 1))
    
    assert result == 108.0


def test_reverse_exchange_rate(in_memory_db):
    """Test that reverse rates are calculated correctly."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    # Insert EUR to USD rate
    in_memory_db.execute("""
        INSERT INTO exchange_rates (date, from_currency, to_currency, rate, source)
        VALUES ('2024-01-01', 'EUR', 'USD', 1.08, 'manual')
    """)
    
    # Should calculate reverse rate
    result = converter.convert(108.0, "USD", "EUR", on_date=date(2024, 1, 1))
    
    assert abs(result - 100.0) < 0.01  # Allow small floating point error


def test_missing_exchange_rate_error(in_memory_db):
    """Test that missing exchange rate raises error."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    with pytest.raises(ValueError, match="No exchange rate available"):
        converter.convert(100.0, "GBP", "USD", on_date=date(2024, 1, 1))


def test_nearest_date_fallback(in_memory_db):
    """Test that nearest available date is used when exact date not found."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    # Insert rate for Jan 1
    in_memory_db.execute("""
        INSERT INTO exchange_rates (date, from_currency, to_currency, rate, source)
        VALUES ('2024-01-01', 'EUR', 'USD', 1.08, 'manual')
    """)
    
    # Request conversion for Jan 3 (should use Jan 1 rate)
    result = converter.convert(100.0, "EUR", "USD", on_date=date(2024, 1, 3))
    
    assert result == 108.0


def test_skip_base_currency_fetch(in_memory_db):
    """Test that fetching rates for base currency is skipped."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    # Should not attempt to fetch (would normally fail without network)
    # This just verifies the skip logic works
    converter.fetch_exchange_rates("USD", force_refresh=False)
    
    # No rates should be inserted for USD/USD
    result = in_memory_db.execute("""
        SELECT COUNT(*) FROM exchange_rates
        WHERE from_currency = 'USD' AND to_currency = 'USD'
    """).fetchone()
    
    assert result[0] == 0


def test_multiple_currency_conversions(in_memory_db):
    """Test converting multiple amounts in sequence."""
    converter = CurrencyConverter(in_memory_db, base_currency="USD")
    
    # Insert multiple rates
    in_memory_db.execute("""
        INSERT INTO exchange_rates (date, from_currency, to_currency, rate, source) VALUES
        ('2024-01-01', 'EUR', 'USD', 1.08, 'manual'),
        ('2024-01-01', 'GBP', 'USD', 1.25, 'manual'),
        ('2024-01-01', 'INR', 'USD', 0.012, 'manual')
    """)
    
    test_date = date(2024, 1, 1)
    
    assert converter.convert(100.0, "EUR", "USD", test_date) == 108.0
    assert converter.convert(100.0, "GBP", "USD", test_date) == 125.0
    assert converter.convert(1000.0, "INR", "USD", test_date) == 12.0
