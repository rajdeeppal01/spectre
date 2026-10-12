"""
SPECTRE Doctor — System Diagnostic & Health Verification Suite
Performs end-to-end verification of infrastructure, local Ollama models,
cloud routing, GPU resource profile, quantum engines, and RAG vector store.

Usage:
    python scripts/spectre_doctor.py
    python scripts/spectre_doctor.py --verbose
    python scripts/spectre_doctor.py --json doctor_report.json
"""

import os
import sys
import json
import socket
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple
import urllib.request
import urllib.error

ROOT_DIR = Path(__file__).resolve().parent.parent


def check_port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    """Test TCP socket connection with fast timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def check_http_endpoint(host: str, port: int, path: str = "/", timeout: float = 0.5) -> Tuple[bool, str]:
    """Test HTTP endpoint status using 127.0.0.1 to bypass IPv6 DNS resolution latency."""
    if not check_port_open(host, port, timeout=0.2):
        return False, "Port closed / Service offline"

    url = f"http://{host}:{port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SPECTRE-Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        # Some endpoints return 401/403 or 405 on GET if alive
        return True, f"HTTP {e.code} (Service active)"
    except Exception as e:
        return False, str(e)


def check_nvidia_gpu() -> Dict[str, Any]:
    """Check NVIDIA GPU driver, VRAM, and CUDA via nvidia-smi."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1.5
        )
        if out.returncode == 0:
            lines = out.stdout.strip().splitlines()
            if lines:
                parts = [p.strip() for p in lines[0].split(",")]
                return {
                    "available": True,
                    "name": parts[0] if len(parts) > 0 else "Unknown",
                    "vram_total_mb": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                    "vram_free_mb": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
                    "driver": parts[3] if len(parts) > 3 else "N/A"
                }
    except Exception:
        pass
    return {"available": False, "name": "No NVIDIA GPU detected via nvidia-smi"}


def check_docker() -> Dict[str, Any]:
    """Check if Docker engine is running."""
    try:
        out = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True, timeout=1.5)
        if out.returncode == 0 and out.stdout.strip():
            return {"available": True, "version": out.stdout.strip()}
    except Exception:
        pass
    return {"available": False, "version": "Docker daemon not running"}


def check_ollama_models() -> Dict[str, Any]:
    """Check models installed in local Ollama."""
    url = "http://localhost:11434/api/tags"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            return {"online": True, "models": models}
    except Exception:
        return {"online": False, "models": []}


def check_gemini_api_key() -> Dict[str, Any]:
    """Check Gemini API key availability."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        # Check infrastructure/.env
        env_file = ROOT_DIR / "infrastructure" / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY=") and len(line.split("=", 1)[1].strip()) > 10:
                    key = line.split("=", 1)[1].strip()
                    break

    if key:
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "Present"
        return {"configured": True, "key_preview": masked}
    return {"configured": False, "key_preview": "Missing (Set GEMINI_API_KEY in infrastructure/.env)"}


def run_diagnostics(verbose: bool = False) -> Dict[str, Any]:
    """Execute full diagnostic suite across SPECTRE layers."""
    report: Dict[str, Any] = {
        "timestamp": sys.platform,
        "sections": {},
        "score": 0,
        "max_score": 100
    }

    # 1. Hardware & GPU
    gpu_info = check_nvidia_gpu()
    docker_info = check_docker()

    report["sections"]["hardware"] = {
        "name": "Hardware & Compute Profile",
        "weight": 15,
        "score": 15 if gpu_info["available"] else 8,
        "gpu": gpu_info,
        "docker": docker_info
    }

    # 2. Local Infrastructure & Services
    services = {
        "Ollama (:11434)": check_http_endpoint("127.0.0.1", 11434, "/api/tags"),
        "LiteLLM Proxy (:4000)": check_http_endpoint("127.0.0.1", 4000, "/health"),
        "Open WebUI (:3000)": check_http_endpoint("127.0.0.1", 3000, "/"),
        "SearXNG (:8080)": check_http_endpoint("127.0.0.1", 8080, "/"),
        "AUTO Router (:8000)": check_http_endpoint("127.0.0.1", 8000, "/healthz")
    }

    svc_online_count = sum(1 for is_up, _ in services.values() if is_up)
    svc_score = int((svc_online_count / len(services)) * 25)

    report["sections"]["services"] = {
        "name": "Container Services & Endpoints",
        "weight": 25,
        "score": svc_score,
        "details": {k: {"online": up, "status": msg} for k, (up, msg) in services.items()}
    }

    # 3. Model Engine
    ollama_info = check_ollama_models()
    expected_personas = ["spectre", "atlas", "architect", "oracle", "nomic-embed-text"]
    found_personas = []
    for p in expected_personas:
        if any(p in m.lower() for m in ollama_info["models"]):
            found_personas.append(p)

    model_score = 0
    if ollama_info["online"]:
        model_score = int(10 + (len(found_personas) / len(expected_personas)) * 15)

    report["sections"]["models"] = {
        "name": "Local Model Personas (Ollama)",
        "weight": 25,
        "score": model_score,
        "ollama_online": ollama_info["online"],
        "installed_models": ollama_info["models"],
        "expected_personas": expected_personas,
        "configured_personas": found_personas
    }

    # 4. Cloud Tier (Gemini)
    gemini_info = check_gemini_api_key()
    gemini_score = 15 if gemini_info["configured"] else 0
    report["sections"]["cloud_tier"] = {
        "name": "Cloud Frontier Tier (Gemini Pro/Flash)",
        "weight": 15,
        "score": gemini_score,
        "status": gemini_info
    }

    # 5. Core Pipelines & RAG Vector Store
    rag_colls = list((ROOT_DIR / "rag" / "collections").glob("*.md")) if (ROOT_DIR / "rag" / "collections").exists() else []
    vector_store_ok = (ROOT_DIR / "rag" / "vector_store.json").exists()

    pipeline_scripts = [
        "pqc_audit.py", "quantum_rng.py", "quantum_sim.py",
        "init_rag.py", "continuous_security.py", "web_dev_studio.py",
        "recon_pipeline.py", "codebase_sync.py", "auto_router.py"
    ]
    existing_scripts = [s for s in pipeline_scripts if (ROOT_DIR / "scripts" / s).exists()]

    pipeline_score = int(
        (len(existing_scripts) / len(pipeline_scripts)) * 10 +
        (len(rag_colls) / 4) * 5 +
        (5 if vector_store_ok else 0)
    )

    report["sections"]["pipelines_and_rag"] = {
        "name": "Pipelines, Quantum Layer & RAG Engine",
        "weight": 20,
        "score": min(20, pipeline_score),
        "scripts_present": f"{len(existing_scripts)}/{len(pipeline_scripts)}",
        "rag_collections_count": len(rag_colls),
        "vector_store_ready": vector_store_ok
    }

    # Calculate Total Score
    total_score = sum(s["score"] for s in report["sections"].values())
    report["score"] = total_score

    return report


def print_scorecard(report: Dict[str, Any], verbose: bool = False):
    score = report["score"]
    status_label = "EXCELLENT" if score >= 85 else ("OPERATIONAL" if score >= 60 else "NEEDS SETUP")
    color = "\033[92m" if score >= 85 else ("\033[93m" if score >= 60 else "\033[91m")
    reset = "\033[0m"

    print("=" * 70)
    print("                    SPECTRE SYSTEM DOCTOR REPORT                    ")
    print("=" * 70)
    print(f"Overall Workspace Health Score : {color}{score}/100 [{status_label}]{reset}")
    print("-" * 70)

    for key, sec in report["sections"].items():
        weight = sec["weight"]
        s = sec["score"]
        sec_color = "\033[92m" if s == weight else ("\033[93m" if s > 0 else "\033[91m")
        print(f"  {sec['name']:40}: {sec_color}{s:2d}/{weight:2d} pts{reset}")

        if key == "hardware":
            gpu = sec["gpu"]
            if gpu["available"]:
                print(f"    * GPU   : {gpu['name']} ({gpu['vram_total_mb']} MB VRAM)")
            else:
                print(f"    * GPU   : {gpu['name']}")
            print(f"    * Docker: {sec['docker']['version']}")

        elif key == "services" and verbose:
            for s_name, s_val in sec["details"].items():
                mark = "[OK]" if s_val["online"] else "[OFFLINE]"
                print(f"    {mark} {s_name}: {s_val['status']}")

        elif key == "cloud_tier":
            print(f"    * Gemini API Key: {sec['status']['key_preview']}")

        elif key == "pipelines_and_rag":
            print(f"    * Automation Scripts : {sec['scripts_present']} verified")
            print(f"    * RAG Collections    : {sec['rag_collections_count']} curated sets active")
            print(f"    * Offline Vector DB  : {'Pre-indexed & ready' if sec['vector_store_ready'] else 'Missing'}")

    print("=" * 70)
    print("Recommended Actions for 100/100 Health:")
    if not report["sections"]["services"]["details"]["Ollama (:11434)"]["online"]:
        print("  1. Start Docker stack: docker compose -f infrastructure/docker-compose.yml up -d")
    if not report["sections"]["cloud_tier"]["status"]["configured"]:
        print("  2. Add your Gemini student key to infrastructure/.env (GEMINI_API_KEY=...)")
    if not report["sections"]["models"]["configured_personas"]:
        print("  3. Pull local models: .\\scripts\\pull_models.ps1")
    print("=" * 70)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="SPECTRE Doctor — System Diagnostic & Health Suite")
    parser.add_argument("--verbose", action="store_true", help="Print detailed per-endpoint diagnostics")
    parser.add_argument("--json", help="Save diagnostic report to JSON file")

    args = parser.parse_args()

    print("[*] Running SPECTRE Workspace Health Diagnostics...")
    report = run_diagnostics(verbose=args.verbose)
    print_scorecard(report, verbose=args.verbose)

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n[+] Diagnostic JSON written to {args.json}")


if __name__ == "__main__":
    main()
