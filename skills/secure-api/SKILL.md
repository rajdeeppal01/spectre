---
name: Secure API & Microservice Hardening
description: Standard operating procedure for building hardened, zero-trust backend endpoints in FastAPI (Python) or Express (TypeScript) with rate limiting, strict CORS, input validation, and CSP headers.
---

# Secure API & Microservice Hardening Workflow

Follow these mandatory practices when creating or modifying backend API endpoints:

## 1. Input Validation & Strict Typing
- In FastAPI: Always use Pydantic `BaseModel` with field constraints (`Field(min_length=..., max_length=..., pattern=...)`). Never accept unvalidated raw dicts.
- In Express/TypeScript: Use `zod` schema parsing on `req.body` before processing.

## 2. Security Headers & Zero-Trust Middleware
- Enforce standard security headers:
  - `Content-Security-Policy: default-src 'self'`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
- Rate Limiting: Apply Redis-backed or in-memory leaky-bucket rate limiting (e.g., max 60 requests/minute per IP) on all public routes.

## 3. Secret Management
- Never commit API keys, database credentials, or secret tokens into source code or config files.
- Always retrieve via `os.environ.get()` or `.env` through `python-dotenv` / `dotenv`.
- Include safe defaults and descriptive error logging if required environment variables are absent.

## 4. Verification & Red-Team Audit
- Run `verify_build` to test syntax and imports.
- Run `handoff_to_spectre` to verify zero secret leaks, no debug routes exposed, and proper access controls.
