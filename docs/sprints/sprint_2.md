# Sprint 2 — Automation & RAG Architecture

## Completed Architecture
In this sprint, we extended the core infrastructure with the active automation layer:

### 1. RAG Auto-Sync Engine (`scripts/codebase_sync.py`)
- **What it is:** A continuous background daemon (via `watchdog`) that monitors your active coding projects.
- **How it works:** Whenever you save a file (`.py`, `.ts`, `.js`, etc.), it hashes the content. If changed, it automatically pushes the new file to the Open WebUI ChromaDB instance.
- **Why it matters:** Gemini Pro and ARCHITECT always have real-time access to your latest code context without you manually uploading files.

### 2. Reconnaissance Pipeline (`scripts/recon_pipeline.py`)
- **What it is:** A direct bridge between network scanning and the local SPECTRE model.
- **How it works:** Executes an `nmap` scan with vulnerability scripts, parses the XML output, and feeds it into the local `whiterabbitneo2` model.
- **Why it matters:** Automates the most tedious part of pentesting (CVE mapping and exploit identification) while ensuring sensitive target data never leaves your laptop.

### 3. Red Team Crew (`agents/red_team_crew.py`)
- **What it is:** A 4-agent CrewAI swarm running purely on local models.
- **The Agents:**
  1. **SCOUT (SPECTRE):** Maps attack surface
  2. **EXPLOIT (SPECTRE):** Writes weaponised payloads
  3. **REVIEWER (ARCHITECT):** Code-reviews the exploits for safety
  4. **REPORTER (ATLAS):** Writes the final markdown report
- **Why it matters:** This implements the true "agentic" workflow. Instead of chatting with one model, you give a target IP, and four specialised AIs debate and collaborate to breach it.

### 4. Web Audit Bridge (`agents/web_audit_bridge.py`)
- **What it is:** A pipeline connecting Burp Suite to AI.
- **How it works:** Takes an XML export of Burp Suite HTTP history and feeds each request/response pair into SPECTRE to look for SQLi, XSS, IDOR, and logic flaws.

## Next Steps (Sprint 3)
- Finalise the Quantum layer (PQC analysis scripts)
- RAG collections definition files
- Setup testing and validation

---
*Status: Merged to main.*
