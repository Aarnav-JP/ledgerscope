"""Logging configuration for LedgerScope.

Provides structured logging with both file and console output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def get_log_path() -> Path:
    """Get the path to the log file."""
    from ledgerscope.config import get_config
    
    config = get_config()
    log_dir = Path.home() / ".ledgerscope"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / config.log_file


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    console_output: bool = True,
) -> logging.Logger:
    """Configure logging for LedgerScope.

    Sets up both file and console logging with appropriate formatters.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: ~/.ledgerscope/ledgerscope.log)
        console_output: Whether to output logs to console

    Returns:
        Configured root logger
    """
    from ledgerscope.config import get_config
    
    config = get_config()
    
    # Determine log level
    if level is None:
        level = config.log_level
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get or create root logger
    logger = logging.getLogger("ledgerscope")
    logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler with detailed formatting
    if log_file is None:
        log_file = get_log_path()
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler with Rich formatting (only for WARNING and above by default)
    if console_output:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            show_time=False,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
        )
        # Only show warnings and errors in console unless debug mode
        console_handler.setLevel(
            logging.DEBUG if numeric_level == logging.DEBUG else logging.WARNING
        )
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    # Ensure base logger is configured
    base_logger = logging.getLogger("ledgerscope")
    if not base_logger.handlers:
        setup_logging()
    
    return logging.getLogger(f"ledgerscope.{name}")


def log_function_call(func):
    """Decorator to log function calls at DEBUG level.

    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            ...
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}", exc_info=True)
            raise
    
    return wrapper


class LogContext:
    """Context manager for temporary logging configuration changes.

    Usage:
        with LogContext(level="DEBUG"):
            # Code here will have DEBUG logging
            pass
    """

    def __init__(self, level: str):
        """Initialize context with new log level.

        Args:
            level: Temporary log level
        """
        self.new_level = getattr(logging, level.upper())
        self.old_level = None
        self.logger = logging.getLogger("ledgerscope")

    def __enter__(self):
        """Save current level and set new level."""
        self.old_level = self.logger.level
        self.logger.setLevel(self.new_level)
        for handler in self.logger.handlers:
            handler.setLevel(self.new_level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original log level."""
        self.logger.setLevel(self.old_level)
