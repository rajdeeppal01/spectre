"""
SPECTRE Command Center — Local Antigravity AI Agent Command Center
Multi-project autonomous workspace powered by Gemini with live tool execution:

  ARCHITECT  — Full-stack web development intelligence (Daily use)
               Tools: run_command, write_file, read_file, list_directory
               Frameworks: React 19, Next.js 15, FastAPI, TypeScript, Tailwind 4

  SPECTRE    — Offensive security & penetration testing intelligence (Weekly use)
               Tools: run_command, write_file, read_file, list_directory
               Pipelines: Nmap recon, CVE analysis, PQC cryptography, Quantum RNG, Doctor

Active Workspace Projects Pre-loaded:
  1. spectre          - C:\\Users\\rajde\\.gemini\\antigravity-ide\\scratch\\spectre
  2. trackrai         - C:\\Users\\rajde\\OneDrive\\Desktop\\projects\\trackrai
  3. forgeai          - C:\\Users\\rajde\\OneDrive\\Desktop\\projects\\forgeai
  4. cybersentinel-ai - C:\\Users\\rajde\\OneDrive\\Desktop\\projects\\cybersentinel-ai
  5. portfolio        - C:\\Users\\rajde\\OneDrive\\Desktop\\projects\\portfolio
  6. resumes          - C:\\Users\\rajde\\OneDrive\\Desktop\\the life\\resumes
"""

import argparse
import json
import os
import sys
import time
import uuid
import webbrowser
import threading
import subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests as _requests

# Fix Windows console UTF-8 output if possible
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --- Paths ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DASH_HTML = ROOT / "dashboard" / "index.html"
PROJECTS_CONFIG = ROOT / "infrastructure" / "projects.json"
sys.path.insert(0, str(ROOT / "scripts"))

# --- Load .env -----------------------------------------------------------------

def _load_env() -> dict:
    env: dict = {}
    for candidate in [ROOT / "infrastructure" / ".env", ROOT / ".env"]:
        if candidate.exists():
            for raw in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
            break
    return env

_ENV = _load_env()
GEMINI_API_KEY = _ENV.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# Multi-model failover pool protects against 429 quota exhaustion and model outages
MODEL_FAILOVER_POOL = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
]
ACTIVE_MODEL = MODEL_FAILOVER_POOL[0]

# --- Multi-Project Registry ---------------------------------------------------

DEFAULT_PROJECTS = {
    "spectre": {
        "id": "spectre",
        "name": "spectre",
        "title": "SPECTRE Command Center",
        "path": str(ROOT),
        "category": "Cyber & PQC",
        "description": "Offensive Security, Post-Quantum Cryptography & AI Agent Workspace",
        "pinned": True,
        "icon": "🔒"
    },
    "trackrai": {
        "id": "trackrai",
        "name": "trackrai",
        "title": "TrackrAI Application",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\trackrai",
        "category": "Full-Stack Web App",
        "description": "Next.js 15 frontend, Python backend, Docker compose & query stats",
        "pinned": True,
        "icon": "⚡"
    },
    "forgeai": {
        "id": "forgeai",
        "name": "forgeai",
        "title": "ForgeAI Playbooks",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\forgeai",
        "category": "AI Automation",
        "description": "Custom agent playbooks, dashboard UI, onboarding workflows & API",
        "pinned": True,
        "icon": "🛠️"
    },
    "cybersentinel-ai": {
        "id": "cybersentinel-ai",
        "name": "cybersentinel-ai",
        "title": "Cyber Sentinel AI",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\cybersentinel-ai",
        "category": "Security Studio",
        "description": "Vite + React + TypeScript cyber defense & continuous monitoring suite",
        "pinned": True,
        "icon": "🛡️"
    },
    "portfolio": {
        "id": "portfolio",
        "name": "portfolio",
        "title": "Developer Portfolio",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\portfolio",
        "category": "Web Portfolio",
        "description": "Personal developer portfolio and responsive web applications",
        "pinned": True,
        "icon": "💼"
    },
    "resumes": {
        "id": "resumes",
        "name": "resumes",
        "title": "Accessing Resumes",
        "path": r"C:\Users\rajde\OneDrive\Desktop\the life\resumes",
        "category": "Career & Documents",
        "description": "SDE, Razorpay & technical resumes, career documents and ATS matching",
        "pinned": True,
        "icon": "📄"
    }
}

def detect_project_stack(p: Path) -> list:
    badges = []
    if not p.exists():
        return badges
    try:
        names = {f.name.lower() for f in p.iterdir()}
        if 'next.config.js' in names or 'next.config.mjs' in names or 'frontend-next' in names:
            badges.append('Next.js')
        if 'vite.config.ts' in names or 'vite.config.js' in names:
            badges.append('Vite')
        if 'package.json' in names:
            badges.append('React / TS')
        if 'requirements.txt' in names or any(f.endswith('.py') for f in names):
            badges.append('Python')
        if 'docker-compose.yml' in names or 'dockerfile' in names:
            badges.append('Docker')
        if any(f.endswith('.pdf') for f in names):
            badges.append('PDF / Docs')
    except Exception:
        pass
    return badges or ['Workspace']

def _load_projects_registry() -> dict:
    projects = dict(DEFAULT_PROJECTS)
    if PROJECTS_CONFIG.exists():
        try:
            saved = json.loads(PROJECTS_CONFIG.read_text(encoding="utf-8", errors="replace"))
            projects.update(saved)
        except Exception:
            pass

    # Auto-discover other desktop projects
    desktop_projects_dir = Path(r"C:\Users\rajde\OneDrive\Desktop\projects")
    if desktop_projects_dir.exists():
        try:
            for item in desktop_projects_dir.iterdir():
                if item.is_dir() and item.name not in projects and not item.name.startswith("."):
                    projects[item.name] = {
                        "id": item.name,
                        "name": item.name,
                        "title": item.name.replace("-", " ").title(),
                        "path": str(item),
                        "category": "Desktop Project",
                        "description": f"Auto-detected project at {item}",
                        "pinned": False,
                        "icon": "📁"
                    }
        except Exception:
            pass

    # Annotate with real existence, file counts, and tech badges
    for pid, pdata in projects.items():
        ppath = Path(pdata["path"])
        pdata["exists"] = ppath.exists()
        pdata["badges"] = detect_project_stack(ppath)
        try:
            if pdata["exists"]:
                pdata["files_count"] = len([f for f in ppath.iterdir() if f.is_file()])
            else:
                pdata["files_count"] = 0
        except Exception:
            pdata["files_count"] = 0

    return projects

_PROJECTS = _load_projects_registry()
_ACTIVE_PROJECT_ID = "spectre"
_projects_lock = threading.Lock()

def get_active_project() -> dict:
    with _projects_lock:
        return _PROJECTS.get(_ACTIVE_PROJECT_ID, DEFAULT_PROJECTS["spectre"])

def get_active_project_path() -> Path:
    proj = get_active_project()
    p = Path(proj["path"])
    return p if p.exists() else ROOT

def set_active_project(project_id: str) -> dict:
    global _ACTIVE_PROJECT_ID
    with _projects_lock:
        if project_id in _PROJECTS:
            _ACTIVE_PROJECT_ID = project_id
            return _PROJECTS[project_id]
        raise ValueError(f"Project '{project_id}' not found in registry.")

def add_custom_project(name: str, path_str: str) -> dict:
    target = Path(path_str).resolve()
    if not target.exists() or not target.is_dir():
        raise ValueError(f"Path does not exist or is not a directory: {path_str}")
    pid = name.lower().replace(" ", "-")
    entry = {
        "id": pid,
        "name": name,
        "title": name.title(),
        "path": str(target),
        "category": "Custom Project",
        "description": f"User workspace at {target}",
        "pinned": True,
        "icon": "📁",
        "exists": True,
        "badges": detect_project_stack(target),
        "files_count": 0
    }
    with _projects_lock:
        _PROJECTS[pid] = entry
        try:
            PROJECTS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            PROJECTS_CONFIG.write_text(json.dumps(_PROJECTS, indent=2), encoding="utf-8")
        except Exception:
            pass
    return entry


# --- Agent System Prompts ------------------------------------------------------

SYSTEM_PROMPTS = {
    "webdev": """\
You are ARCHITECT, an elite autonomous web development agent inside the local Antigravity workspace.
You actively complete full-stack development tasks using your tools rather than just giving advice.

YOUR TOOLKIT:
- run_command: Execute PowerShell / shell commands in the currently active project directory (npm, npx, python, git, docker, etc.)
- write_file: Write or create production-ready source code files directly into the active project
- read_file: Read existing files, configs, and package.json to understand the active project
- list_directory: Explore directories and files in the active project

STANDARDS:
1. When asked to create, edit, or scaffold, USE YOUR TOOLS to inspect the workspace, create files, or run commands.
2. ZERO PLACEHOLDERS: Always write 100% complete files without '// TODO' or '# implement here'.
3. Always verify commands before reporting completion.
4. You are operating on Windows; all shell commands run in PowerShell.
""",

    "pentest": """\
You are SPECTRE, an elite autonomous offensive security & penetration testing agent inside the Antigravity workspace.
You actively run scans, audits, recon, and vulnerability verification using your tools.

YOUR TOOLKIT:
- run_command: Execute security tools and Python automation scripts in the active project directory
- write_file: Save scan reports, custom exploits, or security patch scripts
- read_file: Read scan outputs, XML reports, or target configuration files
- list_directory: Browse reports, logs, and workspace assets

BUILT-IN WORKSPACE CAPABILITIES:
- Target Recon & Port Scan : python scripts/recon_pipeline.py --target <IP_OR_HOST>
- Post-Quantum Crypto Audit : python scripts/pqc_audit.py --path .
- ANU Quantum Entropy Keys  : python scripts/quantum_rng.py --aes-key
- System Health Diagnostics : python scripts/spectre_doctor.py
- Continuous Security Guard : python scripts/continuous_security.py --watch .

STANDARDS:
1. When asked to audit, scan, investigate, or verify, USE YOUR TOOLS to execute the appropriate script or command.
2. Pair every vulnerability with CVE ID, CVSS v3.1 score, and actionable remediation code.
3. Map offensive findings to MITRE ATT&CK tactics & techniques.
4. Always analyze real scan output returned by your tools rather than guessing.
5. You are operating on Windows with Python 3.14 and PowerShell available.
"""
}

# --- Tool Declarations for Gemini Function Calling -----------------------------

GEMINI_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "run_command",
                "description": "Execute a shell command (PowerShell / Python / Nmap / npm) in the active project workspace. Use this to run scans, automation scripts, tests, web servers, or file operations.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {
                            "type": "STRING",
                            "description": "The exact shell command to execute in PowerShell."
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "write_file",
                "description": "Write or create a file in the active project workspace. Creates parent directories automatically.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {
                            "type": "STRING",
                            "description": "Relative path to file in active workspace (e.g. 'src/components/Header.tsx' or 'reports/scan.txt')."
                        },
                        "content": {
                            "type": "STRING",
                            "description": "Complete file content to write (no placeholders)."
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "read_file",
                "description": "Read text content of a file in the active project workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {
                            "type": "STRING",
                            "description": "Relative path to file in active workspace."
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_directory",
                "description": "List files and subdirectories in the active project workspace folder.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {
                            "type": "STRING",
                            "description": "Relative directory path (e.g. '.' or 'src' or 'api'). Default is '.'"
                        }
                    }
                }
            }
        ]
    }
]

# --- Safe Tool Execution Engine Scoped to Active Project -----------------------

def _safe_resolve_path(rel_path: str) -> Path:
    active_root = get_active_project_path()
    p = (active_root / rel_path).resolve()
    return p

def _exec_run_command(command: str, timeout: int = 120) -> dict:
    t0 = time.time()
    active_dir = get_active_project_path()
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(active_dir),
            errors="replace",
            timeout=timeout
        )
        duration = round(time.time() - t0, 2)
        out = (res.stdout + res.stderr).strip()
        if not out:
            out = "(Command completed with no output)"
        return {
            "output": out[:8000],
            "exit_code": res.returncode,
            "duration": duration,
            "command": command,
            "cwd": str(active_dir)
        }
    except subprocess.TimeoutExpired:
        return {
            "output": f"Command timed out after {timeout} seconds.",
            "exit_code": 124,
            "duration": round(time.time() - t0, 2),
            "command": command,
            "cwd": str(active_dir)
        }
    except Exception as exc:
        return {
            "output": f"Execution error: {exc}",
            "exit_code": 1,
            "duration": round(time.time() - t0, 2),
            "command": command,
            "cwd": str(active_dir)
        }

def _exec_write_file(rel_path: str, content: str) -> dict:
    t0 = time.time()
    try:
        target = _safe_resolve_path(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", errors="replace")
        return {
            "output": f"Successfully wrote {len(content)} characters to {rel_path} in {target.parent.name}",
            "exit_code": 0,
            "duration": round(time.time() - t0, 2),
            "path": rel_path
        }
    except Exception as exc:
        return {
            "output": f"Failed to write file: {exc}",
            "exit_code": 1,
            "duration": round(time.time() - t0, 2),
            "path": rel_path
        }

def _exec_read_file(rel_path: str) -> dict:
    t0 = time.time()
    try:
        target = _safe_resolve_path(rel_path)
        if not target.exists():
            return {
                "output": f"File '{rel_path}' not found in active project ({target.parent}).",
                "exit_code": 1,
                "duration": round(time.time() - t0, 2),
                "path": rel_path
            }
        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > 10000:
            preview = content[:10000] + f"\n... [Truncated: {len(content)} total characters]"
        else:
            preview = content
        return {
            "output": preview,
            "exit_code": 0,
            "duration": round(time.time() - t0, 2),
            "path": rel_path
        }
    except Exception as exc:
        return {
            "output": f"Failed to read file: {exc}",
            "exit_code": 1,
            "duration": round(time.time() - t0, 2),
            "path": rel_path
        }

def _exec_list_dir(rel_path: str = ".") -> dict:
    t0 = time.time()
    try:
        target = _safe_resolve_path(rel_path or ".")
        if not target.is_dir():
            return {
                "output": f"'{rel_path}' is not a directory in {target.parent}.",
                "exit_code": 1,
                "duration": round(time.time() - t0, 2)
            }
        entries = []
        for p in sorted(target.iterdir()):
            if p.name in (".git", "__pycache__", "node_modules", ".venv"):
                continue
            kind = "[DIR]" if p.is_dir() else "[FILE]"
            size = f"{p.stat().st_size}B" if p.is_file() else ""
            entries.append(f"{kind:<7} {p.name:<30} {size}")
        return {
            "output": "\n".join(entries) if entries else "(Empty directory)",
            "exit_code": 0,
            "duration": round(time.time() - t0, 2)
        }
    except Exception as exc:
        return {
            "output": f"Failed to list directory: {exc}",
            "exit_code": 1,
            "duration": round(time.time() - t0, 2)
        }

def _dispatch_tool(name: str, args: dict) -> dict:
    if name == "run_command":
        return _exec_run_command(args.get("command", ""))
    elif name == "write_file":
        return _exec_write_file(args.get("path", ""), args.get("content", ""))
    elif name == "read_file":
        return _exec_read_file(args.get("path", ""))
    elif name == "list_directory":
        return _exec_list_dir(args.get("path", "."))
    else:
        return {"output": f"Unknown tool: {name}", "exit_code": 1, "duration": 0.0}

# --- Multi-Turn Agentic Chat Engine with SSE Streaming -------------------------

_sessions: dict[str, list] = {}
_sessions_lock = threading.Lock()

def _call_gemini_with_failover(payload: dict) -> tuple[dict | None, str | None]:
    """Execute generateContent with automatic model failover across MODEL_FAILOVER_POOL."""
    global ACTIVE_MODEL
    # Try ACTIVE_MODEL first, followed by the rest of the pool
    candidates = [ACTIVE_MODEL] + [m for m in MODEL_FAILOVER_POOL if m != ACTIVE_MODEL]
    last_err = ""

    for cand in candidates:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{cand}:generateContent?key={GEMINI_API_KEY}"
        try:
            resp = _requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                if cand != ACTIVE_MODEL:
                    print(f"[*] Gemini model failover successful: switched from {ACTIVE_MODEL} -> {cand}")
                    ACTIVE_MODEL = cand
                return resp.json(), None
            elif resp.status_code in (429, 404, 503):
                err_data = resp.json().get("error", {})
                last_err = f"{cand} (HTTP {resp.status_code}): {err_data.get('message', resp.text)}"
                print(f"[!] Quota/Availability issue on {cand} ({resp.status_code}). Failing over to next candidate...")
                continue
            else:
                err_data = resp.json().get("error", {})
                last_err = f"{cand} (HTTP {resp.status_code}): {err_data.get('message', resp.text)}"
                print(f"[!] Error on {cand} ({resp.status_code}): {last_err}. Trying other models...")
                continue
        except Exception as exc:
            last_err = f"{cand} connection error: {exc}"
            continue

    return None, last_err


def _stream_agent_task(agent: str, sid: str, user_prompt: str):
    if not GEMINI_API_KEY:
        yield {"type": "error", "message": "No Gemini API key found in infrastructure/.env"}
        return

    active_proj = get_active_project()
    active_path = str(get_active_project_path())

    # Build active project context
    project_context = (
        f"\n\nCURRENT ACTIVE WORKSPACE:\n"
        f"- Project Name: {active_proj['name']}\n"
        f"- Root Path: {active_path}\n"
        f"- Stack Tags: {', '.join(active_proj.get('badges', []))}\n"
        f"All your tool actions (run_command, write_file, read_file, list_directory) execute inside this active project's directory."
    )

    base_system = SYSTEM_PROMPTS.get(agent, SYSTEM_PROMPTS["webdev"])
    system_instruction = base_system + project_context

    with _sessions_lock:
        history = _sessions.setdefault(sid, [])
        history.append({"role": "user", "parts": [{"text": user_prompt}]})
        contents = list(history)

    max_tool_turns = 8
    current_turn = 0

    while current_turn < max_tool_turns:
        current_turn += 1

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "tools": GEMINI_TOOLS,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 8192
            }
        }

        res_json, err_msg = _call_gemini_with_failover(payload)
        if not res_json:
            yield {"type": "error", "message": f"Gemini API Error (all failovers exhausted): {err_msg}"}
            return

        candidate = res_json.get("candidates", [{}])[0]
        model_content = candidate.get("content", {})
        parts = model_content.get("parts", [])

        function_calls = [p for p in parts if "functionCall" in p]

        if function_calls:
            contents.append(model_content)
            fr_parts = []
            for p in function_calls:
                fc = p["functionCall"]
                name = fc.get("name", "")
                args = fc.get("args", {})
                call_id = fc.get("id")

                yield {
                    "type": "tool_call",
                    "name": name,
                    "args": args,
                    "id": call_id or str(uuid.uuid4())
                }

                result = _dispatch_tool(name, args)

                yield {
                    "type": "tool_result",
                    "name": name,
                    "output": result.get("output", ""),
                    "exit_code": result.get("exit_code", 0),
                    "duration": result.get("duration", 0.0),
                    "id": call_id
                }

                fr_item = {
                    "name": name,
                    "response": {
                        "name": name,
                        "content": {
                            "output": result.get("output", ""),
                            "exit_code": result.get("exit_code", 0)
                        }
                    }
                }
                if call_id:
                    fr_item["id"] = call_id

                fr_parts.append({"functionResponse": fr_item})

            contents.append({"role": "user", "parts": fr_parts})

            # If we've reached max tool turns, force a final response synthesis
            if current_turn >= max_tool_turns:
                synth_payload = {
                    "systemInstruction": {"parts": [{"text": system_instruction}]},
                    "contents": contents + [{
                        "role": "user",
                        "parts": [{"text": "You have completed your tool inspections. Provide your final comprehensive status and report directly to the user now in clear markdown."}]
                    }],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 8192
                    }
                }
                res_synth, _ = _call_gemini_with_failover(synth_payload)
                if res_synth:
                    cand_synth = res_synth.get("candidates", [{}])[0]
                    synth_content = cand_synth.get("content", {})
                    text_parts = [p.get("text", "") for p in synth_content.get("parts", []) if "text" in p]
                    full_text = "".join(text_parts)
                    if full_text:
                        chunk_size = 32
                        for i in range(0, len(full_text), chunk_size):
                            yield {"type": "text", "text": full_text[i:i + chunk_size]}
                            time.sleep(0.015)
                        contents.append(synth_content)
                break

            continue

        else:
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            full_text = "".join(text_parts)
            if not full_text:
                full_text = "Task execution completed."

            chunk_size = 32
            for i in range(0, len(full_text), chunk_size):
                yield {"type": "text", "text": full_text[i:i + chunk_size]}
                time.sleep(0.015)

            contents.append(model_content)
            break

    with _sessions_lock:
        _sessions[sid] = contents


_cached_health_score = 50
_last_health_check = 0

def _get_cached_health() -> int:
    global _cached_health_score, _last_health_check
    now = time.time()
    if now - _last_health_check > 180:
        _last_health_check = now
        def _calc():
            global _cached_health_score
            try:
                from spectre_doctor import run_diagnostics
                diag = run_diagnostics()
                _cached_health_score = diag.get("overall_score", 50)
            except Exception:
                pass
        threading.Thread(target=_calc, daemon=True).start()
    return _cached_health_score


# --- HTTP Server Handler -------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_resp(self, data, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path in ("/", "/index.html"):
            if DASH_HTML.exists():
                html = DASH_HTML.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self._cors_headers()
                self.end_headers()
                self.wfile.write(html)
            else:
                self._json_resp({"error": "Dashboard HTML not found"}, 404)

        elif path == "/api/status":
            score = _get_cached_health()
            active_proj = get_active_project()
            active_path = get_active_project_path()

            self._json_resp({
                "api_key": bool(GEMINI_API_KEY),
                "model": ACTIVE_MODEL,
                "failover_pool": MODEL_FAILOVER_POOL,
                "sessions": len(_sessions),
                "health": score,
                "active_project": active_proj,
                "active_path": str(active_path)
            })

        elif path == "/api/projects":
            with _projects_lock:
                proj_list = sorted(list(_PROJECTS.values()), key=lambda x: (not x.get("pinned", False), x["name"]))
            self._json_resp({
                "active": _ACTIVE_PROJECT_ID,
                "active_project": get_active_project(),
                "projects": proj_list
            })

        elif path == "/api/workspace/files":
            active_dir = get_active_project_path()
            files_tree = []
            try:
                for item in sorted(active_dir.iterdir()):
                    if item.name.startswith(".") or item.name in ("__pycache__", "node_modules"):
                        continue
                    if item.is_dir():
                        subfiles = [f.name for f in item.iterdir() if f.is_file() and not f.name.startswith(".")][:15]
                        files_tree.append({"dir": item.name, "count": len(subfiles), "files": subfiles})
            except Exception:
                pass
            self._json_resp({
                "workspace": str(active_dir),
                "project": get_active_project()["name"],
                "structure": files_tree
            })

        elif path == "/api/qrng":
            try:
                from quantum_rng import generate_aes256_gcm_bundle
                self._json_resp(generate_aes256_gcm_bundle())
            except Exception as exc:
                import secrets
                self._json_resp({
                    "key_hex": secrets.token_hex(32),
                    "iv_hex": secrets.token_hex(12),
                    "source": f"OS CSPRNG (Fallback: {exc})"
                })

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path == "/api/chat":
            self._handle_chat_stream(body)

        elif path == "/api/projects/select":
            pid = body.get("id", "").strip()
            try:
                proj = set_active_project(pid)
                self._json_resp({"ok": True, "active": proj})
            except Exception as exc:
                self._json_resp({"error": str(exc)}, 400)

        elif path == "/api/projects/add":
            name = body.get("name", "").strip()
            path_str = body.get("path", "").strip()
            if not name or not path_str:
                self._json_resp({"error": "name and path required"}, 400)
                return
            try:
                proj = add_custom_project(name, path_str)
                self._json_resp({"ok": True, "project": proj})
            except Exception as exc:
                self._json_resp({"error": str(exc)}, 400)

        elif path == "/api/terminal/run":
            cmd = body.get("command", "").strip()
            if not cmd:
                self._json_resp({"error": "No command provided"}, 400)
                return
            res = _exec_run_command(cmd)
            self._json_resp(res)

        elif path == "/api/file/save":
            file_path = body.get("path", "").strip()
            content = body.get("content", "")
            if not file_path:
                self._json_resp({"error": "No file path provided"}, 400)
                return
            res = _exec_write_file(file_path, content)
            self._json_resp(res)

        elif path == "/api/session/clear":
            sid = body.get("sessionId", "")
            with _sessions_lock:
                _sessions.pop(sid, None)
            self._json_resp({"ok": True})

        else:
            self.send_response(404)
            self.end_headers()

    def _handle_chat_stream(self, body: dict):
        agent = body.get("agent", "webdev")
        message = body.get("message", "").strip()
        sid = body.get("sessionId") or str(uuid.uuid4())

        if not message:
            self._json_resp({"error": "Empty message"}, 400)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors_headers()
        self.end_headers()

        try:
            for event in _stream_agent_task(agent, sid, message):
                payload = json.dumps(event, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

        try:
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass


# --- CLI Matrix ----------------------------------------------------------------

def _print_cli_matrix():
    print("=" * 75)
    print("        SPECTRE ECOSYSTEM -- MULTI-PROJECT ANTIGRAVITY ENGINE          ")
    print("=" * 75)
    print("LOADED WORKSPACES:")
    for pid, p in DEFAULT_PROJECTS.items():
        exists_mark = "[READY]" if Path(p["path"]).exists() else "[MISSING]"
        print(f"  * {p['icon']} {p['name']:<18} : {p['category']:<20} {exists_mark}")
        print(f"      Path: {p['path']}")
    print("-" * 75)
    print("AUTONOMOUS AGENT PAIR:")
    print("  * ARCHITECT (Web Dev) : Scaffolds, refactors & audits web codebases")
    print("  * SPECTRE   (Pentest) : Scans, exploits, audits PQC & tests targets")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Multi-Project Antigravity Command Center")
    parser.add_argument("--port", type=int, default=5050, help="HTTP port (default 5050)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    parser.add_argument("--cli", action="store_true", help="Print terminal architecture matrix only")
    args = parser.parse_args()

    _print_cli_matrix()

    if args.cli:
        return

    if not GEMINI_API_KEY:
        print("\n[!] WARNING: GEMINI_API_KEY not found in infrastructure/.env\n")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), _Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"\n[+] SPECTRE Antigravity Command Center -> {url}")
    print(f"    Active Model : {ACTIVE_MODEL} (Failover Pool: {len(MODEL_FAILOVER_POOL)} models)")
    print(f"    Active Workspace : {_ACTIVE_PROJECT_ID} ({get_active_project_path()})")
    print("    Press Ctrl+C to stop.\n")

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
