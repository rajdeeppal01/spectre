"""
auto_router.py — AUTO-mode routing layer for SPECTRE.

Sits in front of the LiteLLM proxy. Open WebUI / Continue.dev point at
THIS service when global mode = AUTO. In ONLINE or OFFLINE mode, clients
should bypass this and call LiteLLM (:4000) directly with a pinned model.

Implements the rule order from the design doc, checked in sequence:
  Rule 1 — cybersecurity keyword match  -> force "spectre" (local)
  Rule 2 — no internet connectivity     -> force a local model
  Rule 3 — task complexity (long/multi-file/architecture) -> "gemini-pro"
  Rule 4 — speed vs quality for what's left -> "gemini-flash" / "atlas"

A request can also carry `"x-spectre-private": true` in headers (set
by Open WebUI for conversations tagged "private") to force local
routing regardless of these rules.
"""

import os
import re
import socket
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://localhost:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")

app = FastAPI(title="SPECTRE AUTO Router")

# Rule 1 — never let these touch the cloud
CYBERSEC_PATTERN = re.compile(
    r"\b(exploit|payload|cve|nmap|malware|pentest|reverse shell|"
    r"metasploit|privesc|sqli|xss|rce|shellcode|c2|ransomware)\b",
    re.IGNORECASE,
)

# Rule 3 — complexity signals
COMPLEXITY_PATTERN = re.compile(
    r"\b(architecture|refactor|entire codebase|multi-file|design the)\b",
    re.IGNORECASE,
)

COMPLEXITY_TOKEN_THRESHOLD = 1000  # rough word-count proxy for "1000 tokens"


def has_internet(timeout: float = 1.5) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


def extract_prompt_text(body: dict) -> str:
    messages = body.get("messages", [])
    return " ".join(
        m.get("content", "") if isinstance(m.get("content"), str) else ""
        for m in messages
    )


def choose_model(body: dict, is_private: bool) -> str:
    text = extract_prompt_text(body)

    # Rule 1 — cybersecurity check, overrides everything including privacy flag
    if CYBERSEC_PATTERN.search(text):
        return "spectre"

    if is_private:
        return "architect"  # safe local default for tagged-private chats

    # Rule 2 — connectivity check
    if not has_internet():
        return "architect" if COMPLEXITY_PATTERN.search(text) else "atlas"

    # Rule 3 — complexity check
    word_count = len(text.split())
    if word_count > COMPLEXITY_TOKEN_THRESHOLD or COMPLEXITY_PATTERN.search(text):
        return "gemini-pro"

    # Rule 4 — speed vs quality for what's left
    if word_count < 50:
        return "gemini-flash"
    return "gemini-pro"


@app.post("/v1/chat/completions")
async def route(request: Request):
    body = await request.json()
    is_private = request.headers.get("x-spectre-private", "false").lower() == "true"

    chosen = choose_model(body, is_private)
    body["model"] = chosen

    headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}"}

    async def stream():
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{LITELLM_BASE}/v1/chat/completions",
                json=body,
                headers=headers,
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "internet": has_internet()}
