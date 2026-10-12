# Modern Web Development Architecture Standards & Full-Stack Guide

## 1. Core Engineering Principles
This knowledge base guides Gemini Pro, ARCHITECT, and ATLAS in generating production-grade, high-performance web applications without placeholder code or antipatterns.

### Architecture Tenets
1. **Zero Placeholders:** Never emit `// TODO: implement later` or stub functions without complete operational logic.
2. **Strict Type Safety:** TypeScript in strict mode (`"strict": true`, `"noImplicitAny": true`). All external data parsed with runtime validation (Zod).
3. **Defense in Depth:** Input sanitized on edge, validated on server, parameterized at database layer.
4. **Resilient Data Fetching:** Server-Side Rendering (SSR) for initial load and SEO, optimistic UI updates for client interactivity, and streaming boundaries with `Suspense`.

---

## 2. Next.js 15+ & React 19 Standards

### Server Components vs. Client Components
- **Default to React Server Components (RSC):** Keep data fetching, database queries, and private API keys on the server.
- **Use `'use client'` only at the leaves:** Isolate stateful interactive controls (buttons, forms, modal dialogs) to small client boundary components.
- **Server Actions for Mutations:** Handle form submissions and state changes with Server Actions, validating input with Zod and returning structured results `{ success: boolean, data?: T, error?: string }`.

```typescript
// app/actions/auth.ts
'use server'

import { z } from 'zod';
import { revalidatePath } from 'next/cache';

const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export async function loginAction(formData: FormData) {
  const result = LoginSchema.safeParse(Object.fromEntries(formData));
  if (!result.success) {
    return { success: false, error: result.error.flatten().fieldErrors };
  }
  // Server-side authentication logic ...
  revalidatePath('/dashboard');
  return { success: true };
}
```

---

## 3. High-Performance Backend: FastAPI & Python 3.12+

- **Async First:** Use `async def` for I/O-bound operations (database queries, external HTTP calls).
- **Dependency Injection:** Enforce authorization and database session lifecycles using `Depends()`.
- **Pydantic v2 Models:** Leverage strict validation and fast serialization.

```python
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

app = FastAPI(title="Spectre Core API", version="1.0.0")

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)

@app.post("/api/v1/users", status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: Annotated[AsyncSession, Depends(get_db_session)]):
    # Enforce duplicate checking and password hashing via Argon2id
    pass
```

---

## 4. Database Engineering & Performance

### PostgreSQL 17+ Best Practices
- **Connection Pooling:** Always utilize a connection pool (e.g. PgBouncer, asyncpg pool) with max connection limits tuned to CPU cores.
- **Indexing Guidelines:**
  - Standard equality/range lookups: **B-Tree** indices.
  - Full-text search or JSONB containment: **GIN** indices (`CREATE INDEX idx_data_gin ON records USING gin(metadata);`).
  - High-volume time-series / chronological logs: **BRIN** indices for minimal storage overhead.
- **Migrations:** Explicit forward and backward migrations using Prisma or Alembic. Never rely on automatic unsynced schema alterations in production.

---

## 5. Security & CSP Baseline for Web Deployments
Every production deployment must include strict HTTP headers:
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-...'; object-src 'none'; base-uri 'self';`
- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
