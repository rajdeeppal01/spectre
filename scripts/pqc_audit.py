"""
SPECTRE — Post-Quantum Cryptography (PQC) Auditor & Migration Engine
Scans codebases for classical cryptographic primitives vulnerable to quantum
attacks (RSA, ECC, DH, DSA) and weak symmetric ciphers. Generates remediation
guidance aligned with NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA).

Usage:
    python scripts/pqc_audit.py --path ./src
    python scripts/pqc_audit.py --path ./src --ai-assist --model spectre
    python scripts/pqc_audit.py --path ./src --output pqc_report.md --json pqc_report.json
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

# ── Cryptographic Vulnerability Signatures ────────────────────────
# Maps classical cryptography patterns to NIST PQC migration pathways
VULN_PATTERNS = [
    {
        "id": "PQC-VULN-001",
        "category": "Asymmetric Key Exchange / Encryption",
        "name": "RSA Encryption / Decryption",
        "regex": r"(?i)\b(RSA\.generate|PKCS1_OAEP|RSA_PKCS1_PADDING|generate_private_key\s*\(\s*backend\s*=\s*default_backend\s*\(\)\s*,\s*public_exponent|rsa_new|crypto/rsa|import\s+rsa\b|from\s+rsa\s+import|from\s+Crypto\.PublicKey\s+import\s+RSA|crypto\.generateKeyPairSync\s*\(\s*['\"]rsa['\"])",
        "severity": "CRITICAL",
        "impact": "Shor's algorithm breaks integer factorization in polynomial time O((log N)^3). Subject to Harvest-Now-Decrypt-Later (HNDL) attacks.",
        "pqc_standard": "NIST FIPS 203 (ML-KEM / Module-Lattice Key Encapsulation)",
        "recommendation": "Migrate to ML-KEM-768 (standard security) or ML-KEM-1024 (high security). For hybrid TLS, adopt X25519MLKEM768."
    },
    {
        "id": "PQC-VULN-002",
        "category": "Asymmetric Key Exchange",
        "name": "Classical Diffie-Hellman / ECDH",
        "regex": r"(?i)\b(DiffieHellman|ECDH|curve25519|secp256k1|secp384r1|prime256v1|crypto/ecdh|X25519\b(?!MLKEM)|generate_key_pair\s*\(\s*ec\.SECP|generateKey\s*\(\s*['\"]ecdh['\"])",
        "severity": "CRITICAL",
        "impact": "Discrete logarithm problem over finite fields and elliptic curves is solved in polynomial time by Shor's algorithm. All past recorded ciphertexts are decryptable once CRQC exists.",
        "pqc_standard": "NIST FIPS 203 (ML-KEM-768 / X25519MLKEM768 Hybrid)",
        "recommendation": "Replace classical DH/ECDH with ML-KEM-768 or hybrid X25519MLKEM768 in TLS 1.3 cipher suites."
    },
    {
        "id": "PQC-VULN-003",
        "category": "Digital Signatures",
        "name": "ECDSA / RSA Signatures",
        "regex": r"(?i)\b(ecdsa\.SigningKey|PKCS1_v1_5|PSS\.new|ec\.ECDSA|crypto\.createSign\s*\(\s*['\"]RSA-|crypto\.createSign\s*\(\s*['\"]sha256WithRSAEncryption['\"]|jwt\.sign\(.*algorithms?:\s*\[?['\"](RS256|ES256|ES384|ES512)['\"])",
        "severity": "HIGH",
        "impact": "Quantum computers can forge signatures retroactively by solving discrete logarithms or factoring, breaking non-repudiation and identity verification.",
        "pqc_standard": "NIST FIPS 204 (ML-DSA / Crystals-Dilithium) & NIST FIPS 205 (SLH-DSA / SPHINCS+)",
        "recommendation": "Migrate authentication tokens and document signing to ML-DSA-65 (primary) or SLH-DSA-SHA2-128s (hash-based stateless backup)."
    },
    {
        "id": "PQC-VULN-004",
        "category": "Digital Signatures",
        "name": "Ed25519 / Ed448 Classical Edwards Curves",
        "regex": r"(?i)\b(Ed25519PublicKey|Ed25519PrivateKey|nacl\.signing|crypto/ed25519|crypto\.generateKeyPairSync\s*\(\s*['\"]ed25519['\"])",
        "severity": "HIGH",
        "impact": "While resilient classically, Edwards curve discrete logarithms collapse under Shor's period-finding quantum algorithm.",
        "pqc_standard": "NIST FIPS 204 (ML-DSA-44 or ML-DSA-65)",
        "recommendation": "Transition to ML-DSA-65 or hybrid composite Ed25519+ML-DSA dual signatures."
    },
    {
        "id": "PQC-VULN-005",
        "category": "Symmetric Ciphers (Grover Vulnerable)",
        "name": "Short Symmetric Key / AES-128",
        "regex": r"(?i)\b(AES\.new\(.*key_size\s*=\s*128|crypto\.createCipheriv\s*\(\s*['\"]aes-128|Cipher\s*\(\s*algorithms\.AES\(.*16\s*\)|AES128_GCM)",
        "severity": "MEDIUM",
        "impact": "Grover's algorithm reduces brute-force search complexity from O(2^N) to O(2^(N/2)). AES-128 provides only 64 bits of effective quantum security.",
        "pqc_standard": "NIST SP 800-131A Rev 2 & AES-256",
        "recommendation": "Upgrade all symmetric key lengths to AES-256 (GCM/XTS), which provides 128 bits of security against Grover quantum search."
    },
    {
        "id": "PQC-VULN-006",
        "category": "Broken Primitives",
        "name": "Legacy Hashes (MD5, SHA-1, DES, RC4)",
        "regex": r"(?i)\b(hashlib\.(md5|sha1)\b|Crypto\.Cipher\.(DES|ARC4|Blowfish)|createHash\s*\(\s*['\"](md5|sha1)['\"]|crypto/des|crypto/rc4)",
        "severity": "HIGH",
        "impact": "Classically broken collision resistance, utterly compromised in a quantum or hybrid attack regime.",
        "pqc_standard": "NIST FIPS 180-4 / FIPS 202 (SHA-256, SHA-384, SHA3-256, SHAKE-256)",
        "recommendation": "Immediately replace with SHA-256, SHA-512, or SHA3-256/SHAKE-256."
    }
]

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".rb", ".yaml", ".yml", ".json"
}

IGNORE_DIRS = {
    ".git", "node_modules", "vendor", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", ".turbo", "target", "bin", "obj"
}


class PQCAuditor:
    def __init__(self, target_path: str, ai_assist: bool = False, model: str = "spectre"):
        self.target_path = Path(target_path).resolve()
        self.ai_assist = ai_assist
        self.model = model
        self.findings: List[Dict[str, Any]] = []
        self.scanned_files = 0
        self.ollama_endpoint = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")

    def scan_file(self, file_path: Path):
        self.scanned_files += 1
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return

        lines = content.splitlines()
        for pattern in VULN_PATTERNS:
            regex = re.compile(pattern["regex"])
            for line_no, line in enumerate(lines, 1):
                match = regex.search(line)
                if match:
                    # Extract surrounding context (3 lines before and after)
                    start = max(0, line_no - 4)
                    end = min(len(lines), line_no + 3)
                    context_snippet = "\n".join(
                        f"{i+1}: {lines[i]}" for i in range(start, end)
                    )

                    self.findings.append({
                        "file": str(file_path.relative_to(self.target_path) if self.target_path.is_dir() else file_path.name),
                        "absolute_path": str(file_path),
                        "line": line_no,
                        "matched_code": line.strip(),
                        "context": context_snippet,
                        "vuln_id": pattern["id"],
                        "name": pattern["name"],
                        "category": pattern["category"],
                        "severity": pattern["severity"],
                        "impact": pattern["impact"],
                        "pqc_standard": pattern["pqc_standard"],
                        "recommendation": pattern["recommendation"],
                        "ai_remediation": None
                    })

    def run_scan(self):
        if self.target_path.is_file():
            self.scan_file(self.target_path)
            return

        for root, dirs, files in os.walk(self.target_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    self.scan_file(Path(root) / file)

    def query_ai_remediation(self, finding: Dict[str, Any]) -> str:
        """Query local SPECTRE or ORACLE model for PQC code migration advice."""
        prompt = f"""You are SPECTRE, an expert in Post-Quantum Cryptography and quantum-safe migration.
Analyze this quantum-vulnerable cryptographic finding:
File: {finding['file']} (Line {finding['line']})
Vulnerability: {finding['name']} ({finding['vuln_id']})
Severity: {finding['severity']}
Snippet:
```
{finding['context']}
```

Provide:
1. Exact quantum threat mechanism (Shor / Grover / HNDL risk).
2. Production-ready, drop-in replacement code implementing the NIST Post-Quantum standard: {finding['pqc_standard']}.
   Use modern libraries (e.g. liboqs-python, modern OpenSSL 3.2+ PQC bindings, Go 1.24 crypto, or Node.js 22+).
Keep the response crisp, accurate, and completely production-focused."""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are SPECTRE, an elite post-quantum cryptographer and security researcher. Provide working, production-grade quantum-safe code."},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 1024}
        }

        try:
            req = urllib.request.Request(
                f"{self.ollama_endpoint}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "No AI response received.")
        except Exception as e:
            return f"[AI consultation unavailable: {e}]"

    def enrich_with_ai(self):
        if not self.ai_assist or not self.findings:
            return
        print(f"\n[*] Enriching {len(self.findings)} findings with local {self.model.upper()} AI guidance...")
        for idx, finding in enumerate(self.findings, 1):
            print(f"    [{idx}/{len(self.findings)}] Consulting {self.model.upper()} for {finding['name']} at {finding['file']}:{finding['line']}...")
            finding["ai_remediation"] = self.query_ai_remediation(finding)

    def generate_markdown_report(self) -> str:
        critical_count = sum(1 for f in self.findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in self.findings if f["severity"] == "HIGH")
        medium_count = sum(1 for f in self.findings if f["severity"] == "MEDIUM")

        md = []
        md.append("# SPECTRE Post-Quantum Cryptography (PQC) Audit Report")
        md.append(f"**Target:** `{self.target_path}`  ")
        md.append(f"**Scanned Files:** {self.scanned_files}  ")
        md.append(f"**Total Findings:** {len(self.findings)} (Critical: {critical_count}, High: {high_count}, Medium: {medium_count})\n")
        md.append("---")
        md.append("## Executive Summary")
        if critical_count > 0:
            md.append("> **ALERT: CRITICAL QUANTUM EXPOSURE DETECTED.**  ")
            md.append("> Asymmetric encryption or key exchange algorithms (RSA/ECDH) were detected. Data encrypted using these primitives is vulnerable to **Harvest Now, Decrypt Later (HNDL)** adversary operations prior to full quantum hardware availability.\n")
        else:
            md.append("No critical asymmetric key exchange vulnerabilities detected.\n")

        md.append("### NIST Post-Quantum Cryptography Reference Standards")
        md.append("- **NIST FIPS 203:** Module-Lattice-Based Key-Encapsulation Mechanism (**ML-KEM** / Kyber)")
        md.append("- **NIST FIPS 204:** Module-Lattice-Based Digital Signature Algorithm (**ML-DSA** / Dilithium)")
        md.append("- **NIST FIPS 205:** Stateless Hash-Based Digital Signature Algorithm (**SLH-DSA** / SPHINCS+)\n")
        md.append("---")
        md.append("## Detailed Findings\n")

        for idx, f in enumerate(self.findings, 1):
            md.append(f"### {idx}. [{f['severity']}] {f['name']} ({f['vuln_id']})")
            md.append(f"- **File:** `{f['file']}` (Line {f['line']})")
            md.append(f"- **Category:** {f['category']}")
            md.append(f"- **Quantum Threat Impact:** {f['impact']}")
            md.append(f"- **NIST Target Standard:** `{f['pqc_standard']}`")
            md.append(f"- **Recommended Action:** {f['recommendation']}\n")
            md.append("```\n" + f['context'] + "\n```\n")
            if f.get("ai_remediation"):
                md.append("#### SPECTRE PQC Migration Blueprint:")
                md.append(f['ai_remediation'] + "\n")
            md.append("---\n")

        return "\n".join(md)

    def print_terminal_summary(self):
        critical_count = sum(1 for f in self.findings if f["severity"] == "CRITICAL")
        high_count = sum(1 for f in self.findings if f["severity"] == "HIGH")
        medium_count = sum(1 for f in self.findings if f["severity"] == "MEDIUM")

        print("=" * 70)
        print("          SPECTRE POST-QUANTUM CRYPTOGRAPHY AUDIT RESULTS          ")
        print("=" * 70)
        print(f"Target Path    : {self.target_path}")
        print(f"Files Scanned  : {self.scanned_files}")
        print(f"Findings Found : {len(self.findings)}")
        print(f"Severity Breakdown: CRITICAL: {critical_count} | HIGH: {high_count} | MEDIUM: {medium_count}")
        print("-" * 70)

        for idx, f in enumerate(self.findings, 1):
            color = "\033[91m" if f["severity"] == "CRITICAL" else ("\033[93m" if f["severity"] == "HIGH" else "\033[94m")
            reset = "\033[0m"
            print(f"[{idx}] {color}[{f['severity']}]{reset} {f['name']} in {f['file']}:{f['line']}")
            print(f"    Target PQC Standard : {f['pqc_standard']}")
            print(f"    Code Match          : {f['matched_code'][:80]}")
            print()
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Post-Quantum Cryptography (PQC) Auditor")
    parser.add_argument("--path", required=True, help="Directory or file path to audit")
    parser.add_argument("--ai-assist", action="store_true", help="Consult local SPECTRE / ORACLE model for migration snippets")
    parser.add_argument("--model", default="spectre", help="Model persona to query for remediation (default: spectre)")
    parser.add_argument("--output", help="Path to save Markdown report (e.g., pqc_report.md)")
    parser.add_argument("--json", help="Path to save JSON report (e.g., pqc_report.json)")

    args = parser.parse_args()

    print(f"[*] Initializing SPECTRE PQC Security Engine on '{args.path}'...")
    auditor = PQCAuditor(target_path=args.path, ai_assist=args.ai_assist, model=args.model)
    auditor.run_scan()

    if args.ai_assist:
        auditor.enrich_with_ai()

    auditor.print_terminal_summary()

    if args.output:
        md_content = auditor.generate_markdown_report()
        Path(args.output).write_text(md_content, encoding="utf-8")
        print(f"[+] Markdown report written to {args.output}")

    if args.json:
        Path(args.json).write_text(json.dumps(auditor.findings, indent=2), encoding="utf-8")
        print(f"[+] JSON report written to {args.json}")


if __name__ == "__main__":
    main()
