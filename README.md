# SPECTRE
### Self-hosted Private AI Ecosystem for Cybersecurity, Technology, Research & Engineering

> A fully private, self-hosted AI workspace combining frontier cloud intelligence with offline local models. Built for offensive cybersecurity, full-stack web development, and quantum-readiness — simultaneously.

---

## What is SPECTRE?

SPECTRE is a modular, two-tier AI workspace that runs on your own hardware. It uses:

- **Gemini 2.5 Pro** (cloud) as the primary intelligence for web development and complex reasoning (1M token context)
- **4 locally-run specialist models** via Ollama for offline, private, and security-sensitive work
- **LiteLLM** as the universal proxy that intelligently routes every request to the optimal model
- **Open WebUI** as the chat dashboard and RAG hub
- **Continue.dev** for IDE-level AI integration inside VS Code
- **Grounded Quantum & PQC Layer** for post-quantum security audits, live QRNG entropy, and quantum simulation

## The Four Local Models

| Codename | Model | Domain |
|---|---|---|
| **ATLAS** | Qwen2.5-7B-Abliterated | General AI & daily assistance |
| **SPECTRE** | WhiteRabbitNeo-2-8B | Offensive cybersecurity & pentesting |
| **ARCHITECT** | Devstral-Small-2 | Full-stack web development & debugging |
| **ORACLE** | Llama-3.1-8B-Instruct | Deep reasoning, STEM & quantum mechanics |

## Three Operating Modes

- **🌐 ONLINE** — Route all tasks to Gemini Pro (maximum frontier intelligence)
- **⚡ AUTO** — Smart routing based on task type and security sensitivity
- **🔒 OFFLINE** — All local, fully air-gapped (cybersecurity queries are hardcoded to never touch cloud endpoints)

## Quick Start

```powershell
# 1. Clone the repo
git clone https://github.com/rajdeeppal01/spectre.git
cd spectre

# 2. Run the setup script (Windows PowerShell)
.\scripts\setup.ps1

# 3. Add your Gemini API key
cp infrastructure\.env.example infrastructure\.env
# Edit .env and set: GEMINI_API_KEY=your_key_here

# 4. Start Docker services (Ollama, Open WebUI, LiteLLM, SearXNG)
docker compose -f infrastructure\docker-compose.yml up -d

# 5. Build RAG Vector Knowledge Base
python scripts\init_rag.py --build
```

Access:
- **Open WebUI:** http://localhost:3000
- **LiteLLM Proxy:** http://localhost:4000

---

## Grounded Quantum & PQC Features

### 1. Post-Quantum Cryptography Audit
Scan codebases for RSA, ECC, and DH primitives vulnerable to Shor's algorithm and generate NIST FIPS 203/204/205 migration paths:
```powershell
python scripts\pqc_audit.py --path ./src --output pqc_report.md
```

### 2. Quantum Random Number Generation (QRNG)
Fetch true quantum entropy from the Australian National University (ANU) Quantum Optics lab or fall back to an air-gapped CPU jitter entropy pool:
```powershell
python scripts\quantum_rng.py --aes-key
python scripts\quantum_rng.py --pqc-seed
python scripts\quantum_rng.py --tokens 5 --length 32
python scripts\quantum_rng.py --serve --port 8001
```

### 3. Quantum Circuit Simulator
Demonstrate Grover's search on symmetric keys, Shor's period-finding on toy RSA semiprimes, Bell state entanglement, and lattice LWE hardness:
```powershell
python scripts\quantum_sim.py --demo all
```

---

## Project Structure

```
spectre/
├── infrastructure/          # Docker Compose, LiteLLM config, Ollama Modelfiles
│   ├── docker-compose.yml  # Ollama, Open WebUI, LiteLLM, SearXNG
│   ├── litellm_config.yaml # Unified cloud + local proxy routing
│   ├── continue_config.json# VS Code IDE integration
│   ├── .env.example
│   └── modelfiles/         # Hardware-tuned Ollama model configurations
├── scripts/                 # Automation, security, and quantum pipelines
│   ├── setup.ps1           # Automated environment installer
│   ├── codebase_sync.py    # Auto-sync active code into RAG vector store
│   ├── recon_pipeline.py   # Nmap XML → SPECTRE → CVE exploit map
│   ├── pqc_audit.py        # Post-quantum cryptography codebase scanner
│   ├── quantum_rng.py      # ANU quantum vacuum entropy & key generator
│   ├── quantum_sim.py      # Quantum circuit simulator & attack analyzer
│   └── init_rag.py         # Universal RAG ingestion & semantic search
├── agents/                  # Multi-agent pipelines
│   ├── red_team_crew.py    # 4-agent CrewAI automated Red Team loop
│   └── web_audit_bridge.py # Burp Suite XML → SPECTRE vulnerability audit
├── rag/                     # Universal RAG knowledge layer
│   ├── collections/        # Curated markdown knowledge bases
│   │   ├── post_quantum_crypto.md  # NIST FIPS 203/204/205 specs
│   │   ├── security_standards.md   # OWASP Top 10 & PTES matrix
│   │   ├── web_dev_standards.md    # Next.js 15, React 19 RSC, FastAPI
│   │   └── cve_knowledge_base.md   # Critical CVE exploit catalogue
│   └── vector_store.json   # Dense embeddings & lexical search index
└── docs/                    # Architecture & sprint documentation
    └── sprints/
        ├── sprint_2.md     # Sprint 2 architecture review
        └── sprint_3.md     # Sprint 3 architecture review
```

## Hardware Requirements

- **Minimum:** 8 GB RAM, NVIDIA GPU with 4 GB VRAM, 30 GB free SSD storage
- **Tested on:** Intel i7-12650H (10C/16T), 16 GB RAM, RTX 3050 Ti Laptop (4 GB VRAM)
- **Tuned Configuration:** 28 GPU offloaded layers, 6 CPU threads (P-cores), 8192 context window cap

## Roadmap

- [x] **Sprint 1** — Infrastructure, Docker Compose, LiteLLM Proxy, Hardware-tuned Modelfiles
- [x] **Sprint 2** — Automation Pipelines, Nmap Recon, Burp Bridge, CrewAI Red Team Swarm
- [x] **Sprint 3** — Grounded Quantum / PQC Layer, ANU QRNG, Circuit Sim, Universal RAG Collections
- [ ] **Sprint 4** — Full-stack Web Dev Studio, Continuous Security Background Daemon, Production Hardening

---

*Built with the philosophy: frontier intelligence for creation, local air-gap privacy for security, and real physics for cryptography.*
