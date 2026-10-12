"""
SPECTRE — Full-Stack Web Development Studio Bridge (MODE A & MODE C)
Optimized for React/Next.js 15, TypeScript, TailwindCSS, and FastAPI.
Generates production-ready, zero-placeholder code with automatic
pre-save security verification through SPECTRE.

Usage:
    python scripts/web_dev_studio.py --scaffold nextjs --name my-dashboard
    python scripts/web_dev_studio.py --scaffold fastapi --name secure-api
    python scripts/web_dev_studio.py --generate component --prompt "Dark mode analytics card with responsive chart" --out ./src/Card.tsx
    python scripts/web_dev_studio.py --generate api --prompt "JWT auth with Argon2id and rate-limiting" --out ./api/auth.py
    python scripts/web_dev_studio.py --audit ./src/Card.tsx
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

# Import SPECTRE continuous security scanner for pre-save verification
try:
    from continuous_security import scan_file_content
except ImportError:
    # If run from root directory
    sys.path.insert(0, str(Path(__file__).parent))
    from continuous_security import scan_file_content

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://localhost:4000")
OLLAMA_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

WEB_DEV_SYSTEM_PROMPT = """You are ARCHITECT, an elite senior full-stack web developer and system architect.
Tech Stack Expertise: React 19, Next.js 15 App Router, TypeScript 5 (strict mode), TailwindCSS 4, FastAPI, SQLAlchemy 2.0, PostgreSQL, Zod, and Pydantic v2.

Non-Negotiable Rules:
1. ZERO PLACEHOLDERS: Never emit '// TODO: implement' or stub functions. Complete every function and handler fully.
2. Production-Grade: Include comprehensive error handling, loading states, and full TypeScript typings.
3. Modern Aesthetics: Use sleek dark modes, Tailwind utility classes, subtle borders, glassmorphic backdrops (backdrop-blur-md), and smooth transitions.
4. Security First: Prevent XSS, SQLi, CSRF, and prototype pollution. Validate all user inputs.
5. Return ONLY the complete code inside a single code block without markdown fluff."""


def query_llm(prompt: str, model: str = "gemini-pro") -> str:
    """Routes generation request through LiteLLM proxy or local Ollama."""
    # Attempt LiteLLM (:4000) first
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": WEB_DEV_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        req = urllib.request.Request(
            f"{LITELLM_BASE}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer none"}
        )
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception:
        # Fallback to local Ollama (architect / devstral)
        fallback_model = "architect" if model != "architect" else "devstral:7b"
        print(f"[*] LiteLLM unreachable; falling back to local Ollama model '{fallback_model}'...")
        ollama_payload = {
            "model": fallback_model,
            "messages": [
                {"role": "system", "content": WEB_DEV_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 2048}
        }
        try:
            req = urllib.request.Request(
                f"{OLLAMA_BASE}/api/chat",
                data=json.dumps(ollama_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except Exception as e2:
            return f"// Error: All LLM endpoints unreachable ({e2})"


def clean_code_block(raw: str) -> str:
    """Extract code from markdown code fences if present."""
    lines = raw.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def verify_and_save(file_path: Path, code: str) -> bool:
    """
    MODE C Synergy: Performs pre-save security scan before committing code to disk.
    If critical security flaws are detected, aborts or flags immediately.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = file_path.with_suffix(file_path.suffix + ".tmp")
    temp_file.write_text(code, encoding="utf-8")

    findings = scan_file_content(temp_file)
    temp_file.unlink(missing_ok=True)

    critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
    if critical_count > 0:
        print(f"\n[!] PRE-SAVE SECURITY REJECTION: {critical_count} CRITICAL flaws detected in generated code!")
        for f in findings:
            print(f"    - [{f['severity']}] {f['name']}: {f['remediation']}")
        print("[!] File NOT written to disk until sanitized.")
        return False

    file_path.write_text(code, encoding="utf-8")
    print(f"[+] Security Verified by SPECTRE: Saved {file_path}")
    if findings:
        print(f"    (Notice: {len(findings)} non-critical warnings noted)")
    return True


# ── Full-Stack Project Templates ─────────────────────────────────────

NEXTJS_PACKAGE_JSON = """{
  "name": "{name}",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.460.0",
    "zod": "^3.23.8",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.6.0",
    "tailwindcss": "^3.4.14",
    "postcss": "^8.4.47",
    "autoprefixer": "^10.4.20"
  }
}"""

FASTAPI_MAIN_PY = '''"""
SPECTRE — High-Performance Async FastAPI Backend
Production-ready with CORS, structured error handling, and Pydantic v2 validation.
"""

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
import os

app = FastAPI(
    title="{name}",
    version="1.0.0",
    description="High-performance, secure backend engineered with SPECTRE standards."
)

# CORS Configuration — strict origin binding
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    version: str

@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
async def health_check():
    return {"status": "operational", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
'''


def scaffold_nextjs(project_name: str, dest_dir: Path):
    """Scaffolds modern Next.js 15 App Router project structure."""
    target = dest_dir / project_name
    target.mkdir(parents=True, exist_ok=True)

    print(f"[*] Scaffolding Next.js 15 App Router project at {target}...")

    # package.json
    (target / "package.json").write_text(NEXTJS_PACKAGE_JSON.replace("{name}", project_name), encoding="utf-8")

    # tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "target": "ES2022",
            "lib": ["dom", "dom.iterable", "esnext"],
            "allowJs": True,
            "skipLibCheck": True,
            "strict": True,
            "noEmit": True,
            "esModuleInterop": True,
            "module": "esnext",
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "jsx": "preserve",
            "incremental": True,
            "plugins": [{"name": "next"}],
            "paths": {"@/*": ["./*"]}
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"]
    }
    (target / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2), encoding="utf-8")

    # app/layout.tsx
    app_dir = target / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    layout_tsx = """import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '""" + project_name.title() + """ — SPECTRE Workspace',
  description: 'Built with high-performance Next.js 15 and TailwindCSS.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-cyan-500/30 selection:text-cyan-300">
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
"""
    (app_dir / "layout.tsx").write_text(layout_tsx, encoding="utf-8")

    # app/page.tsx
    page_tsx = """import React from 'react';
import { ShieldCheck, Cpu, Terminal, Zap } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="relative overflow-hidden rounded-2xl border border-cyan-500/20 bg-slate-900/50 p-8 backdrop-blur-xl shadow-2xl">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3 py-1 text-xs font-medium text-cyan-400 mb-4">
          <Zap className="h-3.5 w-3.5" />
          SPECTRE Web Studio Engine
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
          """ + project_name.title() + """
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-400">
          Zero-placeholder, security-audited full-stack architecture running Next.js 15, React 19, and TailwindCSS.
        </p>
      </section>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md">
          <ShieldCheck className="h-8 w-8 text-emerald-400 mb-3" />
          <h3 className="text-lg font-semibold text-white">Pre-Save Audited</h3>
          <p className="mt-2 text-sm text-slate-400">Continuous security verification ensures zero XSS, SQLi, or auth flaws.</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md">
          <Cpu className="h-8 w-8 text-cyan-400 mb-3" />
          <h3 className="text-lg font-semibold text-white">RSC First</h3>
          <p className="mt-2 text-sm text-slate-400">React Server Components for instant data loading and high SEO performance.</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md">
          <Terminal className="h-8 w-8 text-purple-400 mb-3" />
          <h3 className="text-lg font-semibold text-white">Strict TypeScript</h3>
          <p className="mt-2 text-sm text-slate-400">End-to-end typed schemas with Zod runtime validation.</p>
        </div>
      </div>
    </div>
  );
}
"""
    (app_dir / "page.tsx").write_text(page_tsx, encoding="utf-8")

    # app/globals.css
    globals_css = """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: dark;
}
"""
    (app_dir / "globals.css").write_text(globals_css, encoding="utf-8")

    print(f"[+] Scaffolding complete: {target}")
    print(f"    To run: cd {project_name} && npm install && npm run dev")


def scaffold_fastapi(project_name: str, dest_dir: Path):
    """Scaffolds modern FastAPI backend structure."""
    target = dest_dir / project_name
    target.mkdir(parents=True, exist_ok=True)

    print(f"[*] Scaffolding FastAPI backend at {target}...")
    (target / "main.py").write_text(FASTAPI_MAIN_PY.replace("{name}", project_name), encoding="utf-8")

    reqs = "fastapi>=0.110.0\nuvicorn>=0.28.0\npydantic>=2.6.0\npython-dotenv>=1.0.1\npasslib>=1.7.4\nbcrypt>=4.1.2\npyjwt>=2.8.0\n"
    (target / "requirements.txt").write_text(reqs, encoding="utf-8")

    print(f"[+] Scaffolding complete: {target}")
    print(f"    To run: cd {project_name} && pip install -r requirements.txt && python main.py")


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Full-Stack Web Dev Studio Bridge")
    parser.add_argument("--scaffold", choices=["nextjs", "fastapi"], help="Scaffold a new full-stack project template")
    parser.add_argument("--name", default="spectre-app", help="Project name for scaffolding")
    parser.add_argument("--dest", default=".", help="Destination directory (default: .)")
    parser.add_argument("--generate", choices=["component", "api", "schema"], help="Generate a web development element via AI")
    parser.add_argument("--prompt", help="Natural language description of the component or API to generate")
    parser.add_argument("--out", help="Output file path to save verified generated code")
    parser.add_argument("--model", default="gemini-pro", help="AI model to query (gemini-pro, architect)")
    parser.add_argument("--audit", help="Audit an existing component or API file for security & code quality")

    args = parser.parse_args()

    if args.scaffold == "nextjs":
        scaffold_nextjs(args.name, Path(args.dest))
        return

    if args.scaffold == "fastapi":
        scaffold_fastapi(args.name, Path(args.dest))
        return

    if args.audit:
        target = Path(args.audit)
        print(f"[*] Auditing web source file: {target}...")
        findings = scan_file_content(target)
        if not findings:
            print("[+] Clean! Zero security vulnerabilities detected.")
        else:
            print(f"[!] Found {len(findings)} issues:")
            for f in findings:
                print(f"    - [{f['severity']}] Line {f['line']}: {f['name']} -> {f['remediation']}")
        return

    if args.generate:
        if not args.prompt:
            print("[!] Please provide a --prompt describing what to generate.")
            return

        print(f"[*] Querying AI ({args.model}) for {args.generate}: '{args.prompt}'...")
        prompt_full = f"Generate a production-ready, zero-placeholder {args.generate} for: {args.prompt}"
        raw_code = query_llm(prompt_full, model=args.model)
        code = clean_code_block(raw_code)

        if args.out:
            dest_path = Path(args.out)
            verify_and_save(dest_path, code)
        else:
            print("\n" + "=" * 70)
            print(code)
            print("=" * 70)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
