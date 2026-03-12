"""Tests for configuration management."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from ledgerscope.config import Config, get_config


def test_config_defaults():
    """Test that default configuration values are set correctly."""
    config = Config()
    
    assert config.base_currency == "USD"
    assert config.risk_free_rate == 0.04
    assert config.log_level == "INFO"
    assert config.cache_expiry_days == 1
    assert config.retry_attempts == 3
    assert config.auto_convert_currency is True


def test_config_from_file():
    """Test loading configuration from TOML file."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[general]
base_currency = "EUR"
risk_free_rate = 0.05
log_level = "DEBUG"

[data]
cache_expiry_days = 7
retry_attempts = 5
""")
        
        config = Config(config_path=config_path)
        
        assert config.base_currency == "EUR"
        assert config.risk_free_rate == 0.05
        assert config.log_level == "DEBUG"
        assert config.cache_expiry_days == 7
        assert config.retry_attempts == 5


def test_config_env_override():
    """Test that environment variables override config file."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text("""
[general]
base_currency = "USD"
risk_free_rate = 0.04
""")
        
        # Set environment variable
        os.environ["LEDGERSCOPE_GENERAL_BASE_CURRENCY"] = "GBP"
        os.environ["LEDGERSCOPE_GENERAL_RISK_FREE_RATE"] = "0.03"
        
        try:
            config = Config(config_path=config_path)
            
            assert config.base_currency == "GBP"
            assert config.risk_free_rate == 0.03
        finally:
            # Clean up
            del os.environ["LEDGERSCOPE_GENERAL_BASE_CURRENCY"]
            del os.environ["LEDGERSCOPE_GENERAL_RISK_FREE_RATE"]


def test_config_get_section():
    """Test retrieving entire configuration section."""
    config = Config()
    
    general_section = config.get_section("general")
    
    assert "base_currency" in general_section
    assert "risk_free_rate" in general_section
    assert general_section["base_currency"] == "USD"


def test_config_create_default():
    """Test creating default configuration file."""
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config = Config(config_path=config_path)
        
        assert not config_path.exists()
        
        config.create_default_config()
        
        assert config_path.exists()
        content = config_path.read_text()
        assert "[general]" in content
        assert "base_currency" in content


def test_config_type_conversion():
    """Test that configuration values are converted to correct types."""
    os.environ["LEDGERSCOPE_GENERAL_RISK_FREE_RATE"] = "0.05"
    os.environ["LEDGERSCOPE_DATA_CACHE_EXPIRY_DAYS"] = "7"
    os.environ["LEDGERSCOPE_CURRENCY_AUTO_CONVERT"] = "false"
    
    try:
        config = Config()
        
        assert isinstance(config.risk_free_rate, float)
        assert config.risk_free_rate == 0.05
        
        assert isinstance(config.cache_expiry_days, int)
        assert config.cache_expiry_days == 7
        
        assert isinstance(config.auto_convert_currency, bool)
        assert config.auto_convert_currency is False
    finally:
        del os.environ["LEDGERSCOPE_GENERAL_RISK_FREE_RATE"]
        del os.environ["LEDGERSCOPE_DATA_CACHE_EXPIRY_DAYS"]
        del os.environ["LEDGERSCOPE_CURRENCY_AUTO_CONVERT"]
