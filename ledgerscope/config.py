"""Configuration management for LedgerScope.

Supports both config file (~/.ledgerscope/config.toml) and environment variables.
Environment variables take precedence over config file settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python 3.10


class Config:
    """LedgerScope configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration from file and environment.

        Args:
            config_path: Optional path to config file. Defaults to ~/.ledgerscope/config.toml
        """
        self._config_path = config_path or self._get_default_config_path()
        self._config = self._load_config()

    @staticmethod
    def _get_default_config_path() -> Path:
        """Get the default configuration file path."""
        return Path.home() / ".ledgerscope" / "config.toml"

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from TOML file if it exists."""
        if not self._config_path.exists():
            return self._get_defaults()

        try:
            with open(self._config_path, "rb") as f:
                config = tomllib.load(f)
            # Merge with defaults to ensure all keys exist
            defaults = self._get_defaults()
            for section, values in defaults.items():
                if section not in config:
                    config[section] = {}
                for key, default_value in values.items():
                    if key not in config[section]:
                        config[section][key] = default_value
            return config
        except Exception as e:
            raise ValueError(f"Failed to load config from {self._config_path}: {e}")

    @staticmethod
    def _get_defaults() -> dict[str, Any]:
        """Get default configuration values."""
        return {
            "general": {
                "base_currency": "USD",
                "risk_free_rate": 0.04,  # 4% annual
                "log_level": "INFO",
                "log_file": "ledgerscope.log",
            },
            "data": {
                "cache_expiry_days": 1,
                "price_source": "yfinance",
                "macro_source": "fred",
                "retry_attempts": 3,
                "retry_delay_seconds": 2,
                "request_timeout_seconds": 30,
            },
            "currency": {
                "auto_convert": True,
                "exchange_rate_source": "exchangerate-api",
                "fallback_rates": {},  # Manual rate overrides
            },
            "display": {
                "date_format": "%Y-%m-%d",
                "decimal_places": 2,
                "large_number_format": "abbreviated",  # or "full"
            },
            "api_keys": {
                "fred_api_key": "",
                "exchangerate_api_key": "",
            },
        }

    def _get_env_override(self, section: str, key: str) -> Optional[str]:
        """Check for environment variable override.

        Environment variables are in the format: LEDGERSCOPE_SECTION_KEY
        Example: LEDGERSCOPE_GENERAL_BASE_CURRENCY
        """
        env_key = f"LEDGERSCOPE_{section.upper()}_{key.upper()}"
        return os.environ.get(env_key)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Checks in order:
        1. Environment variable (LEDGERSCOPE_SECTION_KEY)
        2. Config file
        3. Provided default
        4. Built-in default

        Args:
            section: Configuration section (e.g., 'general', 'data')
            key: Configuration key within the section
            default: Optional default value if not found

        Returns:
            Configuration value
        """
        # Check environment variable first
        env_value = self._get_env_override(section, key)
        if env_value is not None:
            # Try to convert to appropriate type
            return self._convert_type(env_value, type(self._config.get(section, {}).get(key)))

        # Check config file
        if section in self._config and key in self._config[section]:
            return self._config[section][key]

        # Return provided default or None
        return default

    @staticmethod
    def _convert_type(value: str, target_type: type) -> Any:
        """Convert string value to target type."""
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        return value

    def get_section(self, section: str) -> dict[str, Any]:
        """Get all values from a configuration section.

        Args:
            section: Section name

        Returns:
            Dictionary of configuration values
        """
        config_section = self._config.get(section, {}).copy()

        # Override with environment variables
        for key in config_section.keys():
            env_value = self._get_env_override(section, key)
            if env_value is not None:
                config_section[key] = self._convert_type(
                    env_value, type(config_section[key])
                )

        return config_section

    def create_default_config(self) -> None:
        """Create a default configuration file if it doesn't exist."""
        if self._config_path.exists():
            return

        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        toml_content = self._generate_toml()
        self._config_path.write_text(toml_content)

    def _generate_toml(self) -> str:
        """Generate TOML configuration file content."""
        return """# LedgerScope Configuration File
# This file is automatically generated. Edit as needed.
# Environment variables override these settings (format: LEDGERSCOPE_SECTION_KEY)

[general]
# Base currency for portfolio valuation and reporting
base_currency = "USD"

# Risk-free rate for Sharpe ratio calculations (annual percentage as decimal)
# Default: 4% (0.04)
risk_free_rate = 0.04

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = "INFO"

# Log file name (stored in ~/.ledgerscope/)
log_file = "ledgerscope.log"

[data]
# Number of days before cached data expires
cache_expiry_days = 1

# Data source for historical prices
price_source = "yfinance"

# Data source for macroeconomic indicators
macro_source = "fred"

# Number of retry attempts for failed API calls
retry_attempts = 3

# Delay between retry attempts (seconds)
retry_delay_seconds = 2

# HTTP request timeout (seconds)
request_timeout_seconds = 30

[currency]
# Automatically convert all holdings to base currency
auto_convert = true

# Exchange rate data source
exchange_rate_source = "exchangerate-api"

# Manual exchange rate overrides (symbol pairs)
# Example: "EUR/USD" = 1.08
[currency.fallback_rates]

[display]
# Date format for reports and displays
date_format = "%Y-%m-%d"

# Number of decimal places for currency values
decimal_places = 2

# Format for large numbers: "abbreviated" (1.2M) or "full" (1200000)
large_number_format = "abbreviated"

[api_keys]
# Optional API keys for data sources
# FRED API key (get from: https://fred.stlouisfed.org/docs/api/api_key.html)
fred_api_key = ""

# ExchangeRate-API key (get from: https://www.exchangerate-api.com/)
exchangerate_api_key = ""
"""

    @property
    def base_currency(self) -> str:
        """Get base currency for portfolio."""
        return self.get("general", "base_currency", "USD")

    @property
    def risk_free_rate(self) -> float:
        """Get risk-free rate for calculations."""
        return self.get("general", "risk_free_rate", 0.04)

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.get("general", "log_level", "INFO")

    @property
    def log_file(self) -> str:
        """Get log file name."""
        return self.get("general", "log_file", "ledgerscope.log")

    @property
    def cache_expiry_days(self) -> int:
        """Get cache expiry in days."""
        return self.get("data", "cache_expiry_days", 1)

    @property
    def retry_attempts(self) -> int:
        """Get number of retry attempts for API calls."""
        return self.get("data", "retry_attempts", 3)

    @property
    def retry_delay(self) -> int:
        """Get delay between retries in seconds."""
        return self.get("data", "retry_delay_seconds", 2)

    @property
    def request_timeout(self) -> int:
        """Get HTTP request timeout in seconds."""
        return self.get("data", "request_timeout_seconds", 30)

    @property
    def auto_convert_currency(self) -> bool:
        """Check if automatic currency conversion is enabled."""
        return self.get("currency", "auto_convert", True)


# Global configuration instance
_config: Optional[Config] = None


def get_config(reload: bool = False) -> Config:
    """Get or create the global configuration instance.

    Args:
        reload: Force reload configuration from file

    Returns:
        Config instance
    """
    global _config
    if _config is None or reload:
        _config = Config()
    return _config


def init_config() -> Config:
    """Initialize configuration and create default config file if needed.

    Returns:
        Config instance
    """
    config = get_config()
    config.create_default_config()
    return config
