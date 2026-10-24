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
import difflib
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
        "icon": "zap",
        "preview_url": "https://trackrai.in"
    },
    "forgeai": {
        "id": "forgeai",
        "name": "forgeai",
        "title": "ForgeAI Playbooks",
        "path": r"C:\Users\rajde\OneDrive\Desktop\projects\forgeai",
        "category": "AI Automation",
        "description": "Custom agent playbooks, dashboard UI, onboarding workflows & API",
        "pinned": True,
        "icon": "code",
        "preview_url": "https://forgeai-rose.vercel.app"
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
        "description": "Personal developer portfolio hosted on GitHub Pages",
        "pinned": True,
        "icon": "folder",
        "preview_url": "https://rajdeeppal01.github.io/portfolio/"
    },
    "resumes": {
        "id": "resumes",
        "name": "resumes",
        "title": "Accessing Resumes",
        "path": r"C:\Users\rajde\OneDrive\Desktop\the life\resumes",
        "category": "Career & Documents",
        "description": "SDE, Razorpay & technical resumes, career documents and ATS matching",
        "pinned": True,
        "icon": "file",
        "preview_url": "https://rajdeeppal01.github.io/portfolio/"
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
        if 'index.html' in names and any(f.endswith('.js') or f.endswith('.css') for f in names):
            badges.append('Vanilla JS')
            badges.append('GitHub Pages')
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

    # Map of verified live URLs for known projects
    LIVE_URL_MAP = {
        "portfolio": "https://rajdeeppal01.github.io/portfolio/",
        "forgeai": "https://forgeai-rose.vercel.app",
        "trackrai": "https://trackrai.in",
        "synthscan": "https://synthscan-psi.vercel.app",
        "vapordrop": "https://vapordrop-iota.vercel.app",
        "zeroclaw-hub": "https://zeroclaw-hub.vercel.app",
        "cywar": "https://cywar.vercel.app",
        "cybercouncil-frontend": "https://cybercouncil-frontend.vercel.app",
        "secureonboard": "https://secureonboard.vercel.app",
        "alfredthebuttler": "https://alfredthebuttler.vercel.app",
        "q": "https://q-vert-eight.vercel.app",
        "resumes": "https://rajdeeppal01.github.io/portfolio/"
    }

    # Annotate with real existence, file counts, tech badges, and preview URLs
    for pid, pdata in projects.items():
        ppath = Path(pdata["path"])
        pdata["exists"] = ppath.exists()
        pdata["badges"] = detect_project_stack(ppath)
        if "preview_url" not in pdata or not pdata.get("preview_url") or pdata.get("preview_url") == "http://localhost:3000":
            low_id = pid.lower()
            low_name = str(pdata.get("name", "")).lower()
            if low_id in LIVE_URL_MAP:
                pdata["preview_url"] = LIVE_URL_MAP[low_id]
            elif low_name in LIVE_URL_MAP:
                pdata["preview_url"] = LIVE_URL_MAP[low_name]
            elif (ppath / ".git" / "config").exists():
                try:
                    cfg_text = (ppath / ".git" / "config").read_text(encoding="utf-8", errors="replace")
                    if "rajdeeppal01/portfolio" in cfg_text:
                        pdata["preview_url"] = "https://rajdeeppal01.github.io/portfolio/"
                    elif "rajdeeppal01/" in cfg_text:
                        import re
                        m = re.search(r"github\.com[:/]rajdeeppal01/([a-zA-Z0-9_\-]+)", cfg_text)
                        if m:
                            pdata["preview_url"] = f"https://rajdeeppal01.github.io/{m.group(1)}/"
                except Exception:
                    pass
            if "preview_url" not in pdata:
                pdata["preview_url"] = "http://localhost:3000"
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
- write_file: Write or create complete production-ready source code files directly into the active project (creates visual diff & rollback snapshot)
- replace_in_file: Surgically edit or replace a specific block of text in an existing file without rewriting the whole file (creates visual diff & rollback snapshot)
- read_file: Read existing files, configs, package.json, or error traces to understand the active project
- grep_search: Fast regex / symbol search across files to find functions, classes, imports, or references
- list_directory: Explore directories and files in the active project
- search_web: Search the live web / documentation via SearXNG or DuckDuckGo for latest library APIs, syntax, or error resolutions
- verify_build: Run automated compiler / type / syntax checks (npx tsc, npm run build, python -m py_compile) to self-verify your work
- handoff_to_spectre: Run automated red-team security audits against your code to verify zero secret leaks and no security flaws

AGENTIC WORKFLOW (PLAN -> ACT -> VERIFY -> SECURE):
1. OBSERVE: Use grep_search, read_file, search_web, or list_directory to understand existing code or look up latest docs.
2. ACT: Write new files (write_file) or surgically edit existing code (replace_in_file).
3. VERIFY: Call verify_build to verify your code compiles and passes type checks.
4. SELF-CORRECT: If verify_build returns compiler errors or traces, use replace_in_file to repair them until passing.
5. SECURE: Call handoff_to_spectre before declaring completion to guarantee no leaked secrets or insecure patterns.
6. ZERO PLACEHOLDERS: Always write 100% complete files without '// TODO' or '# implement here'.
7. OPERATING ENVIRONMENT: Windows; shell commands run in PowerShell.
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
- search_web: Search the live web / NVD / CVE databases for exploit details, CVSS scores, and remediation advisories
- verify_build: Verify that security patches and script modifications compile cleanly

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
            "description": "Write or create a file in the active project workspace. Creates parent directories automatically, generates a visual diff, and registers an undo snapshot.",
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
            "description": "Surgically edit or replace a specific block of text in an existing file without rewriting the whole file. Generates a visual diff and registers an undo snapshot.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the live web or documentation via local SearXNG / DuckDuckGo for the latest APIs, libraries, syntax, or CVE security details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g. 'Next.js 15 server actions typescript' or 'CVE-2024-xxxx details')."
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of results to retrieve (default 5)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_build",
            "description": "Run automated compiler, type checking, or test verification (npx tsc, npm run build, or python -m py_compile) to self-verify your code changes compile with zero errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_type": {
                        "type": "string",
                        "description": "Type of check: 'auto' (detects stack), 'build', 'typecheck', or 'syntax'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_spectre",
            "description": "Triggers SPECTRE red-team cybersecurity audit against the modified files or project to verify zero secret leaks, no exposed keys, and security hardening compliance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_paths": {
                        "type": "string",
                        "description": "Relative paths or directories to audit (e.g. '.' or 'src/api')."
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
                            "type": "INTEGER" if v.get("type") == "integer" else ("BOOLEAN" if v.get("type") == "boolean" else "STRING"),
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

def _safe_resolve_path(rel_path) -> Path:
    active_root = get_active_project_path()
    if isinstance(rel_path, (list, tuple)):
        rel_path = rel_path[0] if rel_path else "."
    elif not isinstance(rel_path, str):
        rel_path = str(rel_path or ".")
    p = (active_root / rel_path).resolve()
    return p

# Snapshot & Rollback Store for File Undo
_SNAPSHOTS: dict[str, dict] = {}

def _create_snapshot(target_path: Path, rel_path: str, before_content: str, after_content: str) -> dict:
    snapshot_id = f"snap_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    before_lines = before_content.splitlines(keepends=True) if before_content else []
    after_lines = after_content.splitlines(keepends=True) if after_content else []
    diff_lines = list(difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
        n=3
    ))
    diff_text = "".join(diff_lines)
    snap_info = {
        "id": snapshot_id,
        "path": rel_path,
        "abs_path": str(target_path),
        "before": before_content,
        "after": after_content,
        "diff": diff_text,
        "ts": time.time()
    }
    _SNAPSHOTS[snapshot_id] = snap_info
    if len(_SNAPSHOTS) > 60:
        oldest = min(_SNAPSHOTS.keys(), key=lambda k: _SNAPSHOTS[k]["ts"])
        _SNAPSHOTS.pop(oldest, None)
    return snap_info

def _exec_revert_snapshot(snapshot_id: str) -> dict:
    snap = _SNAPSHOTS.get(snapshot_id)
    if not snap:
        return {"error": f"Snapshot {snapshot_id} not found or expired.", "ok": False}
    target = Path(snap["abs_path"])
    try:
        if snap["before"] == "":
            if target.exists():
                target.unlink()
            return {"ok": True, "message": f"Reverted: Deleted created file '{snap['path']}'"}
        else:
            target.write_text(snap["before"], encoding="utf-8", errors="replace")
            return {"ok": True, "message": f"Reverted: Restored '{snap['path']}' to previous state."}
    except Exception as exc:
        return {"error": f"Failed to restore file: {exc}", "ok": False}

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
        before_content = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        target.write_text(content, encoding="utf-8", errors="replace")
        snap = _create_snapshot(target, rel_path, before_content, content)
        return {
            "output": f"Successfully wrote {len(content)} characters to {rel_path} in {target.parent.name}",
            "exit_code": 0,
            "duration": round(time.time() - t0, 2),
            "path": rel_path,
            "diff": snap["diff"],
            "snapshot_id": snap["id"]
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
        before_content = target_path.read_text(encoding="utf-8", errors="replace")
        if target not in before_content:
            return {
                "output": f"Error: Target string not found in '{rel_path}'. Verify exact characters and whitespace.",
                "exit_code": 1,
                "duration": round(time.time() - t0, 2),
                "path": rel_path
            }
        occurrences = before_content.count(target)
        if occurrences > 1:
            return {
                "output": f"Error: Target string occurs {occurrences} times in '{rel_path}'. Include more surrounding lines to make the target replacement unique.",
                "exit_code": 1,
                "duration": round(time.time() - t0, 2),
                "path": rel_path
            }
        after_content = before_content.replace(target, replacement, 1)
        target_path.write_text(after_content, encoding="utf-8", errors="replace")
        snap = _create_snapshot(target_path, rel_path, before_content, after_content)
        return {
            "output": f"Successfully replaced {len(target)} chars with {len(replacement)} chars in '{rel_path}'.",
            "exit_code": 0,
            "duration": round(time.time() - t0, 2),
            "path": rel_path,
            "diff": snap["diff"],
            "snapshot_id": snap["id"]
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

def _exec_search_web(query: str, count: int = 5) -> dict:
    t0 = time.time()
    # 1. Try local SearXNG on http://127.0.0.1:8080 if running in docker
    try:
        sx_resp = _requests.get(
            "http://127.0.0.1:8080/search",
            params={"q": query, "format": "json"},
            timeout=3
        )
        if sx_resp.status_code == 200:
            results = sx_resp.json().get("results", [])[:count]
            if results:
                formatted = [
                    f"### [{r.get('title', 'Result')}]({r.get('url')})\n{r.get('content', '')}\nSource: {r.get('url')}"
                    for r in results
                ]
                return {
                    "output": f"Found {len(formatted)} results via SearXNG:\n\n" + "\n\n---\n\n".join(formatted),
                    "exit_code": 0,
                    "duration": round(time.time() - t0, 2),
                    "source": "searxng"
                }
    except Exception:
        pass

    # 2. DuckDuckGo Instant Answers API + HTML Fallback
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        ddg_resp = _requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers=headers,
            timeout=5
        )
        data = ddg_resp.json()
        results = []
        if data.get("AbstractText"):
            results.append(f"**Abstract**: {data.get('AbstractText')}\nURL: {data.get('AbstractURL')}")
        for topic in data.get("RelatedTopics", [])[:count]:
            if isinstance(topic, dict) and "Text" in topic and "FirstURL" in topic:
                results.append(f"- **{topic['Text']}**\n  URL: {topic['FirstURL']}")

        if not results:
            html_resp = _requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers=headers,
                timeout=5
            )
            from urllib.parse import unquote
            matches = re.findall(r'<a class="result__snippet[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_resp.text, re.DOTALL)
            if not matches:
                matches = re.findall(r'<a class="result__url[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_resp.text, re.DOTALL)
            for url, snippet in matches[:count]:
                clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                if url.startswith("//duckduckgo.com/l/?uddg="):
                    url = unquote(url.split("uddg=")[1].split("&")[0])
                results.append(f"- {clean_snippet}\n  URL: {url}")

        if results:
            return {
                "output": f"Web Search Results for '{query}':\n\n" + "\n\n".join(results),
                "exit_code": 0,
                "duration": round(time.time() - t0, 2),
                "source": "duckduckgo"
            }
        else:
            return {
                "output": f"No direct web results found for query: '{query}'.",
                "exit_code": 0,
                "duration": round(time.time() - t0, 2),
                "source": "duckduckgo"
            }
    except Exception as exc:
        return {
            "output": f"Web search error: {exc}",
            "exit_code": 1,
            "duration": round(time.time() - t0, 2)
        }

def _exec_verify_build(check_type: str = "auto") -> dict:
    t0 = time.time()
    active_dir = get_active_project_path()
    files = {f.name.lower() for f in active_dir.iterdir() if f.is_file() or f.is_dir()}
    
    cmd = ""
    label = ""
    if "tsconfig.json" in files or "package.json" in files:
        pkg_json = active_dir / "package.json"
        scripts = {}
        if pkg_json.exists():
            try:
                scripts = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace")).get("scripts", {})
            except Exception:
                pass
        
        if "type-check" in scripts:
            cmd = "npm run type-check"
            label = "TypeScript Type Check"
        elif "build" in scripts:
            cmd = "npm run build"
            label = "npm Build Verification"
        else:
            cmd = "npx tsc --noEmit"
            label = "npx tsc Verification"
    elif "requirements.txt" in files or any(f.endswith(".py") for f in files):
        py_files = [f'"{f.name}"' for f in active_dir.glob("*.py") if not f.name.startswith(".")][:10]
        if py_files:
            cmd = "python -m py_compile " + " ".join(py_files)
            label = "Python Compilation Check"
        else:
            cmd = "python --version"
            label = "Python Environment Check"
    else:
        cmd = "git status"
        label = "Workspace Status Check"
        
    res = _exec_run_command(cmd, timeout=60)
    passed = res.get("exit_code") == 0
    return {
        "output": f"[{label} - {'PASSED (Zero Errors)' if passed else 'FAILED (Compiler/Lint Errors Detected)'}]\nCommand: {cmd}\n\n{res.get('output', '')}",
        "exit_code": res.get("exit_code", 0),
        "duration": round(time.time() - t0, 2),
        "passed": passed,
        "command": cmd
    }

def _exec_handoff_to_spectre(target_paths=".") -> dict:
    t0 = time.time()
    active_dir = get_active_project_path()
    
    findings = []
    secret_patterns = [
        (r'(?i)(?:api_key|apikey|secret|token|password|bearer|auth)\s*[:=]\s*["\']([^"\']{8,})["\']', "Potential Leaked API Key / Secret"),
        (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Exposed Private Key"),
        (r'(?i)sk-ant-api\d+-[a-zA-Z0-9_\-]{20,}', "Exposed Anthropic API Key"),
        (r'AIza[0-9A-Za-z-_]{35}', "Exposed Google/Gemini API Key"),
    ]
    
    # Handle list or string of target_paths
    if isinstance(target_paths, (list, tuple)):
        raw_list = target_paths
    elif isinstance(target_paths, str) and "," in target_paths:
        raw_list = [tp.strip() for tp in target_paths.split(",") if tp.strip()]
    else:
        raw_list = [target_paths] if target_paths else ["."]

    targets = []
    for item in raw_list:
        p = _safe_resolve_path(item)
        if p.is_file():
            targets.append(p)
        elif p.is_dir():
            targets.extend([f for f in p.rglob("*") if f.is_file() and not any(part in f.parts for part in (".git", "node_modules", ".venv", "__pycache__", ".next", "dist"))])

    files_checked = 0
    for tf in targets[:35]:
        files_checked += 1
        try:
            content = tf.read_text(encoding="utf-8", errors="replace")
            for pat, desc in secret_patterns:
                matches = re.findall(pat, content)
                if matches:
                    rel = tf.relative_to(active_dir) if active_dir in tf.parents else tf.name
                    findings.append(f"CRITICAL: {desc} in `{rel}`")
        except Exception:
            pass

    display_target = str(target_paths)
    if findings:
        report = (
            f"### [SPECTRE RED TEAM AUDIT: VULNERABILITIES DETECTED]\n"
            f"Checked {files_checked} files in `{display_target}`.\n\n"
            + "\n".join([f"- [!] {f}" for f in findings])
            + f"\n\n**Action Required**: ARCHITECT must sanitize these secrets and replace them with environment variables before proceeding."
        )
        exit_code = 1
    else:
        report = (
            f"### [SPECTRE RED TEAM AUDIT: CLEAR]\n"
            f"Checked {files_checked} files in `{display_target}`.\n"
            f"- Zero exposed secrets, private keys, or API tokens found.\n"
            f"- Static security baseline passed."
        )
        exit_code = 0
        
    return {
        "output": report,
        "exit_code": exit_code,
        "duration": round(time.time() - t0, 2),
        "files_checked": files_checked
    }

def _load_skills(workspace_path: Path | None = None) -> list[dict]:
    skills = []
    candidates_dirs = []
    if workspace_path and (workspace_path / "skills").is_dir():
        candidates_dirs.append(workspace_path / "skills")
    if (ROOT / "skills").is_dir():
        candidates_dirs.append(ROOT / "skills")
    if (ROOT / "infrastructure" / "skills").is_dir():
        candidates_dirs.append(ROOT / "infrastructure" / "skills")

    seen_names = set()
    for sdir in candidates_dirs:
        for item in sdir.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists() and item.name not in seen_names:
                    seen_names.add(item.name)
                    text = skill_file.read_text(encoding="utf-8", errors="replace")
                    desc = ""
                    title = item.name.replace("-", " ").title()
                    if text.startswith("---"):
                        parts = text.split("---", 2)
                        if len(parts) >= 3:
                            fm = parts[1]
                            for line in fm.splitlines():
                                if line.startswith("description:"):
                                    desc = line.split("description:", 1)[1].strip().strip('"\'')
                                elif line.startswith("name:"):
                                    title = line.split("name:", 1)[1].strip().strip('"\'')
                    if not desc:
                        for line in text.splitlines():
                            if line.strip() and not line.startswith("#") and not line.startswith("---"):
                                desc = line.strip()
                                break
                    skills.append({
                        "id": item.name,
                        "name": title,
                        "description": desc or f"Workflow instructions for {title}",
                        "path": str(skill_file),
                        "content": text
                    })
    return skills

def _dispatch_tool(name: str, args: dict) -> dict:
    try:
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
        elif name == "search_web":
            return _exec_search_web(args.get("query", ""), int(args.get("count", 5)))
        elif name == "verify_build":
            return _exec_verify_build(args.get("check_type", "auto"))
        elif name == "handoff_to_spectre":
            return _exec_handoff_to_spectre(args.get("target_paths", "."))
        else:
            return {"output": f"Unknown tool: {name}", "exit_code": 1, "duration": 0.0}
    except Exception as exc:
        return {"output": f"Tool execution failed: {type(exc).__name__}: {str(exc)}", "exit_code": 1, "duration": 0.0}

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


def _stream_agent_task(agent: str, sid: str, user_prompt: str, selected_model: str = "gemini", autopilot: bool = True, attachments: list | None = None):
    active_proj = get_active_project()
    active_path = str(get_active_project_path())

    # Build active project context
    project_context = (
        f"\n\nCURRENT ACTIVE WORKSPACE:\n"
        f"- Project Name: {active_proj['name']}\n"
        f"- Root Path: {active_path}\n"
        f"- Stack Tags: {', '.join(active_proj.get('badges', []))}\n"
        f"All your tool actions (run_command, write_file, replace_in_file, read_file, grep_search, list_directory, search_web, verify_build, handoff_to_spectre) execute inside this active project's directory."
    )

    if autopilot:
        project_context += (
            f"\n\n[⚡ AUTOPILOT MODE ACTIVATED - MANDATORY OPERATIONAL PROTOCOL]:\n"
            f"- AUTOPILOT IS ON: The user has granted full, unconditional pre-approval for all actions and tool calls.\n"
            f"- All tool permissions (running shell commands, writing/overwriting files, code patches, installing packages, tests, and builds) are AUTOMATICALLY ALLOWED.\n"
            f"- CRITICAL: NEVER stop, wait, or ask the user for permission, approval, confirmation, or whether to continue (e.g. 'Should I run this?', 'Allow me to edit this file?', 'May I install this package?').\n"
            f"- Proactively execute tools in sequence to complete the entire requested objective.\n"
            f"- If a build error, lint failure, or command failure occurs, immediately use your tools to fix it, re-verify with verify_build, and keep going autonomously.\n"
            f"- Only stop when the requested task is completely implemented, verified, and functioning."
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

    # Discover and inject active skills if referenced or matching prompt (/skill-name or /skill skill-name)
    active_skills = _load_skills(Path(active_path))
    activated_skill = None
    prompt_lower = user_prompt.lower().strip()
    for sk in active_skills:
        sk_id = sk["id"].lower()
        if f"/{sk_id}" in prompt_lower or f"/skill {sk_id}" in prompt_lower or prompt_lower.startswith(f"/{sk_id}") or f"skill: {sk_id}" in prompt_lower:
            activated_skill = sk
            break

    if activated_skill:
        project_context += (
            f"\n\n[ACTIVATED SKILL WORKFLOW: {activated_skill['name']} ({activated_skill['id']})]:\n"
            f"{activated_skill['content']}\n"
            f"Strictly adhere to the specific instructions, rules, and steps detailed in this skill.\n"
        )

    # Query local RAG vector store for relevant cybersecurity, web standards, and PQC knowledge
    try:
        from init_rag import search_vector_store
        rag_hits = search_vector_store(user_prompt, top_k=2)
        if rag_hits:
            rag_docs = []
            for hit in rag_hits:
                rec = hit.get("record", {})
                score = hit.get("score", 0)
                if score > 0.10 or not rec.get("embedding"):
                    rag_docs.append(f"• [{rec.get('collection')}] {rec.get('header')}:\n{rec.get('text')}")
            if rag_docs:
                project_context += (
                    f"\n\n[SPECTRE RAG KNOWLEDGE BASE - RETRIEVED RELEVANT DOCUMENTS]:\n"
                    + "\n\n".join(rag_docs)
                    + "\nUse this verified technical knowledge when formulating your response and tool commands."
                )
    except Exception:
        pass

    base_system = SYSTEM_PROMPTS.get(agent, SYSTEM_PROMPTS["webdev"])
    system_instruction = base_system + project_context

    user_parts = []

    # Process user attachments (Multimodal Images, PDFs, Code, Data)
    if attachments:
        for att in attachments:
            name = att.get("name", "attachment")
            mime = att.get("type", "application/octet-stream")
            b64_data = att.get("data", "")
            if "base64," in b64_data:
                b64_data = b64_data.split("base64,")[1]

            # Gemini Vision & Document Multimodal API
            if mime.startswith("image/") or mime == "application/pdf":
                user_parts.append({
                    "inlineData": {
                        "mimeType": mime,
                        "data": b64_data
                    }
                })
            else:
                # Text / Code / Markdown attachments
                try:
                    import base64
                    text_content = base64.b64decode(b64_data).decode("utf-8", errors="replace")
                    ext = name.split(".")[-1] if "." in name else "text"
                    user_parts.append({
                        "text": f"\n\n[USER ATTACHED FILE: {name}]\n```{ext}\n{text_content}\n```\n"
                    })
                except Exception:
                    pass

    user_parts.append({"text": user_prompt})

    with _sessions_lock:
        history = _sessions.setdefault(sid, [])
        history.append({"role": "user", "parts": user_parts})
        contents = list(history)

    if activated_skill:
        yield {"type": "text", "text": f"> ⚡ *Skill Activated: `{activated_skill['name']}`* (`skills/{activated_skill['id']}/SKILL.md`)\n\n"}

    if autopilot:
        yield {"type": "text", "text": f"> ⚡ *Autopilot Mode Engaged* · Zero permission pauses · Full autonomous execution.\n\n"}

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

            max_tool_turns = 25 if autopilot else 8
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
                            "diff": result.get("diff", ""),
                            "snapshot_id": result.get("snapshot_id", ""),
                            "path": result.get("path", ""),
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
                            "diff": result.get("diff", ""),
                            "snapshot_id": result.get("snapshot_id", ""),
                            "path": result.get("path", ""),
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

    max_tool_turns = 25 if autopilot else 8
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
                call_id = fc.get("id") or str(uuid.uuid4())

                yield {
                    "type": "tool_call",
                    "name": name,
                    "args": args,
                    "id": call_id
                }

                result = _dispatch_tool(name, args)

                yield {
                    "type": "tool_result",
                    "name": name,
                    "output": result.get("output", ""),
                    "exit_code": result.get("exit_code", 0),
                    "duration": result.get("duration", 0.0),
                    "diff": result.get("diff", ""),
                    "snapshot_id": result.get("snapshot_id", ""),
                    "path": result.get("path", ""),
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

        elif path.startswith("/assets/") or path.endswith((".mp4", ".webm", ".jpg", ".jpeg", ".png", ".svg", ".ico", ".css", ".js")):
            rel_file = path.lstrip("/")
            target = ROOT / "dashboard" / rel_file
            if not target.exists():
                target = ROOT / rel_file
            if target.exists() and target.is_file():
                ext = target.suffix.lower()
                mime_map = {
                    ".mp4": "video/mp4",
                    ".webm": "video/webm",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon",
                    ".css": "text/css",
                    ".js": "application/javascript"
                }
                mime = mime_map.get(ext, "application/octet-stream")
                file_size = target.stat().st_size
                range_header = self.headers.get("Range")

                if range_header and range_header.startswith("bytes="):
                    try:
                        ranges = range_header[6:].split("-")
                        start = int(ranges[0]) if ranges[0] else 0
                        end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                        length = end - start + 1

                        self.send_response(206)
                        self.send_header("Content-Type", mime)
                        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                        self.send_header("Content-Length", str(length))
                        self.send_header("Accept-Ranges", "bytes")
                        self._cors_headers()
                        self.end_headers()

                        with open(target, "rb") as f:
                            f.seek(start)
                            self.wfile.write(f.read(length))
                        return
                    except Exception:
                        pass

                data = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Accept-Ranges", "bytes")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self._json_resp({"error": "Asset not found"}, 404)
                return

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

        elif path == "/api/skills":
            active_path = get_active_project_path()
            self._json_resp({
                "skills": _load_skills(active_path)
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

        elif path == "/api/file/revert":
            snapshot_id = body.get("snapshotId", "").strip()
            if not snapshot_id:
                self._json_resp({"error": "No snapshotId provided", "ok": False}, 400)
                return
            res = _exec_revert_snapshot(snapshot_id)
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
        autopilot = bool(body.get("autopilot", True))
        attachments = body.get("attachments", [])

        if not message and not attachments:
            self._json_resp({"error": "Empty message"}, 400)
            return

        if not message and attachments:
            message = "Please inspect, analyze, and process the attached files / images."

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self._cors_headers()
        self.end_headers()

        try:
            for event in _stream_agent_task(agent, sid, message, selected_model=model, autopilot=autopilot, attachments=attachments):
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
