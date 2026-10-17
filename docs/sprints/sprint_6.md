# SPECTRE — Sprint 6 Architecture Review

## Objective: Autonomous Dual-Agent Antigravity Command Center

Sprint 6 transforms SPECTRE from a passive assistant into an active, local **Antigravity AI Agent Command Center**. The workspace provides a chat-driven interface with live tool calling, allowing agents to execute PowerShell commands, inspect repositories, write production-grade code, and run cybersecurity pipelines autonomously.

---

## 1. Architecture Overview

```
                                ┌───────────────────────────┐
                                │   Local Web UI (:5050)    │
                                │  - Glassmorphic Interface │
                                │  - Live Tool Cards        │
                                │  - Terminal Drawer        │
                                └─────────────┬─────────────┘
                                              │ SSE / JSON
                                              ▼
                                ┌───────────────────────────┐
                                │    spectre_dashboard.py   │
                                │   ThreadingHTTPServer     │
                                └─────────────┬─────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │                                               │
                      ▼                                               ▼
     ┌─────────────────────────────────┐             ┌─────────────────────────────────┐
     │      ARCHITECT (Daily Dev)      │             │      SPECTRE (Weekly Pentest)   │
     │  React 19 / Next.js 15 / FastAPI│             │  Nmap Recon / CVEs / PQC Crypto │
     └────────────────┬────────────────┘             └────────────────┬────────────────┘
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              │
                                              ▼
                                ┌───────────────────────────┐
                                │   Gemini 3.5 Flash API    │
                                │  Native Function Calling  │
                                │  & Thought Signatures     │
                                └─────────────┬─────────────┘
                                              │
                                              ▼
                                ┌───────────────────────────┐
                                │  Workspace Tool Dispatch  │
                                │  - run_command            │
                                │  - write_file             │
                                │  - read_file              │
                                │  - list_directory         │
                                └───────────────────────────┘
```

---

## 2. Autonomous Specialist Personas

### Mode A: ARCHITECT (Daily Full-Stack Web Development)
- **Role**: Principal Full-Stack Engineer and System Architect.
- **Specializations**: React 19, Next.js 15 (App Router, Server Actions, RSC), TypeScript 5, TailwindCSS 4, FastAPI, SQLAlchemy 2.0, PostgreSQL.
- **Autonomous Execution**:
  - Automatically inspects `package.json` and directory structure using `read_file` and `list_directory`.
  - Creates and refactors zero-placeholder components using `write_file`.
  - Scaffolds complete applications using `python scripts/web_dev_studio.py` via `run_command`.

### Mode B: SPECTRE (Weekly Offensive Cybersecurity)
- **Role**: Elite Penetration Tester, Vulnerability Researcher, and Cryptographer.
- **Specializations**: Nmap port scanning, OWASP Top 10 auditing, CVE analysis, NIST FIPS 203/204/205 PQC compliance, ANU quantum entropy generation.
- **Autonomous Execution**:
  - Launches target recon scans via `python scripts/recon_pipeline.py --target <host>`.
  - Audits codebases for classical RSA/ECC cryptography via `python scripts/pqc_audit.py`.
  - Generates quantum-seeded AES-256-GCM key bundles via `python scripts/quantum_rng.py`.
  - Runs full workspace diagnostics via `python scripts/spectre_doctor.py`.

---

## 3. Tool Execution Protocol

When a user prompts either agent, Gemini 3.5 Flash evaluates the request and can invoke tools:
1. **`run_command`**: Spawns PowerShell processes with timeout protection, stdout/stderr capture, and exit code reporting.
2. **`write_file`**: Writes complete files to disk within the workspace root.
3. **`read_file`**: Reads file content to inspect existing logic, configs, or reports.
4. **`list_directory`**: Explores directories and file listings.

Tool execution events stream to the frontend via Server-Sent Events (SSE):
- `tool_call`: Triggers an active execution card with pulsing spinner.
- `tool_result`: Populates the collapsible terminal block with exit code, duration, and output.
- `text`: Streams the agent's explanation, insights, and recommendations.

---

## 4. Frontend Command Center Features

- **Dynamic Theme Transitions**: Smooth accent transitions between Cyan (`#22d3ee`) for ARCHITECT and Amber/Orange (`#f97316`) for SPECTRE.
- **Action Chips Bar**: Contextual 1-click execution chips for common daily and weekly workflows.
- **Workspace PowerShell Terminal Drawer**: Embedded slide-up terminal console for direct shell interaction.
- **Interactive Code Blocks**: Code snippets include both `📋 Copy` and `▶ Run in Terminal` buttons.
- **Session History**: Local storage persistence for conversations across reloads.
