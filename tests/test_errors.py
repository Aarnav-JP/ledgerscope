"""Tests for error handling and retry mechanisms."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from ledgerscope.errors import (
    DataFetchError,
    ErrorContext,
    LedgerScopeError,
    ValidationError,
    retry_on_exception,
    safe_execute,
    validate_input,
)


def test_custom_exceptions():
    """Test that custom exceptions inherit correctly."""
    assert issubclass(DataFetchError, LedgerScopeError)
    assert issubclass(ValidationError, LedgerScopeError)
    
    error = DataFetchError("Test error")
    assert str(error) == "Test error"


def test_retry_decorator_success():
    """Test retry decorator with successful execution."""
    call_count = [0]
    
    @retry_on_exception(max_attempts=3, delay=0.1)
    def flaky_function():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ValueError("Temporary error")
        return "success"
    
    result = flaky_function()
    
    assert result == "success"
    assert call_count[0] == 2


def test_retry_decorator_exhausted():
    """Test retry decorator when all attempts fail."""
    call_count = [0]
    
    @retry_on_exception(max_attempts=3, delay=0.05)
    def always_fails():
        call_count[0] += 1
        raise ValueError("Persistent error")
    
    with pytest.raises(ValueError, match="Persistent error"):
        always_fails()
    
    assert call_count[0] == 3


def test_retry_decorator_immediate_success():
    """Test retry decorator when no retry is needed."""
    
    @retry_on_exception(max_attempts=3, delay=0.1)
    def works_first_time():
        return "success"
    
    result = works_first_time()
    
    assert result == "success"


def test_retry_decorator_specific_exceptions():
    """Test retry decorator only catches specified exceptions."""
    
    @retry_on_exception(max_attempts=3, delay=0.05, exceptions=(ValueError,))
    def raises_type_error():
        raise TypeError("Wrong exception type")
    
    # Should not retry TypeError
    with pytest.raises(TypeError):
        raises_type_error()


def test_retry_callback():
    """Test retry decorator callback is called."""
    callback_calls = []
    
    def on_retry(exception, attempt):
        callback_calls.append((exception, attempt))
    
    call_count = [0]
    
    @retry_on_exception(max_attempts=3, delay=0.05, on_retry=on_retry)
    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ValueError(f"Error {call_count[0]}")
        return "success"
    
    result = flaky()
    
    assert result == "success"
    assert len(callback_calls) == 2
    assert callback_calls[0][1] == 1
    assert callback_calls[1][1] == 2


def test_error_context_success():
    """Test ErrorContext when no error occurs."""
    with ErrorContext("test operation") as ctx:
        result = 1 + 1
    
    assert ctx.exception is None


def test_error_context_with_error_raise():
    """Test ErrorContext re-raises exception when configured."""
    with pytest.raises(ValueError):
        with ErrorContext("test operation", raise_on_error=True):
            raise ValueError("Test error")


def test_error_context_with_error_suppress():
    """Test ErrorContext suppresses exception when configured."""
    with ErrorContext("test operation", raise_on_error=False) as ctx:
        raise ValueError("Test error")
    
    assert ctx.exception is not None
    assert isinstance(ctx.exception, ValueError)


def test_safe_execute_success():
    """Test safe_execute with successful function."""
    def successful_func(x, y):
        return x + y
    
    result = safe_execute(successful_func, 5, 10)
    
    assert result == 15


def test_safe_execute_with_error():
    """Test safe_execute returns default on error."""
    def failing_func():
        raise ValueError("Error")
    
    result = safe_execute(failing_func, default="fallback")
    
    assert result == "fallback"


def test_safe_execute_no_default():
    """Test safe_execute returns None when no default provided."""
    def failing_func():
        raise ValueError("Error")
    
    result = safe_execute(failing_func)
    
    assert result is None


def test_validate_input_type():
    """Test input validation for type checking."""
    validate_input("test", "my_string", expected_type=str)
    
    with pytest.raises(ValidationError, match="must be of type int"):
        validate_input("test", "my_number", expected_type=int)


def test_validate_input_allowed_values():
    """Test input validation for allowed values."""
    validate_input("blue", "color", allowed_values=["red", "green", "blue"])
    
    with pytest.raises(ValidationError, match="must be one of"):
        validate_input("yellow", "color", allowed_values=["red", "green", "blue"])


def test_validate_input_range():
    """Test input validation for numeric ranges."""
    validate_input(50, "percentage", min_value=0, max_value=100)
    
    with pytest.raises(ValidationError, match="must be >= 0"):
        validate_input(-10, "percentage", min_value=0)
    
    with pytest.raises(ValidationError, match="must be <= 100"):
        validate_input(150, "percentage", max_value=100)


def test_validate_input_combined():
    """Test input validation with multiple constraints."""
    validate_input(50, "score", expected_type=int, min_value=0, max_value=100)
    
    with pytest.raises(ValidationError):
        validate_input(50.5, "score", expected_type=int, min_value=0, max_value=100)
