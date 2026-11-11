"""
SPECTRE Test Suite — QRNG Unit Tests
Tests for scripts/quantum_rng.py: ANU API fetcher success and failure paths.

Validates: Requirements 6.1, 6.2
"""

import pytest

from scripts.quantum_rng import fetch_anu_quantum_bytes


class TestFetchANUQuantumBytes:
    """
    Tests for the ANU quantum vacuum API fetcher.

    Validates: Requirements 6.1, 6.2
    """

    def test_anu_success_returns_correct_length(self, mock_anu_success):
        """
        WHEN fetch_anu_quantum_bytes is called and the ANU API returns a valid
        {"success": true, "data": [...]} response with 1024 byte values,
        THE QRNG SHALL return a bytes object of exactly the requested length.

        Validates: Requirement 6.1
        """
        result = fetch_anu_quantum_bytes(32)

        assert isinstance(result, bytes), "Expected a bytes object, got: " + type(result).__name__
        assert len(result) == 32, f"Expected 32 bytes, got {len(result)}"

    def test_anu_failure_returns_none(self, mock_anu_failure):
        """
        WHEN fetch_anu_quantum_bytes is called and the ANU API is unreachable
        (network error), THE QRNG SHALL return None without raising an exception.

        Validates: Requirement 6.2
        """
        result = fetch_anu_quantum_bytes(32)

        assert result is None, f"Expected None on network failure, got: {result!r}"
