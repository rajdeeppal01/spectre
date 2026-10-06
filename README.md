# SPECTRE
### Self-hosted Private AI Ecosystem for Cybersecurity, Technology, Research & Engineering

> A fully private, self-hosted AI workspace combining frontier cloud intelligence with offline local models. Built for offensive cybersecurity, full-stack web development, and general AI — simultaneously.

---

## What is SPECTRE?

SPECTRE is a modular, two-tier AI workspace that runs on your own hardware. It uses:

- **Gemini 2.5 Pro** (cloud) as the primary intelligence for web development and complex reasoning
- **4 locally-run specialist models** via Ollama for offline, private, and security-sensitive work
- **LiteLLM** as the universal proxy that intelligently routes every request to the optimal model
- **Open WebUI** as the Odysseus-style chat dashboard
- **Continue.dev** for IDE-level AI integration inside VS Code

## The Four Local Models

| Codename | Model | Domain |
|---|---|---|
| **ATLAS** | Qwen2.5-7B-Abliterated | General AI & daily assistance |
| **SPECTRE** | WhiteRabbitNeo-2-8B | Offensive cybersecurity & pentesting |
| **ARCHITECT** | Devstral-Small-2 | Full-stack web development & debugging |
| **ORACLE** | Llama-3.1-8B-Instruct | Deep reasoning & quantum computing |

## Three Operating Modes

- **🌐 ONLINE** — Route all tasks to Gemini Pro (maximum intelligence)
- **⚡ AUTO** — Smart routing based on task type and sensitivity
- **🔒 OFFLINE** — All local, fully air-gapped

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/spectre.git
cd spectre

# 2. Run the setup script (Windows PowerShell)
.\scripts\setup.ps1

# 3. Add your Gemini API key
cp infrastructure/.env.example infrastructure/.env
# Edit .env and add: GEMINI_API_KEY=your_key_here

# 4. Start everything
docker compose -f infrastructure/docker-compose.yml up -d

# 5. Pull local models
.\scripts\pull_models.ps1
```

Access:
- **Open WebUI:** http://localhost:3000
- **LiteLLM Proxy:** http://localhost:4000

## Project Structure

```
spectre/
├── infrastructure/          # Docker Compose, LiteLLM config, Ollama Modelfiles
│   ├── docker-compose.yml
│   ├── litellm_config.yaml
│   ├── .env.example
│   └── modelfiles/         # Custom Ollama model configurations
├── scripts/                 # Setup, automation, and pipeline scripts
│   ├── setup.ps1           # Windows one-click setup
│   ├── pull_models.ps1     # Download all 4 local models
│   ├── codebase_sync.py    # Auto-sync your code into RAG
│   └── recon_pipeline.py   # Nmap → SPECTRE → exploit map
├── agents/                  # CrewAI multi-agent pipelines
│   ├── red_team_crew.py    # Full automated Red Team loop
│   └── web_audit_bridge.py # Burp Suite → AI analysis bridge
├── rag/                     # RAG collection management
│   └── collections/        # Document collection configs
└── docs/                    # Architecture & sprint documentation
    ├── architecture.md
    └── sprints/
```

## Hardware Requirements

- **Minimum:** 8 GB RAM, NVIDIA GPU with 4 GB VRAM, 30 GB free SSD storage
- **Tested on:** Intel i7-12650H, 16 GB RAM, RTX 3050 Ti (4 GB VRAM)
- **Recommended:** 16 GB RAM, NVIDIA GPU with 8+ GB VRAM

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud AI | Google Gemini 2.5 Pro / Flash |
| Local inference | Ollama + llama.cpp |
| Proxy/router | LiteLLM |
| Chat UI | Open WebUI |
| IDE integration | Continue.dev |
| Web search | SearXNG |
| Agent pipelines | CrewAI + LangChain |
| Quantum | Qiskit-Aer + liboqs-python |
| Containers | Docker + Docker Compose |

## Roadmap

- [x] Sprint 1 — Infrastructure & Docker Compose
- [ ] Sprint 2 — Model configuration & RAG collections
- [ ] Sprint 3 — Continue.dev IDE integration
- [ ] Sprint 4 — Pentesting automation pipelines
- [ ] Sprint 5 — CrewAI multi-agent Red Team loop
- [ ] Sprint 6 — Quantum / PQC integration layer

---

*Built with the philosophy: frontier intelligence for creation, local privacy for security.*
