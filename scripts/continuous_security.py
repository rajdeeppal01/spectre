"""
SPECTRE — Continuous Security Background Daemon (MODE C Always-On)
Monitors project files in real time. On save, scans code for OWASP Top 10
vulnerabilities, hardcoded secrets, injection flaws, and quantum-vulnerable
cryptography. Optionally routes modified snippets to local SPECTRE for deep audit.

Usage:
    python scripts/continuous_security.py --watch ./src
    python scripts/continuous_security.py --scan ./src
    python scripts/continuous_security.py --scan ./src --pre-commit
    python scripts/continuous_security.py --watch ./src --ai-assist
"""

import os
import re
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

# ── Vulnerability Signatures ──────────────────────────────────────────
SECURITY_RULES = [
    {
        "id": "SEC-001",
        "name": "Hardcoded Secret / API Key",
        "severity": "CRITICAL",
        "regex": r"(?i)\b((?:api[_-]?key|access[_-]?token|secret[_-]?key|client[_-]?secret|auth[_-]?token|private[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]|sk_live_[0-9a-zA-Z]{24}|ghp_[0-9a-zA-Z]{36}|AIzaSy[0-9A-Za-z\-_]{33})",
        "desc": "Hardcoded credential detected. Secrets in source control can be extracted by adversaries.",
        "remediation": "Move credentials to environment variables or a secure key vault (.env)."
    },
    {
        "id": "SEC-002",
        "name": "SQL Injection (Unsanitized Concatenation)",
        "severity": "CRITICAL",
        "regex": r"(?i)\b(execute|cursor\.execute|query|raw)\s*\(\s*(?:f['\"].*SELECT.*\{|['\"].*SELECT.*['\"]\s*%\s*|\s*['\"].*SELECT.*['\"]\s*\+\s*)",
        "desc": "Direct string interpolation into SQL query allows attackers to alter query logic.",
        "remediation": "Use parameterized queries, prepared statements, or ORM bound parameters."
    },
    {
        "id": "SEC-003",
        "name": "Command Injection (Shell Execution)",
        "severity": "CRITICAL",
        "regex": r"(?i)\b(os\.system\s*\(|subprocess\.(?:call|check_call|Popen|run)\s*\(.*shell\s*=\s*True|child_process\.exec\s*\(|eval\s*\(|exec\s*\()",
        "desc": "Direct shell execution allows arbitrary OS command injection via unescaped inputs.",
        "remediation": "Use subprocess.run with argument arrays and shell=False. Never use eval/exec on user input."
    },
    {
        "id": "SEC-004",
        "name": "Cross-Site Scripting (XSS / Raw HTML)",
        "severity": "HIGH",
        "regex": r"(?i)\b(dangerouslySetInnerHTML\s*=|innerHTML\s*=|v-html\s*=|document\.write\s*\(|\$\s*\(.*\.html\s*\()",
        "desc": "Raw HTML rendering bypasses framework escaping and enables DOM-based XSS attacks.",
        "remediation": "Use safe text nodes (textContent, innerText) or sanitize input via DOMPurify."
    },
    {
        "id": "SEC-005",
        "name": "Path Traversal (Unvalidated File Open)",
        "severity": "HIGH",
        "regex": r"(?i)\b(open\s*\(\s*(?:f['\"].*\{|req\.(?:query|body|params)|request\.(?:args|form)|fs\.readFile(?:Sync)?\s*\(.*req\.))",
        "desc": "Opening files using unvalidated input allows directory traversal outside root.",
        "remediation": "Validate paths using os.path.abspath and verify they stay within intended directory."
    },
    {
        "id": "SEC-006",
        "name": "Insecure / Quantum-Vulnerable Cryptography",
        "severity": "HIGH",
        "regex": r"(?i)\b(hashlib\.(?:md5|sha1)\b|RSA\.generate|PKCS1_OAEP|DES\.new|ARC4\.new|createHash\s*\(\s*['\"](?:md5|sha1)['\"])",
        "desc": "Legacy or classical asymmetric cryptography susceptible to collision or quantum attacks.",
        "remediation": "Upgrade to SHA-256/SHA3 for hashing, AES-256 for symmetric, and NIST PQC (ML-KEM) for key exchange."
    },
    {
        "id": "SEC-007",
        "name": "Server-Side Request Forgery (SSRF)",
        "severity": "HIGH",
        "regex": r"(?i)\b(requests\.(?:get|post|put|delete)\s*\(\s*(?:req\.|request\.|url\s*=)|urllib\.request\.urlopen\s*\(\s*(?:req\.|request\.)|fetch\s*\(\s*(?:req\.body|req\.query))",
        "desc": "Unfiltered HTTP client calls with user-specified URLs enable SSRF to internal services.",
        "remediation": "Whitelist permitted hostnames and protocols; block private IP ranges (127.0.0.1, 169.254.169.254)."
    },
    {
        "id": "SEC-008",
        "name": "Production Debug Mode Enabled",
        "severity": "MEDIUM",
        "regex": r"(?i)\b(DEBUG\s*=\s*True|app\.run\(.*debug\s*=\s*True|display_errors\s*=\s*1|NODE_ENV\s*=\s*['\"]development['\"])",
        "desc": "Debug mode exposes stack traces, server environment, and interactive debug shells.",
        "remediation": "Ensure debug flags are disabled in production and controlled via environment variables."
    }
]

WATCHED_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".java", ".php", ".rb", ".cs", ".c", ".cpp", ".html"
}

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", ".next",
    "venv", ".venv", "__pycache__", "target", "vendor"
}

OLLAMA_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")


def scan_file_content(path: Path) -> List[Dict[str, Any]]:
    """Scan a single file against the security rules."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = content.splitlines()
    findings = []

    for rule in SECURITY_RULES:
        pattern = re.compile(rule["regex"])
        for idx, line in enumerate(lines, 1):
            # Skip self-referential signature definitions
            if '"regex":' in line or "r'(?i)" in line or 'r"(?i)' in line:
                continue
            if pattern.search(line):
                # Context snippet
                start = max(0, idx - 2)
                end = min(len(lines), idx + 2)
                context = "\n".join(f"  {i+1}: {lines[i]}" for i in range(start, end))

                findings.append({
                    "file": str(path),
                    "line": idx,
                    "rule_id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["desc"],
                    "remediation": rule["remediation"],
                    "code_snippet": line.strip(),
                    "context": context
                })

    return findings


def query_spectre_ai(finding: Dict[str, Any], model: str = "spectre") -> Optional[str]:
    """Consult local SPECTRE model for deep code audit and exploit analysis."""
    prompt = f"""You are SPECTRE, an elite offensive security researcher.
Analyze this code vulnerability discovered during real-time security watching:
File: {finding['file']} (Line {finding['line']})
Vulnerability: {finding['name']} [{finding['severity']}]
Rule ID: {finding['rule_id']}
Snippet:
{finding['context']}

Explain:
1. Exact attack payload or exploit vector.
2. How an adversary would leverage this in a real pentest.
3. Secure refactored replacement code."""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are SPECTRE, an elite cybersecurity auditor. Provide precise, technical analysis."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 768}
    }

    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content")
    except Exception as e:
        return f"[SPECTRE offline: {e}]"


def log_findings(findings: List[Dict[str, Any]], log_file: Path):
    """Append structured findings to markdown security log."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.write_text("# SPECTRE Continuous Security Audit Log\n\n", encoding="utf-8")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entries = []
    for f in findings:
        entries.append(f"### [{timestamp}] [{f['severity']}] {f['name']} ({f['rule_id']})\n")
        entries.append(f"- **File:** `{f['file']}` (Line {f['line']})\n")
        entries.append(f"- **Vulnerability:** {f['description']}\n")
        entries.append(f"- **Remediation:** {f['remediation']}\n\n")
        entries.append("```\n" + f['context'] + "\n```\n")
        if f.get("ai_analysis"):
            entries.append("#### SPECTRE Exploit & Fix Blueprint:\n")
            entries.append(f"{f['ai_analysis']}\n")
        entries.append("\n---\n\n")

    with open(log_file, "a", encoding="utf-8") as lf:
        lf.writelines(entries)


def print_alert(finding: Dict[str, Any]):
    """Print high-visibility terminal alert."""
    colors = {
        "CRITICAL": "\033[91m",
        "HIGH": "\033[93m",
        "MEDIUM": "\033[94m"
    }
    reset = "\033[0m"
    color = colors.get(finding["severity"], "\033[97m")

    print(f"\n{color}[!] SECURITY ALERT [{finding['severity']}]: {finding['name']}{reset}")
    print(f"    File: {finding['file']}:{finding['line']}")
    print(f"    Code: {finding['code_snippet'][:75]}")
    print(f"    Fix : {finding['remediation']}")


def scan_directory(target_path: Path, ai_assist: bool = False, model: str = "spectre") -> List[Dict[str, Any]]:
    """Scan all qualifying files under target_path."""
    all_findings = []
    files_to_scan = []

    if target_path.is_file():
        files_to_scan.append(target_path)
    else:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                p = Path(root) / file
                if p.suffix.lower() in WATCHED_EXTS:
                    files_to_scan.append(p)

    for p in files_to_scan:
        findings = scan_file_content(p)
        for f in findings:
            if ai_assist:
                f["ai_analysis"] = query_spectre_ai(f, model)
            all_findings.append(f)

    return all_findings


def watch_directory(target_path: Path, log_file: Path, ai_assist: bool = False, model: str = "spectre"):
    """Background file watcher daemon monitoring project files on save."""
    print(f"[*] SPECTRE Continuous Security Daemon active.")
    print(f"    Watching: {target_path.resolve()}")
    print(f"    Log File: {log_file.resolve()}")
    print(f"    AI Mode : {'SPECTRE (' + model + ')' if ai_assist else 'Static Rules Engine'}")
    print("    Press Ctrl+C to stop.\n")

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class WatcherHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.is_directory:
                    return
                p = Path(event.src_path)
                if p.suffix.lower() in WATCHED_EXTS:
                    findings = scan_file_content(p)
                    if findings:
                        print(f"\n[~] File modified: {p.name} -> {len(findings)} vulnerability alerts!")
                        for f in findings:
                            print_alert(f)
                            if ai_assist:
                                print(f"    [*] Consulting local SPECTRE model for {f['name']}...")
                                f["ai_analysis"] = query_spectre_ai(f, model)
                        log_findings(findings, log_file)
                        print(f"[+] Logged findings to {log_file.name}")

        observer = Observer()
        observer.schedule(WatcherHandler(), str(target_path), recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    except ImportError:
        # Fallback polling loop if watchdog is not available
        print("[!] watchdog library not found; running in high-efficiency polling mode.")
        mtimes: Dict[str, float] = {}
        try:
            while True:
                for root, dirs, files in os.walk(target_path):
                    dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                    for f in files:
                        p = Path(root) / f
                        if p.suffix.lower() in WATCHED_EXTS:
                            try:
                                mtime = p.stat().st_mtime
                                key = str(p)
                                if key in mtimes and mtime > mtimes[key]:
                                    findings = scan_file_content(p)
                                    if findings:
                                        print(f"\n[~] File modified: {p.name} -> {len(findings)} alerts!")
                                        for fnd in findings:
                                            print_alert(fnd)
                                            if ai_assist:
                                                fnd["ai_analysis"] = query_spectre_ai(fnd, model)
                                        log_findings(findings, log_file)
                                mtimes[key] = mtime
                            except Exception:
                                pass
                time.sleep(1.5)
        except KeyboardInterrupt:
            print("\n[*] Daemon stopped.")


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Continuous Security Background Daemon")
    parser.add_argument("--watch", help="Directory to monitor continuously for modified files")
    parser.add_argument("--scan", help="One-shot scan of a file or directory")
    parser.add_argument("--pre-commit", action="store_true", help="Exit with code 1 if CRITICAL vulnerabilities are found (for Git hooks)")
    parser.add_argument("--ai-assist", action="store_true", help="Consult local SPECTRE model on findings")
    parser.add_argument("--model", default="spectre", help="Model persona for AI consultation (default: spectre)")
    parser.add_argument("--log", default="security_log.md", help="Output security log path (default: security_log.md)")

    args = parser.parse_args()

    log_path = Path(args.log).resolve()

    if args.watch:
        watch_directory(Path(args.watch), log_path, ai_assist=args.ai_assist, model=args.model)
        return

    if args.scan:
        target = Path(args.scan).resolve()
        print(f"[*] Running SPECTRE security scan on '{target}'...")
        findings = scan_directory(target, ai_assist=args.ai_assist, model=args.model)

        critical_count = sum(1 for f in findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in findings if f["severity"] == "HIGH")
        medium_count = sum(1 for f in findings if f["severity"] == "MEDIUM")

        print("=" * 70)
        print("             SPECTRE CONTINUOUS SECURITY SCAN REPORT              ")
        print("=" * 70)
        print(f"Target Path     : {target}")
        print(f"Total Findings  : {len(findings)} (Critical: {critical_count}, High: {high_count}, Medium: {medium_count})")
        print("-" * 70)

        for idx, f in enumerate(findings, 1):
            print_alert(f)

        if findings:
            log_findings(findings, log_path)
            print(f"\n[+] Detailed findings logged to {log_path}")

        print("=" * 70)

        if args.pre_commit and critical_count > 0:
            print(f"\n[!] Pre-commit check FAILED: {critical_count} CRITICAL security flaws detected.")
            sys.exit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
