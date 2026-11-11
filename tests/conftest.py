"""
SPECTRE Test Suite — Root conftest.py
Shared fixtures for mocking the Ollama API, ANU QRNG API, LiteLLM proxy,
and filesystem helpers.  All fixtures are air-gapped: no real network calls
are made in unit tests.

Validates: Requirements 1.2
"""

import io
import json
import types
import urllib.error
from pathlib import Path
from typing import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── 1. Ollama API mock (urllib-based) ────────────────────────────────────────

class _FakeUrllibResponse:
    """
    Minimal file-like context-manager that satisfies the interface used by
    `urllib.request.urlopen`:
        with urllib.request.urlopen(req) as response:
            response.status
            response.read()
    """

    def __init__(self, data: bytes, status: int = 200):
        self._buf = io.BytesIO(data)
        self.status = status

    # io / file-like API
    def read(self, *args, **kwargs) -> bytes:
        return self._buf.read(*args, **kwargs)

    # context-manager API
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def mock_ollama(monkeypatch):
    """
    Monkeypatch ``urllib.request.urlopen`` globally so that any call to the
    Ollama ``/api/generate`` endpoint (used by ``continuous_security``,
    ``pqc_audit``, and ``quantum_sim``) receives a deterministic JSON
    response without touching the network.

    The fake response body matches Ollama's ``/api/generate`` schema:
        {"response": "mock AI analysis", "done": true}
    """
    payload = json.dumps({"response": "mock AI analysis", "done": True}).encode()
    fake_response = _FakeUrllibResponse(payload, status=200)

    def _fake_urlopen(*args, **kwargs):
        return fake_response

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    return fake_response


# ── 2. OpenAI client mock (web_audit_bridge) ─────────────────────────────────

@pytest.fixture
def mock_openai_client(monkeypatch):
    """
    Replace the module-level ``CLIENT`` object in ``agents.web_audit_bridge``
    with a ``MagicMock`` whose ``.chat.completions.create()`` returns a
    SimpleNamespace that looks like an ``openai.ChatCompletion`` object.

    Shape returned:
        SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="mock AI analysis"))]
        )
    """
    fake_message = types.SimpleNamespace(content="mock AI analysis")
    fake_choice = types.SimpleNamespace(message=fake_message)
    fake_completion = types.SimpleNamespace(choices=[fake_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_completion

    # Patch the already-constructed module-level CLIENT instance
    import agents.web_audit_bridge as _bridge
    monkeypatch.setattr(_bridge, "CLIENT", mock_client)

    return mock_client


# ── 3. ANU QRNG API mock — success path ──────────────────────────────────────

@pytest.fixture
def mock_anu_success(monkeypatch):
    """
    Monkeypatch ``scripts.quantum_rng.urllib.request.urlopen`` so that every
    call returns a valid ANU QRNG JSON response containing 1 024 byte values
    (the API maximum per request), regardless of the requested length.

    Returning 1 024 values ensures the QRNG module can satisfy any request
    ≤ 1 024 bytes in a single call without hitting the recursive branch.
    """
    payload = json.dumps({"success": True, "data": [42] * 1024}).encode()

    def _fake_urlopen(*args, **kwargs):
        return _FakeUrllibResponse(payload, status=200)

    import scripts.quantum_rng as _qrng
    monkeypatch.setattr(_qrng.urllib.request, "urlopen", _fake_urlopen)
    return _fake_urlopen


# ── 4. ANU QRNG API mock — failure path ──────────────────────────────────────

@pytest.fixture
def mock_anu_failure(monkeypatch):
    """
    Monkeypatch ``scripts.quantum_rng.urllib.request.urlopen`` so that every
    call raises ``urllib.error.URLError("unreachable")``, simulating a network
    outage.  ``fetch_anu_quantum_bytes`` should catch this and return ``None``.
    """
    def _fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("unreachable")

    import scripts.quantum_rng as _qrng
    monkeypatch.setattr(_qrng.urllib.request, "urlopen", _fake_urlopen)
    return _fake_urlopen


# ── 5. LiteLLM proxy mock (httpx-based, async streaming) ─────────────────────

@pytest.fixture
def mock_litellm(monkeypatch):
    """
    Monkeypatch ``httpx.AsyncClient`` used by ``scripts.auto_router.route``
    so that ``.stream(...)`` yields a single fake SSE chunk:

        b'data: {"choices":[{"delta":{"content":"ok"}}]}\\n\\n'

    The mock satisfies the ``async with client.stream(...) as response``
    pattern and makes the response body async-iterable line-by-line.
    """
    sse_chunk = b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'

    # Async iterator that yields the single SSE chunk
    async def _aiter_lines():
        yield sse_chunk

    # Response object returned by `async with client.stream(...) as resp`
    mock_response = MagicMock()
    mock_response.aiter_lines = _aiter_lines
    mock_response.aiter_bytes = _aiter_lines  # in case router uses aiter_bytes
    mock_response.status_code = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    # The client's .stream() itself is an async context manager
    mock_stream_cm = MagicMock()
    mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_cm.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_stream_cm
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    # AsyncClient() constructor → our mock
    mock_async_client_cls = MagicMock(return_value=mock_client)

    monkeypatch.setattr("httpx.AsyncClient", mock_async_client_cls)
    return mock_async_client_cls


# ── 6. Temporary single-file factory ─────────────────────────────────────────

@pytest.fixture
def tmp_py_file(tmp_path: Path) -> Callable[[str, str], Path]:
    """
    Return a factory callable::

        tmp_py_file(content: str, suffix: str = ".py") -> Path

    Writes *content* to ``tmp_path / "test_input{suffix}"`` and returns the
    resulting ``Path``.  Use this fixture wherever a test needs a real file
    on disk (``test_continuous_security``, ``test_pqc_audit``,
    ``test_web_audit_bridge``).
    """

    def _factory(content: str, suffix: str = ".py") -> Path:
        p = tmp_path / f"test_input{suffix}"
        p.write_text(content, encoding="utf-8")
        return p

    return _factory


# ── 7. Temporary directory-with-files factory ─────────────────────────────────

@pytest.fixture
def tmp_dir_with_files(tmp_path: Path) -> Callable[[dict], Path]:
    """
    Return a factory callable::

        tmp_dir_with_files(file_map: dict) -> Path

    *file_map* maps relative path strings to file content strings::

        {
            "src/app.py": "DEBUG = True",
            "src/db.py":  "cursor.execute('SELECT ' + user_id)",
        }

    Each file is created under ``tmp_path``, with parent directories
    created as needed.  Returns ``tmp_path``.
    """

    def _factory(file_map: dict) -> Path:
        for rel_path, content in file_map.items():
            full_path = tmp_path / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
        return tmp_path

    return _factory


# ── pytest CLI option and markers ────────────────────────────────────────────

def pytest_addoption(parser):
    """Register the ``--run-integration`` CLI flag consumed by integration tests."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require live local services (Ollama, LiteLLM, ANU API).",
    )
