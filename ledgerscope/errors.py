"""Error handling utilities and custom exceptions for LedgerScope.

Provides retry decorators, custom exceptions, and error recovery mechanisms.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Optional, Type

from ledgerscope.logging import get_logger

logger = get_logger(__name__)


# ── Custom Exceptions ────────────────────────────────────────────


class LedgerScopeError(Exception):
    """Base exception for all LedgerScope errors."""

    pass


class DataIngestionError(LedgerScopeError):
    """Error during data ingestion from broker files."""

    pass


class ValidationError(LedgerScopeError):
    """Error during data validation."""

    pass


class DataFetchError(LedgerScopeError):
    """Error fetching data from external APIs."""

    pass


class CurrencyConversionError(LedgerScopeError):
    """Error during currency conversion."""

    pass


class DatabaseError(LedgerScopeError):
    """Error during database operations."""

    pass


class ConfigurationError(LedgerScopeError):
    """Error in configuration."""

    pass


# ── Retry Decorator ──────────────────────────────────────────────


def retry_on_exception(
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    backoff: float = 1.5,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """Decorator to retry a function on exception.

    Args:
        max_attempts: Maximum number of attempts (from config if None)
        delay: Initial delay between retries in seconds (from config if None)
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry

    Usage:
        @retry_on_exception(max_attempts=3, delay=1)
        def fetch_data():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from ledgerscope.config import get_config

            config = get_config()
            attempts = max_attempts or config.retry_attempts
            current_delay = delay if delay is not None else config.retry_delay

            last_exception = None

            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == attempts:
                        # Last attempt failed
                        logger.error(
                            f"{func.__name__} failed after {attempts} attempts: {e}",
                            exc_info=True,
                        )
                        raise

                    # Log retry
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )

                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error(f"Retry callback failed: {callback_error}")

                    # Wait before retry
                    time.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_with_timeout(
    timeout: float,
    max_attempts: Optional[int] = None,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator to retry a function with a global timeout.

    Args:
        timeout: Maximum total time in seconds for all attempts
        max_attempts: Maximum number of attempts
        exceptions: Tuple of exception types to catch and retry

    Usage:
        @retry_with_timeout(timeout=30, max_attempts=5)
        def slow_operation():
            ...
    """
    import threading

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from ledgerscope.config import get_config

            config = get_config()
            attempts = max_attempts or config.retry_attempts

            result = [None]
            exception = [None]
            completed = threading.Event()

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except exceptions as e:
                    exception[0] = e
                finally:
                    completed.set()

            start_time = time.time()
            last_exception = None

            for attempt in range(1, attempts + 1):
                if time.time() - start_time >= timeout:
                    raise TimeoutError(
                        f"{func.__name__} timed out after {timeout}s and {attempt - 1} attempts"
                    )

                thread = threading.Thread(target=target)
                thread.daemon = True
                thread.start()

                remaining_time = timeout - (time.time() - start_time)
                thread.join(timeout=remaining_time)

                if thread.is_alive():
                    raise TimeoutError(
                        f"{func.__name__} timed out after {timeout}s on attempt {attempt}"
                    )

                if exception[0]:
                    last_exception = exception[0]
                    if attempt < attempts:
                        logger.warning(
                            f"{func.__name__} attempt {attempt}/{attempts} failed: {exception[0]}"
                        )
                        exception[0] = None
                        completed.clear()
                    else:
                        raise last_exception
                else:
                    return result[0]

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# ── Error Context Manager ────────────────────────────────────────


class ErrorContext:
    """Context manager for structured error handling.

    Usage:
        with ErrorContext("importing transactions", raise_on_error=True):
            # Code that might fail
            parse_csv(file)
    """

    def __init__(
        self,
        operation: str,
        raise_on_error: bool = True,
        log_level: str = "error",
    ):
        """Initialize error context.

        Args:
            operation: Description of the operation being performed
            raise_on_error: Whether to re-raise exceptions
            log_level: Log level for errors (error, warning, info)
        """
        self.operation = operation
        self.raise_on_error = raise_on_error
        self.log_level = log_level.lower()
        self.exception: Optional[Exception] = None

    def __enter__(self):
        """Enter context."""
        logger.debug(f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and handle exceptions."""
        if exc_type is None:
            logger.debug(f"Completed: {self.operation}")
            return True

        self.exception = exc_val

        # Log the error at appropriate level
        log_msg = f"Error during {self.operation}: {exc_val}"
        
        if self.log_level == "error":
            logger.error(log_msg, exc_info=True)
        elif self.log_level == "warning":
            logger.warning(log_msg)
        elif self.log_level == "info":
            logger.info(log_msg)

        # Return True to suppress exception, False to re-raise
        return not self.raise_on_error


# ── Safe Execution Helpers ───────────────────────────────────────


def safe_execute(
    func: Callable,
    *args,
    default: Any = None,
    log_errors: bool = True,
    **kwargs,
) -> Any:
    """Safely execute a function, returning default value on error.

    Args:
        func: Function to execute
        *args: Positional arguments for function
        default: Default value to return on error
        log_errors: Whether to log errors
        **kwargs: Keyword arguments for function

    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error executing {func.__name__}: {e}", exc_info=True)
        return default


def validate_input(
    value: Any,
    value_name: str,
    expected_type: Optional[Type] = None,
    allowed_values: Optional[list] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> None:
    """Validate input parameters.

    Args:
        value: Value to validate
        value_name: Name of the value for error messages
        expected_type: Expected type of the value
        allowed_values: List of allowed values
        min_value: Minimum allowed value (for numeric types)
        max_value: Maximum allowed value (for numeric types)

    Raises:
        ValidationError: If validation fails
    """
    if expected_type and not isinstance(value, expected_type):
        raise ValidationError(
            f"{value_name} must be of type {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )

    if allowed_values and value not in allowed_values:
        raise ValidationError(
            f"{value_name} must be one of {allowed_values}, got {value}"
        )

    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{value_name} must be >= {min_value}, got {value}"
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"{value_name} must be <= {max_value}, got {value}"
        )


def handle_api_error(response) -> None:
    """Handle HTTP API errors with appropriate exceptions.

    Args:
        response: requests.Response object

    Raises:
        DataFetchError: On API errors
    """
    if response.status_code == 200:
        return

    error_messages = {
        400: "Bad request",
        401: "Unauthorized - check API key",
        403: "Forbidden - access denied",
        404: "Resource not found",
        429: "Rate limit exceeded - please try again later",
        500: "Internal server error",
        503: "Service unavailable",
    }

    message = error_messages.get(response.status_code, f"HTTP {response.status_code}")
    
    try:
        error_detail = response.json()
        if isinstance(error_detail, dict):
            message += f": {error_detail.get('message', error_detail.get('error', ''))}"
    except Exception:
        pass

    logger.error(f"API error: {message} (URL: {response.url})")
    raise DataFetchError(message)
