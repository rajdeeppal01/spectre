# Sprint 5 — SPECTRE Command Center & Interactive Architecture Visualizer

## Overview
In Sprint 5, we created the **SPECTRE Command Center**—a unified, interactive web dashboard and terminal architecture visualizer that provides a single point of visibility across the entire workspace.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SPECTRE SPRINT 5 ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                     SPECTRE COMMAND CENTER (:5050)                              │
│                                                                                 │
│  [1] dashboard/index.html                                                       │
│      • Dark glassmorphic interface (Inter, Fira Code, cyan/emerald palette)    │
│      • Real-time workspace metrics (39 files, 6 personas, 39 vectors, 14 rules) │
│      • Interactive Two-Tier Architecture Graph                                  │
│      • Sprint Deliverables Timeline (Sprints 1–5 complete)                      │
│      • Live Interactive Tool Playground:                                        │
│          - True Quantum Random Generator (QRNG API)                             │
│          - Semantic RAG Knowledge Search Console                                │
│          - Quantum Circuit Simulator Console                                    │
│          - System Doctor Diagnostics Runner                                     │
│                                                                                 │
│  [2] scripts/spectre_dashboard.py                                               │
│      • Zero-dependency Python server (built-in http.server)                     │
│      • REST APIs: /api/status, /api/qrng, /api/rag, /api/sim, /api/doctor       │
│      • ASCII Terminal CLI Visualizer (--cli)                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## How to View and Run the Architecture

### Option 1: Launch the Interactive Web Command Center
```powershell
python scripts\spectre_dashboard.py --port 5050
```
This automatically opens your browser at `http://localhost:5050` with the complete visual interface and interactive playground.

### Option 2: Print Terminal Architecture Matrix
```powershell
python scripts\spectre_dashboard.py --cli
```
Renders a structured terminal overview of all models, layers, and commands.

### Option 3: Run the Health Doctor
```powershell
python scripts\spectre_doctor.py --verbose
```
Runs the 100-point diagnostic check across your hardware, Docker stack, and pipelines.

### Option 4: Inspect the GitHub Repository
Every file, Modelfile, agent swarm, and sprint document is tracked and published at:
`https://github.com/rajdeeppal01/spectre`

---

## Complete Project Structure (39 Tracked Files)

```
spectre/
├── dashboard/               # Interactive Command Center UI
│   └── index.html          # Dark-mode glassmorphic visualizer
├── infrastructure/          # Docker Compose, LiteLLM config, Modelfiles
│   ├── docker-compose.yml  # Ollama, Open WebUI, LiteLLM, SearXNG
│   ├── litellm_config.yaml # Unified cloud + local proxy routing
│   ├── continue_config.json# VS Code IDE integration
│   ├── .env.example
│   └── modelfiles/         # Hardware-tuned Ollama model configurations
├── scripts/                 # Automation, security, web dev, and quantum pipelines
│   ├── setup.ps1           # Automated environment installer
│   ├── pull_models.ps1     # Download all local models
│   ├── auto_router.py      # AUTO-mode intelligent request router
│   ├── spectre_dashboard.py# Unified web & CLI command center
│   ├── spectre_doctor.py   # Automated system diagnostics & health scorecard
│   ├── continuous_security.py # Real-time background vulnerability daemon
│   ├── web_dev_studio.py   # Full-stack Next.js/FastAPI studio bridge
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
        ├── sprint_2.md
        ├── sprint_3.md
        ├── sprint_4.md
        └── sprint_5.md
```

*Status: All sprint deliverables committed and merged to main.*
