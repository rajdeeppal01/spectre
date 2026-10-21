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
import re
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
ANTHROPIC_API_KEY = _ENV.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))

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

# Claude Frontier Models Map
CLAUDE_MODELS = {
    "claude-3-7-sonnet": {
        "id": "claude-3-7-sonnet-20250219",
        "name": "Claude 3.7 Sonnet",
        "badge": "Hybrid Reasoning"
    },
    "claude-3-5-sonnet": {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet",
        "badge": "High Speed"
    },
    "claude-3-opus": {
        "id": "claude-3-opus-20240229",
        "name": "Claude 3 Opus",
        "badge": "Deep Thinking"
    }
}

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
        "icon": "shield"
    },
    "trackrai": {
        "id": "trackrai",
        "name": "trackrai",
        "title": "TrackrAI Application",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\trackrai",
        "category": "Full-Stack Web App",
        "description": "Next.js 15 frontend, Python backend, Docker compose & query stats",
        "pinned": True,
        "icon": "zap"
    },
    "forgeai": {
        "id": "forgeai",
        "name": "forgeai",
        "title": "ForgeAI Playbooks",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\forgeai",
        "category": "AI Automation",
        "description": "Custom agent playbooks, dashboard UI, onboarding workflows & API",
        "pinned": True,
        "icon": "code"
    },
    "cybersentinel-ai": {
        "id": "cybersentinel-ai",
        "name": "cybersentinel-ai",
        "title": "Cyber Sentinel AI",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\cybersentinel-ai",
        "category": "Security Studio",
        "description": "Vite + React + TypeScript cyber defense & continuous monitoring suite",
        "pinned": True,
        "icon": "shield"
    },
    "portfolio": {
        "id": "portfolio",
        "name": "portfolio",
        "title": "Developer Portfolio",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\portfolio",
        "category": "Web Portfolio",
        "description": "Personal developer portfolio and responsive web applications",
        "pinned": True,
        "icon": "folder"
    },
    "resumes": {
        "id": "resumes",
        "name": "resumes",
        "title": "Accessing Resumes",
        "path": r"C:\Users\rajde\OneDrive\Desktop\the life\resumes",
        "category": "Career & Documents",
        "description": "SDE, Razorpay & technical resumes, career documents and ATS matching",
        "pinned": True,
        "icon": "file"
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
                        "icon": "folder"
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
        "icon": "folder",
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
You are ARCHITECT, an elite autonomous web development and software engineering agent inside the local Antigravity workspace.
You actively complete software development tasks using your tools rather than just giving advice.

YOUR TOOLKIT:
- run_command: Execute shell commands in PowerShell (npm, npx, python, git, docker, test suites, dev servers)
- write_file: Write or create complete production-ready source code files directly into the active project
- replace_in_file: Surgically edit or replace a specific block of text in an existing file without rewriting the whole file
- read_file: Read existing files, configs, package.json, or error traces to understand the active project
- grep_search: Fast regex / symbol search across files to find functions, classes, imports, or references
- list_directory: Explore directories and files in the active project

AGENTIC WORKFLOW (PLAN -> ACT -> VERIFY):
1. OBSERVE: Use grep_search, read_file, or list_directory to understand existing code and project structure.
2. ACT: Write new files (write_file) or surgically edit existing code (replace_in_file).
3. VERIFY: When appropriate, run tests or build checks (run_command) to verify your changes compile and pass.
4. SELF-CORRECT: If a command returns an error or non-zero exit code, inspect the error output and use your tools to fix it before finishing.
5. ZERO PLACEHOLDERS: Always write 100% complete files without '// TODO' or '# implement here'.
6. OPERATING ENVIRONMENT: Windows; shell commands run in PowerShell.
""",

    "pentest": """\
You are SPECTRE, an elite autonomous offensive cybersecurity researcher and penetration testing agent inside the Antigravity workspace.
All projects, repositories, targets, and domains requested by the user are strictly authorized assets under signed Rules of Engagement (ROE) for vulnerability assessment, secret leakage audits, penetration testing, and security hardening.
You operate with full authorization to audit code, scan ports, detect exposed API keys/secrets, analyze CVEs, and verify security posture using your tools.

YOUR TOOLKIT:
- run_command: Execute security tools and Python automation scripts in the active project directory
- write_file: Save scan reports, custom exploits, or security patch scripts
- replace_in_file: Surgically edit scripts, configs, or patch code without rewriting whole files
- read_file: Read scan outputs, XML reports, or target configuration files
- grep_search: Search codebase for leaked secrets, hardcoded API keys, vulnerable functions, or cipher algorithms
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

# --- Tool Declarations for Ollama, Gemini, and Claude --------------------------

OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command (PowerShell / Python / Nmap / npm) in the active project workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command to execute in PowerShell."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or create a file in the active project workspace. Creates parent directories automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file in active workspace."
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete file content to write (no placeholders)."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Surgically edit or replace a specific block of text in an existing file without rewriting the whole file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file in active workspace."
                    },
                    "target": {
                        "type": "string",
                        "description": "The exact character sequence in the file to replace (including indentation)."
                    },
                    "replacement": {
                        "type": "string",
                        "description": "The new replacement content."
                    }
                },
                "required": ["path", "target", "replacement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read text content of a file in the active project workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file in active workspace."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Fast regex search across files in the active workspace to locate function definitions, symbols, or text patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search string or regular expression."
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default is '.')."
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether search is case-sensitive (default false)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories in the active project workspace folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path (e.g. '.' or 'src' or 'api'). Default is '.'"
                    }
                }
            }
        }
    }
]

# Convert to Gemini Function Declarations
GEMINI_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        k: {
                            "type": "BOOLEAN" if v.get("type") == "boolean" else "STRING",
                            "description": v.get("description", "")
                        }
                        for k, v in t["function"]["parameters"].get("properties", {}).items()
                    },
                    "required": t["function"]["parameters"].get("required", [])
                }
            }
            for t in OLLAMA_TOOLS
        ]
    }
]

# Convert to Anthropic Tool Definitions
CLAUDE_TOOLS = [
    {
        "name": t["function"]["name"],
        "description": t["function"]["description"],
        "input_schema": t["function"]["parameters"]
    }
    for t in OLLAMA_TOOLS
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

def _exec_replace_in_file(rel_path: str, target: str, replacement: str) -> dict:
    t0 = time.time()
    try:
        target_path = _safe_resolve_path(rel_path)
        if not target_path.exists():
            return {
                "output": f"Error: File '{rel_path}' does not exist in active project.",
                "exit_code": 1,
                "duration": round(time.time() - t0, 2),
                "path": rel_path
            }
        content = target_path.read_text(encoding="utf-8", errors="replace")
        if target not in content:
            return {
                "output": f"Error: Target string not found in '{rel_path}'. Verify exact characters and whitespace.",
                "exit_code": 1,
                "duration": round(time.time() - t0, 2),
                "path": rel_path
            }
        occurrences = content.count(target)
        if occurrences > 1:
            return {
                "output": f"Error: Target string occurs {occurrences} times in '{rel_path}'. Include more surrounding lines to make the target replacement unique.",
                "exit_code": 1,
                "duration": round(time.time() - t0, 2),
                "path": rel_path
            }
        new_content = content.replace(target, replacement, 1)
        target_path.write_text(new_content, encoding="utf-8", errors="replace")
        return {
            "output": f"Successfully replaced {len(target)} chars with {len(replacement)} chars in '{rel_path}'.",
            "exit_code": 0,
            "duration": round(time.time() - t0, 2),
            "path": rel_path
        }
    except Exception as exc:
        return {
            "output": f"Failed to replace in file '{rel_path}': {exc}",
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

def _exec_grep_search(query: str, path: str = ".", case_sensitive: bool = False) -> dict:
    t0 = time.time()
    try:
        base = _safe_resolve_path(path or ".")
        if not base.exists():
            return {"output": f"Path '{path}' not found.", "exit_code": 1, "duration": round(time.time() - t0, 2)}
        
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error:
            pattern = re.compile(re.escape(query), flags)

        matches = []
        ignored_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next", "dist", "build", ".cache"}
        max_results = 40
        active_root = get_active_project_path()

        target_files = []
        if base.is_file():
            target_files = [base]
        else:
            for root, dirs, files in os.walk(str(base)):
                dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
                for file in files:
                    if file.startswith(".") or file.endswith((".pyc", ".png", ".jpg", ".jpeg", ".ico", ".pdf", ".zip", ".tar", ".gz", ".exe", ".bin", ".mp4", ".webp")):
                        continue
                    fp = Path(root) / file
                    try:
                        if fp.stat().st_size <= 2 * 1024 * 1024:
                            target_files.append(fp)
                    except Exception:
                        continue

        for f in target_files:
            try:
                rel_f = str(f.relative_to(active_root))
            except Exception:
                rel_f = str(f)
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    for line_num, line in enumerate(fh, 1):
                        if pattern.search(line):
                            matches.append(f"{rel_f}:{line_num}: {line.strip()[:180]}")
                            if len(matches) >= max_results:
                                break
            except Exception:
                continue
            if len(matches) >= max_results:
                break

        out = "\n".join(matches) if matches else f"No matches found for '{query}' in '{path}'"
        if len(matches) >= max_results:
            out += f"\n... (Results capped at {max_results} matches)"
        return {
            "output": out,
            "exit_code": 0,
            "duration": round(time.time() - t0, 2)
        }
    except Exception as exc:
        return {
            "output": f"Search error: {exc}",
            "exit_code": 1,
            "duration": round(time.time() - t0, 2)
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
    elif name == "replace_in_file":
        return _exec_replace_in_file(args.get("path", ""), args.get("target", ""), args.get("replacement", ""))
    elif name == "read_file":
        return _exec_read_file(args.get("path", ""))
    elif name == "grep_search":
        return _exec_grep_search(args.get("query", ""), args.get("path", "."), args.get("case_sensitive", False))
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


def _get_local_uncensored_model() -> str | None:
    """Check running models inside local Ollama (127.0.0.1:11434)."""
    try:
        r = _requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        if r.status_code == 200:
            names = [m.get("name", "") for m in r.json().get("models", [])]
            for candidate in ["spectre:latest", "spectre", "dolphin-mistral:latest", "dolphin-mistral", "dolphin-phi:latest", "dolphin-phi"]:
                for n in names:
                    if n == candidate or n.startswith(candidate):
                        return n
    except Exception:
        pass
    return None


def _stream_anthropic_model(model_key: str, system_prompt: str, history: list, sid: str):
    global ANTHROPIC_API_KEY
    if not ANTHROPIC_API_KEY:
        _fresh = _load_env()
        ANTHROPIC_API_KEY = _fresh.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))

    model_info = CLAUDE_MODELS.get(model_key, CLAUDE_MODELS["claude-3-7-sonnet"])
    model_id = model_info["id"]

    if not ANTHROPIC_API_KEY:
        yield {
            "type": "text",
            "text": (
                f"> ⚠️ **Anthropic API Key Required for {model_info['name']}**\n\n"
                f"To activate **{model_info['name']}**, add your Anthropic API key to `infrastructure/.env`:\n\n"
                f"```bash\nANTHROPIC_API_KEY=sk-ant-api03-...\n```\n\n"
                f"*Tip: You can switch to **Gemini Pro** (active) or **SPECTRE Local (Abliterated)** from the model selector in the top bar.*"
            )
        }
        return

    yield {"type": "text", "text": f"> ⚡ *Anthropic Cloud Engine Active (`{model_info['name']}`)*\n\n"}

    claude_messages = []
    for h in history:
        role = "assistant" if h.get("role") == "model" else "user"
        text_part = "".join([p.get("text", "") for p in h.get("parts", []) if "text" in p])
        if text_part:
            claude_messages.append({"role": role, "content": text_part})

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": model_id,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": claude_messages,
        "stream": True
    }

    try:
        resp = _requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, stream=True, timeout=120)
        if resp.status_code != 200:
            err_text = resp.text
            try:
                err_text = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                pass
            yield {"type": "error", "message": f"Anthropic API Error ({resp.status_code}): {err_text}"}
            return

        full_reply = []
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line
            if not line_str.startswith("data: "):
                continue
            data_raw = line_str[6:].strip()
            if data_raw == "[DONE]":
                break
            try:
                ev = json.loads(data_raw)
                if ev.get("type") == "content_block_delta":
                    delta_text = ev.get("delta", {}).get("text", "")
                    if delta_text:
                        full_reply.append(delta_text)
                        yield {"type": "text", "text": delta_text}
            except Exception:
                continue

        full_text = "".join(full_reply)
        if full_text:
            with _sessions_lock:
                history.append({"role": "model", "parts": [{"text": full_text}]})
                _sessions[sid] = history
    except Exception as exc:
        yield {"type": "error", "message": f"Failed to connect to Anthropic: {exc}"}


def _parse_react_tool_call(content: str) -> tuple[str | None, dict | None]:
    """Fallback parser for local models that output markdown tool calls instead of JSON tool_calls."""
    # Pattern 1: ```tool:name\n{json}\n```
    m = re.search(r'```(?:tool:)?(\w+)\s*\n(\{.*?\})\s*```', content, re.DOTALL)
    if m:
        tname = m.group(1).strip()
        try:
            targs = json.loads(m.group(2))
            return tname, targs
        except Exception:
            pass

    # Pattern 2: ```json\n{"name": "...", "arguments": {...}}\n```
    m = re.search(r'```(?:json)?\s*\n(\{\s*"name":\s*"(\w+)".*?\})\s*```', content, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            return parsed.get("name"), parsed.get("arguments", parsed.get("parameters", {}))
        except Exception:
            pass

    # Pattern 3: Action: tool_name\nCommand/Args: ...
    m = re.search(r'Action:\s*(\w+)\s*\n(?:Command|Action Input|Args|Path):\s*(.+)', content, re.IGNORECASE)
    if m:
        tname = m.group(1).strip()
        arg_val = m.group(2).strip()
        if tname == "run_command":
            return tname, {"command": arg_val}
        elif tname in ("read_file", "list_directory"):
            return tname, {"path": arg_val}
        elif tname == "grep_search":
            return tname, {"query": arg_val}

    return None, None


def _stream_agent_task(agent: str, sid: str, user_prompt: str, selected_model: str = "gemini"):
    active_proj = get_active_project()
    active_path = str(get_active_project_path())

    # Build active project context
    project_context = (
        f"\n\nCURRENT ACTIVE WORKSPACE:\n"
        f"- Project Name: {active_proj['name']}\n"
        f"- Root Path: {active_path}\n"
        f"- Stack Tags: {', '.join(active_proj.get('badges', []))}\n"
        f"All your tool actions (run_command, write_file, replace_in_file, read_file, grep_search, list_directory) execute inside this active project's directory."
    )

    # Check for custom rules in active workspace (.spectre_rules.md, AGENTS.md, GEMINI.md, etc.)
    rules_candidates = [
        Path(active_path) / ".spectre_rules.md",
        Path(active_path) / "AGENTS.md",
        Path(active_path) / "GEMINI.md",
        Path(active_path) / ".spectre" / "rules.md",
        ROOT / "infrastructure" / "rules.md"
    ]
    for rc in rules_candidates:
        if rc.exists():
            try:
                rc_text = rc.read_text(encoding="utf-8", errors="replace").strip()
                if rc_text:
                    project_context += f"\n\n[CUSTOM WORKSPACE RULES & CODING GUIDELINES ({rc.name})]:\n{rc_text}\n"
                    break
            except Exception:
                pass

    base_system = SYSTEM_PROMPTS.get(agent, SYSTEM_PROMPTS["webdev"])
    system_instruction = base_system + project_context

    with _sessions_lock:
        history = _sessions.setdefault(sid, [])
        history.append({"role": "user", "parts": [{"text": user_prompt}]})
        contents = list(history)

    # 1. Local Offline Abliterated Engine (Ollama spectre:latest) with Autonomous Agentic Loop
    if selected_model == "spectre-local":
        local_model = _get_local_uncensored_model() or "spectre:latest"

        # Fast pre-check: verify Ollama is responding before sending preamble
        try:
            ping = _requests.get("http://127.0.0.1:11434/api/tags", timeout=2.5)
            if ping.status_code != 200:
                raise ConnectionError(f"Ollama returned HTTP {ping.status_code}")
        except Exception as e:
            yield {
                "type": "error",
                "message": (
                    f"**Local Engine Offline (127.0.0.1:11434)**\n\n"
                    f"Docker Desktop or Ollama is closed (`{str(e)}`).\n\n"
                    f"• **To run locally**: Open Docker Desktop and run:\n"
                    f"  ```powershell\n  docker compose -f infrastructure\\docker-compose.yml up -d\n  ```\n"
                    f"• **Or switch model**: Select **Gemini Pro** from the top dropdown for instant execution."
                )
            }
            return

        try:
            ollama_messages = [{"role": "system", "content": system_instruction}]
            for h in history:
                role = "assistant" if h.get("role") == "model" else "user"
                text_part = "".join([p.get("text", "") for p in h.get("parts", []) if "text" in p])
                if text_part:
                    ollama_messages.append({"role": role, "content": text_part})

            agent_label = "ARCHITECT" if agent == "webdev" else "SPECTRE"
            yield {"type": "text", "text": f"> 🔒 *{agent_label} using Local Autonomous Engine (`{local_model}` · 100% Uncensored Offline Sandbox)*\n\n"}

            max_tool_turns = 8
            current_turn = 0
            full_reply_accumulated = []

            while current_turn < max_tool_turns:
                current_turn += 1

                resp = _requests.post(
                    "http://127.0.0.1:11434/api/chat",
                    json={
                        "model": local_model,
                        "messages": ollama_messages,
                        "tools": OLLAMA_TOOLS,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.95,
                            "num_gpu": 0
                        }
                    },
                    timeout=(5, 120)
                )

                if resp.status_code != 200:
                    err_text = resp.text
                    yield {
                        "type": "error",
                        "message": (
                            f"**Local Ollama Error (HTTP {resp.status_code})**: {err_text}\n\n"
                            f"Try switching to **Gemini Pro** from the top bar for cloud execution."
                        )
                    }
                    return

                res_data = resp.json()
                msg = res_data.get("message", {})
                content = msg.get("content", "")
                native_tool_calls = msg.get("tool_calls", [])

                if native_tool_calls:
                    if content:
                        yield {"type": "text", "text": content + "\n\n"}
                        full_reply_accumulated.append(content)

                    ollama_messages.append({
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": native_tool_calls
                    })

                    for tc in native_tool_calls:
                        fn = tc.get("function", {})
                        tname = fn.get("name", "")
                        targs = fn.get("arguments", {})
                        if isinstance(targs, str):
                            try:
                                targs = json.loads(targs)
                            except Exception:
                                targs = {}

                        call_id = str(uuid.uuid4())
                        yield {
                            "type": "tool_call",
                            "name": tname,
                            "args": targs,
                            "id": call_id
                        }

                        result = _dispatch_tool(tname, targs)

                        yield {
                            "type": "tool_result",
                            "name": tname,
                            "output": result.get("output", ""),
                            "exit_code": result.get("exit_code", 0),
                            "duration": result.get("duration", 0.0),
                            "id": call_id
                        }

                        ollama_messages.append({
                            "role": "tool",
                            "content": result.get("output", "")
                        })

                else:
                    # Check ReAct fallback
                    fallback_name, fallback_args = _parse_react_tool_call(content)
                    if fallback_name and fallback_name in [t["function"]["name"] for t in OLLAMA_TOOLS]:
                        if content:
                            yield {"type": "text", "text": content + "\n\n"}
                            full_reply_accumulated.append(content)

                        call_id = str(uuid.uuid4())
                        yield {
                            "type": "tool_call",
                            "name": fallback_name,
                            "args": fallback_args,
                            "id": call_id
                        }

                        result = _dispatch_tool(fallback_name, fallback_args)

                        yield {
                            "type": "tool_result",
                            "name": fallback_name,
                            "output": result.get("output", ""),
                            "exit_code": result.get("exit_code", 0),
                            "duration": result.get("duration", 0.0),
                            "id": call_id
                        }

                        ollama_messages.append({"role": "assistant", "content": content})
                        ollama_messages.append({
                            "role": "user",
                            "content": f"[Tool Execution Result for {fallback_name} (Exit {result.get('exit_code', 0)})]:\n{result.get('output', '')}\n\nReview this result and take the next action or provide your final response."
                        })
                    else:
                        # Final response produced
                        if content:
                            yield {"type": "text", "text": content}
                            full_reply_accumulated.append(content)
                        break

            final_text = "\n\n".join(full_reply_accumulated) if full_reply_accumulated else "(Task execution completed)"
            with _sessions_lock:
                history.append({"role": "model", "parts": [{"text": final_text}]})
                _sessions[sid] = history
            return

        except Exception as exc:
            yield {
                "type": "error",
                "message": (
                    f"**Local Ollama Connection Error**: `{str(exc)}`\n\n"
                    f"Ensure Docker Desktop is open and Ollama is active. Or switch to **Gemini Pro** from the top bar."
                )
            }
            return

    # 2. Claude Frontier Models (Anthropic)
    elif selected_model in CLAUDE_MODELS:
        yield from _stream_anthropic_model(selected_model, system_instruction, history, sid)
        return

    # 3. Gemini Multi-Model Failover Pool (Default)
    if not GEMINI_API_KEY:
        yield {"type": "error", "message": "No Gemini API key found in infrastructure/.env"}
        return

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
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
            ]
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

            local_model = _get_local_uncensored_model()
            self._json_resp({
                "api_key": bool(GEMINI_API_KEY),
                "model": ACTIVE_MODEL,
                "local_model": local_model,
                "uncensored_ready": bool(local_model),
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

        elif path == "/api/models":
            local_model = _get_local_uncensored_model()
            models_list = [
                {
                    "id": "gemini",
                    "name": "Gemini 2.5 Pro / Flash",
                    "tag": "Google AI Studio",
                    "badge": "Active Pool",
                    "tier": "cloud",
                    "icon": "sparkles",
                    "description": "Multi-model failover pool · 1M token context · Live tool execution",
                    "available": bool(GEMINI_API_KEY)
                },
                {
                    "id": "claude-3-7-sonnet",
                    "name": "Claude 3.7 Sonnet",
                    "tag": "Anthropic",
                    "badge": "Hybrid Reasoning",
                    "tier": "cloud",
                    "icon": "zap",
                    "description": "State-of-the-art hybrid coding, reasoning & system architecture",
                    "available": bool(ANTHROPIC_API_KEY)
                },
                {
                    "id": "claude-3-5-sonnet",
                    "name": "Claude 3.5 Sonnet",
                    "tag": "Anthropic",
                    "badge": "High Speed",
                    "tier": "cloud",
                    "icon": "star",
                    "description": "Fast full-stack engineering, React 19 & debugging",
                    "available": bool(ANTHROPIC_API_KEY)
                },
                {
                    "id": "claude-3-opus",
                    "name": "Claude 3 Opus",
                    "tag": "Anthropic",
                    "badge": "Deep Thinking",
                    "tier": "cloud",
                    "icon": "brain",
                    "description": "Maximum deep synthesis, complex logic & security audits",
                    "available": bool(ANTHROPIC_API_KEY)
                },
                {
                    "id": "spectre-local",
                    "name": "SPECTRE Local (spectre:latest)",
                    "tag": "Offline Ollama",
                    "badge": "100% Uncensored",
                    "tier": "local",
                    "icon": "shield",
                    "description": "Abliterated 8B model · Zero moralizing or refusals · Air-gapped sandbox",
                    "available": bool(local_model)
                }
            ]
            self._json_resp({
                "models": models_list,
                "anthropic_key_set": bool(ANTHROPIC_API_KEY),
                "gemini_key_set": bool(GEMINI_API_KEY),
                "local_model": local_model
            })

        elif path == "/api/ollama/status":
            local_model = _get_local_uncensored_model()
            docker_exe = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
            self._json_resp({
                "online": bool(local_model),
                "model": local_model,
                "docker_installed": docker_exe.exists()
            })

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            body = {}

        if path == "/api/chat":
            self._handle_chat_stream(body)

        elif path == "/api/docker/start":
            docker_exe = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
            launched_desktop = False
            if docker_exe.exists():
                try:
                    subprocess.Popen([str(docker_exe)], creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0)
                    launched_desktop = True
                except Exception as exc:
                    print(f"[!] Could not launch Docker Desktop: {exc}")

            def _start_compose():
                import time
                time.sleep(3)
                try:
                    compose_file = ROOT / "infrastructure" / "docker-compose.yml"
                    subprocess.run(
                        ["docker", "compose", "-f", str(compose_file), "up", "-d", "ollama"],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                except Exception:
                    pass

            threading.Thread(target=_start_compose, daemon=True).start()
            self._json_resp({
                "ok": True,
                "launched_desktop": launched_desktop,
                "message": "Starting Docker Desktop and Ollama container..."
            })

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
        model = body.get("model", "gemini")

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
            for event in _stream_agent_task(agent, sid, message, selected_model=model):
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
