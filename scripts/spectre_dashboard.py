"""
SPECTRE Command Center — Local Antigravity AI Agent Command Center
Autonomous dual-agent workspace powered by Gemini with live tool execution:

  ARCHITECT  — Full-stack web development intelligence (Daily use)
               Tools: run_command, write_file, read_file, list_directory
               Frameworks: React 19, Next.js 15, FastAPI, TypeScript, Tailwind 4

  SPECTRE    — Offensive security & penetration testing intelligence (Weekly use)
               Tools: run_command, write_file, read_file, list_directory
               Pipelines: Nmap recon, CVE analysis, PQC cryptography, Quantum RNG, Doctor

Usage:
    python scripts/spectre_dashboard.py            # web UI on :5050
    python scripts/spectre_dashboard.py --port 8080
    python scripts/spectre_dashboard.py --cli       # terminal matrix
    python scripts/spectre_dashboard.py --no-browser
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
ACTIVE_MODEL = "gemini-3.5-flash"  # Fast, reliable, supports function calling + thought signatures

# --- Agent System Prompts ------------------------------------------------------

SYSTEM_PROMPTS = {
    "webdev": """\
You are ARCHITECT, an elite autonomous web development agent inside the local SPECTRE Antigravity workspace.
You do not just give passive advice; you ACTIVELY COMPLETE DEVELOPMENT TASKS using your workspace tools.

YOUR TOOLKIT:
- run_command: Execute PowerShell / shell commands in the workspace (npm, npx, python, git, etc.)
- write_file: Write or create production-ready source code files directly into the workspace
- read_file: Read existing files, configs, and package.json to understand the project structure
- list_directory: Explore directories and files in the workspace

CORE STACK:
- React 19, Next.js 15 (App Router, Server Actions, RSC), TypeScript 5.x
- TailwindCSS 4, Framer Motion, Radix UI / shadcn/ui
- FastAPI, SQLAlchemy 2.0, PostgreSQL, Pydantic v2
- Workspace Scaffolder: python scripts/web_dev_studio.py --scaffold nextjs --name <app>

STANDARDS:
1. When asked to create, edit, or scaffold, USE YOUR TOOLS to inspect the workspace, create files, or run commands.
2. ZERO PLACEHOLDERS: Always write 100% complete files without '// TODO' or '# implement here'.
3. Always verify commands before reporting completion.
4. You are operating on Windows; all shell commands run in PowerShell.
""",

    "pentest": """\
You are SPECTRE, an elite autonomous offensive security & penetration testing agent inside the SPECTRE workspace.
You do not just give passive theoretical advice; you ACTIVELY RUN SCANS, AUDITS, AND RECON using your workspace tools.

YOUR TOOLKIT:
- run_command: Execute security tools and Python automation scripts in the workspace
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
                "description": "Execute a shell command (PowerShell / Python / Nmap / npm) in the SPECTRE workspace. Use this to run scans, automation scripts, tests, web servers, or file operations.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {
                            "type": "STRING",
                            "description": "The exact shell command to execute in PowerShell (e.g., 'python scripts/spectre_doctor.py' or 'python scripts/recon_pipeline.py --target 127.0.0.1')."
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "write_file",
                "description": "Write or create a file in the workspace. Creates parent directories automatically.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {
                            "type": "STRING",
                            "description": "Relative path to file in workspace (e.g. 'src/components/Header.tsx' or 'reports/recon.txt')."
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
                "description": "Read text content of a file in the workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {
                            "type": "STRING",
                            "description": "Relative path to file in workspace."
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_directory",
                "description": "List files and subdirectories in a workspace folder.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "path": {
                            "type": "STRING",
                            "description": "Relative directory path (e.g. '.' or 'scripts' or 'reports'). Default is '.'"
                        }
                    }
                }
            }
        ]
    }
]

# --- Safe Tool Execution Engine ------------------------------------------------

def _safe_resolve_path(rel_path: str) -> Path:
    p = (ROOT / rel_path).resolve()
    # Ensure within ROOT for safety
    try:
        p.relative_to(ROOT)
    except ValueError:
        raise PermissionError(f"Access denied: path '{rel_path}' is outside workspace root.")
    return p

def _exec_run_command(command: str, timeout: int = 120) -> dict:
    t0 = time.time()
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            errors="replace",
            timeout=timeout
        )
        duration = round(time.time() - t0, 2)
        out = (res.stdout + res.stderr).strip()
        if not out:
            out = "(Command completed with no output)"
        return {
            "output": out[:8000],  # cap to prevent payload explosion
            "exit_code": res.returncode,
            "duration": duration,
            "command": command
        }
    except subprocess.TimeoutExpired:
        return {
            "output": f"Command timed out after {timeout} seconds.",
            "exit_code": 124,
            "duration": round(time.time() - t0, 2),
            "command": command
        }
    except Exception as exc:
        return {
            "output": f"Execution error: {exc}",
            "exit_code": 1,
            "duration": round(time.time() - t0, 2),
            "command": command
        }

def _exec_write_file(rel_path: str, content: str) -> dict:
    t0 = time.time()
    try:
        target = _safe_resolve_path(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", errors="replace")
        return {
            "output": f"Successfully wrote {len(content)} characters to {rel_path}",
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
                "output": f"File '{rel_path}' not found.",
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
                "output": f"'{rel_path}' is not a directory.",
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

# Session store: sessions[sid] = list of raw Gemini contents parts
_sessions: dict[str, list] = {}
_sessions_lock = threading.Lock()

def _stream_agent_task(agent: str, sid: str, user_prompt: str):
    """
    Generator yielding SSE event dictionaries:
      {"type": "tool_call", "name": ..., "args": ..., "id": ...}
      {"type": "tool_result", "name": ..., "output": ..., "exit_code": ..., "duration": ...}
      {"type": "text", "text": "..."}
      {"type": "error", "message": "..."}
    """
    if not GEMINI_API_KEY:
        yield {"type": "error", "message": "No Gemini API key found in infrastructure/.env"}
        return

    system_instruction = SYSTEM_PROMPTS.get(agent, SYSTEM_PROMPTS["webdev"])
    url_generate = f"https://generativelanguage.googleapis.com/v1beta/models/{ACTIVE_MODEL}:generateContent?key={GEMINI_API_KEY}"
    url_stream = f"https://generativelanguage.googleapis.com/v1beta/models/{ACTIVE_MODEL}:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"

    with _sessions_lock:
        history = _sessions.setdefault(sid, [])
        history.append({"role": "user", "parts": [{"text": user_prompt}]})
        # Local copy of contents for this loop
        contents = list(history)

    max_tool_turns = 5
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

        # First query generateContent synchronously to check if Gemini requests tool calls
        try:
            resp = _requests.post(url_generate, json=payload, timeout=60)
            if resp.status_code != 200:
                err_data = resp.json().get("error", {})
                yield {"type": "error", "message": f"Gemini API Error {resp.status_code}: {err_data.get('message', resp.text)}"}
                return
            res_json = resp.json()
        except Exception as exc:
            yield {"type": "error", "message": f"Connection error: {exc}"}
            return

        candidate = res_json.get("candidates", [{}])[0]
        model_content = candidate.get("content", {})
        parts = model_content.get("parts", [])

        # Check for functionCall
        function_calls = [p for p in parts if "functionCall" in p]

        if function_calls:
            # Append model turn with function calls to contents
            contents.append(model_content)

            # Execute all function calls requested by the model
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

                # Execute tool
                result = _dispatch_tool(name, args)

                yield {
                    "type": "tool_result",
                    "name": name,
                    "output": result.get("output", ""),
                    "exit_code": result.get("exit_code", 0),
                    "duration": result.get("duration", 0.0),
                    "id": call_id
                }

                # Build functionResponse part
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

            # Append user turn containing functionResponses
            contents.append({"role": "user", "parts": fr_parts})
            # Continue the loop so Gemini can analyze tool output or call more tools
            continue

        else:
            # Model generated a pure text response — stream it!
            # We can stream the final turn or emit the text chunks
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            full_text = "".join(text_parts)

            # Stream chunks for smooth typing effect in UI
            chunk_size = 32
            for i in range(0, len(full_text), chunk_size):
                yield {"type": "text", "text": full_text[i:i + chunk_size]}
                time.sleep(0.015)

            # Append final model response to history
            contents.append(model_content)
            break

_cached_health_score = 50
_last_health_check = 0

def _get_cached_health() -> int:
    global _cached_health_score, _last_health_check
    now = time.time()
    if now - _last_health_check > 180:  # Refresh every 3 minutes
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
        pass  # Suppress default noisy access logs

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
            total_files = sum(
                1 for p in ROOT.rglob("*")
                if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
            )

            self._json_resp({
                "api_key": bool(GEMINI_API_KEY),
                "model": ACTIVE_MODEL,
                "sessions": len(_sessions),
                "health": score,
                "files": total_files,
                "root": str(ROOT)
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

        elif path == "/api/workspace/files":
            files_tree = []
            for sub in ["scripts", "reports", "src", "infrastructure", "rag"]:
                p = ROOT / sub
                if p.exists():
                    items = [f.name for f in p.iterdir() if f.is_file()]
                    files_tree.append({"dir": sub, "count": len(items), "files": items[:15]})
            self._json_resp({"workspace": str(ROOT), "structure": files_tree})

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
    try:
        total_files = sum(
            1 for p in ROOT.rglob("*")
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
        )
        total_lines = sum(
            len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
            for p in ROOT.rglob("*")
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
        )
    except Exception:
        total_files, total_lines = 41, 7883

    print("=" * 75)
    print("                 SPECTRE ECOSYSTEM -- ARCHITECTURE MATRIX                  ")
    print("=" * 75)
    print(f"Total Tracked Files : {total_files:<4} | Total Lines of Code : {total_lines:<6}")
    print( "Architecture Status : 100% Core Workspace Completed across 6 Sprints")
    print("-" * 75)
    print("AUTONOMOUS AGENT PAIR:")
    print("  * ARCHITECT (Web Dev) : React 19, Next.js 15, FastAPI, TypeScript, Component Gen")
    print("  * SPECTRE   (Pentest) : Nmap Recon, CVE Analysis, PQC Cryptography, Live QRNG")
    print("TOOL INTEGRATION: Autonomous run_command, write_file, read_file, list_directory")
    print("-" * 75)
    print("QUICK RUNNERS:")
    print("  * Agent Chat Web UI : python scripts/spectre_dashboard.py --port 5050")
    print("  * System Doctor     : python scripts/spectre_doctor.py")
    print("  * Recon Pipeline    : python scripts/recon_pipeline.py --target 127.0.0.1")
    print("  * PQC Code Audit    : python scripts/pqc_audit.py --path .")
    print("  * Quantum Key Gen   : python scripts/quantum_rng.py --aes-key")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Command Center -- Autonomous AI Agent Workspace")
    parser.add_argument("--port", type=int, default=5050, help="HTTP port (default 5050)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    parser.add_argument("--cli", action="store_true", help="Print terminal architecture matrix only")
    args = parser.parse_args()

    _print_cli_matrix()

    if args.cli:
        return

    if not GEMINI_API_KEY:
        print("\n[!] WARNING: GEMINI_API_KEY not found in infrastructure/.env")
        print("    Chat will show an error. Add the key and restart.\n")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), _Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"\n[+] SPECTRE Antigravity Command Center -> {url}")
    print(f"    Active Model : {ACTIVE_MODEL} (with Tool Calling)")
    print("    Agents Ready : ARCHITECT (Web Dev) + SPECTRE (Pentest)")
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
