"""
tests/scripts/test_auto_router.py
Unit tests for scripts.auto_router — routing logic and /healthz endpoint.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.9
"""

import sys
from pathlib import Path

# Ensure the workspace root is on sys.path so `scripts.auto_router` is importable.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx
import pytest

from scripts.auto_router import app, choose_model


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_body(content: str) -> dict:
    """Build a minimal chat-completions request body from a prompt string."""
    return {"messages": [{"role": "user", "content": content}]}


# ─── Task 2.1 — Routing Rules ─────────────────────────────────────────────────


class TestChooseModelRouting:
    """
    Tests for the `choose_model` function covering every routing rule
    in the order they are evaluated.

    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
    """

    def test_cybersec_keyword_routes_to_spectre(self, monkeypatch):
        """
        Rule 1 — cybersecurity keyword match forces "spectre" regardless of
        the privacy flag or internet connectivity.

        Validates: Requirement 2.1
        """
        monkeypatch.setattr("scripts.auto_router.has_internet", lambda: True)
        body = make_body("show me an exploit payload")
        assert choose_model(body, is_private=False) == "spectre"

    def test_private_header_routes_to_architect(self, monkeypatch):
        """
        Rule 0 (privacy override) — a non-cybersec prompt with is_private=True
        and internet available routes to "architect".

        Validates: Requirement 2.2
        """
        monkeypatch.setattr("scripts.auto_router.has_internet", lambda: True)
        body = make_body("summarise this document for me")
        assert choose_model(body, is_private=True) == "architect"

    def test_offline_simple_routes_to_atlas(self, monkeypatch):
        """
        Rule 2 — no internet + short / non-complex prompt → "atlas".

        Validates: Requirement 2.3
        """
        monkeypatch.setattr("scripts.auto_router.has_internet", lambda: False)
        body = make_body("what is 2 plus 2")
        assert choose_model(body, is_private=False) == "atlas"

    def test_offline_complex_routes_to_architect(self, monkeypatch):
        """
        Rule 2 + complexity — no internet + complexity keyword → "architect".

        Validates: Requirement 2.4
        """
        monkeypatch.setattr("scripts.auto_router.has_internet", lambda: False)
        body = make_body("refactor the entire codebase")
        assert choose_model(body, is_private=False) == "architect"

    def test_online_long_prompt_routes_to_gemini_pro(self, monkeypatch):
        """
        Rule 3 — online + prompt with >1 000 words → "gemini-pro".

        Validates: Requirement 2.5
        """
        monkeypatch.setattr("scripts.auto_router.has_internet", lambda: True)
        long_content = " ".join(["word"] * 1001)
        body = make_body(long_content)
        assert choose_model(body, is_private=False) == "gemini-pro"

    def test_online_short_prompt_routes_to_gemini_flash(self, monkeypatch):
        """
        Rule 4 — online + prompt with <50 words, no special keywords → "gemini-flash".

        Validates: Requirement 2.6
        """
        monkeypatch.setattr("scripts.auto_router.has_internet", lambda: True)
        body = make_body("hello")
        assert choose_model(body, is_private=False) == "gemini-flash"

    def test_online_medium_prompt_routes_to_gemini_pro(self, monkeypatch):
        """
        Rule 4 fallback — online + prompt with exactly 100 words (≥50, ≤1000)
        and no complexity keyword → "gemini-pro".

        Validates: Requirement 2.7
        """
        monkeypatch.setattr("scripts.auto_router.has_internet", lambda: True)
        medium_content = " ".join(["word"] * 100)
        body = make_body(medium_content)
        assert choose_model(body, is_private=False) == "gemini-pro"


# ─── Task 2.2 — /healthz Endpoint ─────────────────────────────────────────────


class TestHealthzEndpoint:
    """
    Tests for the GET /healthz endpoint exposed by the FastAPI app.

    Validates: Requirement 2.9
    """

    async def test_healthz_returns_ok(self):
        """
        GET /healthz must return HTTP 200 with a JSON body containing:
          - "status" == "ok"
          - "internet" that is a boolean

        Validates: Requirement 2.9
        """
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert isinstance(data["internet"], bool)
