"""Multi-currency support for LedgerScope.

Handles exchange rate fetching, caching, and currency conversion.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ledgerscope.logging import get_logger

logger = get_logger(__name__)


class CurrencyConverter:
    """Handles currency conversion with exchange rate caching."""

    def __init__(self, conn: duckdb.DuckDBPyConnection, base_currency: str = "USD"):
        """Initialize currency converter.

        Args:
            conn: DuckDB connection
            base_currency: Base currency for conversions
        """
        self.conn = conn
        self.base_currency = base_currency.upper()
        self._ensure_tables()
        logger.info(f"Initialized CurrencyConverter with base currency: {self.base_currency}")

    def _ensure_tables(self) -> None:
        """Ensure exchange_rates table exists."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS exchange_rates (
                date DATE NOT NULL,
                from_currency VARCHAR NOT NULL,
                to_currency VARCHAR NOT NULL,
                rate DOUBLE NOT NULL,
                source VARCHAR DEFAULT 'manual',
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, from_currency, to_currency)
            )
        """)
        logger.debug("Ensured exchange_rates table exists")

    def _get_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        from ledgerscope.config import get_config
        
        config = get_config()
        session = requests.Session()
        
        retries = Retry(
            total=config.retry_attempts,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def fetch_exchange_rates(
        self,
        currency: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        force_refresh: bool = False,
    ) -> None:
        """Fetch historical exchange rates for a currency.

        Args:
            currency: Currency code (e.g., 'EUR', 'INR')
            start_date: Start date for historical rates
            end_date: End date for historical rates
            force_refresh: Force re-fetch even if cached
        """
        from ledgerscope.config import get_config
        
        config = get_config()
        currency = currency.upper()
        
        # Don't fetch if currency is same as base
        if currency == self.base_currency:
            logger.debug(f"Skipping fetch for base currency: {currency}")
            return

        # Check if we already have recent data
        if not force_refresh:
            cached = self.conn.execute("""
                SELECT COUNT(*) as count, MAX(date) as latest_date
                FROM exchange_rates
                WHERE from_currency = ? AND to_currency = ?
            """, [currency, self.base_currency]).fetchone()
            
            if cached and cached[0] > 0:
                latest = cached[1]
                if isinstance(latest, str):
                    latest = datetime.strptime(latest, "%Y-%m-%d").date()
                
                cache_age_days = (date.today() - latest).days
                if cache_age_days < config.cache_expiry_days:
                    logger.info(
                        f"Using cached exchange rates for {currency}/{self.base_currency} "
                        f"(latest: {latest}, age: {cache_age_days} days)"
                    )
                    return

        logger.info(f"Fetching exchange rates for {currency}/{self.base_currency}")

        try:
            # Try to use exchangerate-api if API key provided
            api_key = config.get("api_keys", "exchangerate_api_key")
            if api_key:
                self._fetch_from_exchangerate_api(currency, start_date, end_date, api_key)
            else:
                # Fallback to free source (frankfurter.app for EU currencies)
                self._fetch_from_frankfurter(currency, start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch exchange rates for {currency}: {e}")
            # Try to use fallback rates from config
            self._try_fallback_rates(currency)

    def _fetch_from_exchangerate_api(
        self,
        currency: str,
        start_date: Optional[date],
        end_date: Optional[date],
        api_key: str,
    ) -> None:
        """Fetch from exchangerate-api.com (requires API key)."""
        from ledgerscope.config import get_config
        
        config = get_config()
        session = self._get_session()
        
        # This API provides current rates, not historical
        # For historical data, would need a different API or service
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{currency}/{self.base_currency}"
        
        try:
            response = session.get(url, timeout=config.request_timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get("result") == "success":
                rate = data.get("conversion_rate")
                today = date.today()
                
                self.conn.execute("""
                    INSERT OR REPLACE INTO exchange_rates (date, from_currency, to_currency, rate, source)
                    VALUES (?, ?, ?, ?, 'exchangerate-api')
                """, [today, currency, self.base_currency, rate])
                
                logger.info(f"Fetched current rate: 1 {currency} = {rate} {self.base_currency}")
            else:
                raise ValueError(f"API returned error: {data}")
        except Exception as e:
            logger.error(f"Failed to fetch from exchangerate-api: {e}")
            raise

    def _fetch_from_frankfurter(
        self,
        currency: str,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> None:
        """Fetch from frankfurter.app (free, no API key needed, EU currencies only)."""
        from ledgerscope.config import get_config
        
        config = get_config()
        session = self._get_session()
        
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # Frankfurter uses EUR as base, so we may need to convert
        base = "EUR" if currency != "EUR" else self.base_currency
        
        url = f"https://api.frankfurter.app/{start_date}..{end_date}"
        params = {
            "from": currency,
            "to": self.base_currency,
        }
        
        try:
            response = session.get(url, params=params, timeout=config.request_timeout)
            response.raise_for_status()
            data = response.json()
            
            rates_data = []
            for date_str, rates in data.get("rates", {}).items():
                if self.base_currency in rates:
                    rates_data.append({
                        "date": date_str,
                        "from_currency": currency,
                        "to_currency": self.base_currency,
                        "rate": rates[self.base_currency],
                        "source": "frankfurter",
                    })
            
            if rates_data:
                df = pd.DataFrame(rates_data)
                self.conn.register("_exchange_staging", df)
                self.conn.execute("""
                    INSERT OR REPLACE INTO exchange_rates (date, from_currency, to_currency, rate, source)
                    SELECT date, from_currency, to_currency, rate, source
                    FROM _exchange_staging
                """)
                self.conn.unregister("_exchange_staging")
                logger.info(f"Inserted {len(rates_data)} exchange rates for {currency}")
            else:
                raise ValueError("No rates returned from API")
        except Exception as e:
            logger.error(f"Failed to fetch from frankfurter: {e}")
            raise

    def _try_fallback_rates(self, currency: str) -> None:
        """Try to use fallback rates from configuration."""
        from ledgerscope.config import get_config
        
        config = get_config()
        fallback_rates = config.get("currency", "fallback_rates", {})
        
        rate_key = f"{currency}/{self.base_currency}"
        if rate_key in fallback_rates:
            rate = fallback_rates[rate_key]
            today = date.today()
            
            self.conn.execute("""
                INSERT OR REPLACE INTO exchange_rates (date, from_currency, to_currency, rate, source)
                VALUES (?, ?, ?, ?, 'config')
            """, [today, currency, self.base_currency, rate])
            
            logger.info(f"Using fallback rate from config: 1 {currency} = {rate} {self.base_currency}")

    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: Optional[str] = None,
        on_date: Optional[date] = None,
    ) -> float:
        """Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code (defaults to base currency)
            on_date: Date for conversion rate (defaults to today)

        Returns:
            Converted amount

        Raises:
            ValueError: If exchange rate not available
        """
        from_currency = from_currency.upper()
        to_currency = (to_currency or self.base_currency).upper()
        
        if from_currency == to_currency:
            return amount

        if on_date is None:
            on_date = date.today()

        # Try to get exact date first, then fall back to nearest date
        rate = self._get_exchange_rate(from_currency, to_currency, on_date)
        
        if rate is None:
            # Try reverse rate
            reverse_rate = self._get_exchange_rate(to_currency, from_currency, on_date)
            if reverse_rate:
                rate = 1.0 / reverse_rate
            else:
                raise ValueError(
                    f"No exchange rate available for {from_currency}/{to_currency} on {on_date}"
                )

        result = amount * rate
        logger.debug(
            f"Converted {amount:.2f} {from_currency} to {result:.2f} {to_currency} "
            f"(rate: {rate:.4f}, date: {on_date})"
        )
        return result

    def _get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        on_date: date,
    ) -> Optional[float]:
        """Get exchange rate for a specific date."""
        # Try exact date first
        result = self.conn.execute("""
            SELECT rate FROM exchange_rates
            WHERE from_currency = ? AND to_currency = ? AND date = ?
            ORDER BY fetched_at DESC
            LIMIT 1
        """, [from_currency, to_currency, on_date]).fetchone()
        
        if result:
            return result[0]

        # Fall back to nearest available date (within 7 days)
        result = self.conn.execute("""
            SELECT rate, date FROM exchange_rates
            WHERE from_currency = ? AND to_currency = ?
              AND ABS(DATEDIFF('day', date, ?)) <= 7
            ORDER BY ABS(DATEDIFF('day', date, ?)), fetched_at DESC
            LIMIT 1
        """, [from_currency, to_currency, on_date, on_date]).fetchone()
        
        if result:
            rate, nearest_date = result
            logger.debug(
                f"Using nearest rate from {nearest_date} for {from_currency}/{to_currency} on {on_date}"
            )
            return rate

        return None

    def get_portfolio_currencies(self) -> list[str]:
        """Get list of unique currencies in the portfolio.

        Returns:
            List of currency codes
        """
        result = self.conn.execute("""
            SELECT DISTINCT currency
            FROM transactions
            WHERE currency IS NOT NULL AND currency != ''
            ORDER BY currency
        """).fetchall()
        
        currencies = [row[0] for row in result if row[0]]
        logger.info(f"Found currencies in portfolio: {currencies}")
        return currencies

    def fetch_all_portfolio_currencies(self, force_refresh: bool = False) -> None:
        """Fetch exchange rates for all currencies in the portfolio.

        Args:
            force_refresh: Force re-fetch even if cached
        """
        currencies = self.get_portfolio_currencies()
        
        # Get date range from transactions
        date_range = self.conn.execute("""
            SELECT MIN(trade_date) as earliest, MAX(trade_date) as latest
            FROM transactions
        """).fetchone()
        
        if not date_range or not date_range[0]:
            logger.warning("No transactions found, skipping currency fetch")
            return

        start_date = date_range[0]
        end_date = date_range[1] or date.today()
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        logger.info(f"Fetching exchange rates for {len(currencies)} currencies")
        
        for currency in currencies:
            if currency and currency.upper() != self.base_currency:
                try:
                    self.fetch_exchange_rates(
                        currency, start_date, end_date, force_refresh
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch rates for {currency}: {e}")
