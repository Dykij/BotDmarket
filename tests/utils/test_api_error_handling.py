"""Tests for the API error handling utility."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.utils.api_error_handling import (
    APIError,
    handle_response,
    retry_request,
)


def test_api_error_creation():
    """Test creating APIError instances."""
    error = APIError("Test error")
    assert str(error) == "Test error (Статус: 0)"

    error_with_status = APIError("Error with status", status_code=404)
    assert error_with_status.status_code == 404
    assert "Error with status" in str(error_with_status)
    assert "404" in str(error_with_status)


@pytest.mark.asyncio
async def test_handle_response():
    """Test handling API responses."""
    # Create a successful response mock
    success_response = MagicMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value={"data": "success"})

    # Test successful response
    result = await handle_response(success_response)
    assert result == {"data": "success"}

    # Create an error response mock
    error_response = MagicMock()
    error_response.status = 404
    error_response.json = AsyncMock(return_value={"error": "Not found"})

    # Test error response
    with pytest.raises(APIError) as excinfo:
        await handle_response(error_response)
    assert "404" in str(excinfo.value)


@pytest.mark.asyncio
async def test_retry_request():
    """Test retry_request function for API calls."""
    # Create a mock function that fails first then succeeds
    mock_func = AsyncMock()
    mock_func.side_effect = [
        APIError("First failure"),
        APIError("Second failure"),
        "Success",
    ]

    # Call retry_request with our mock
    result = await retry_request(
        request_func=mock_func,
        max_retries=2,
    )

    # Check that the function was called the expected number of times
    assert mock_func.call_count == 3

    # Check the final result
    assert result == "Success"


@pytest.mark.asyncio
async def test_retry_request_max_retries_exceeded():
    """Test retry_request when max retries is exceeded."""
    # Create a mock function that always fails
    mock_func = AsyncMock()
    mock_func.side_effect = APIError("Always fails")

    # Call retry_request with short delays to speed up test
    start_time = time.time()

    # Should raise the original APIError after max_retries
    with pytest.raises(APIError) as excinfo:
        await retry_request(
            request_func=mock_func,
            max_retries=1,
        )

    elapsed_time = time.time() - start_time

    # Check that the function was called the expected number of times
    assert mock_func.call_count == 2  # 1 initial + 1 retry

    # Verify that error message is preserved
    assert "Always fails" in str(excinfo.value)

    # Verify that some delay happened
    assert elapsed_time > 0
