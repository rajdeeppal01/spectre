"""
SPECTRE — Recon Pipeline
Runs Nmap against a target, parses the results, and sends them to the
SPECTRE model (local, offline) for CVE mapping and exploit identification.

Usage:
    python scripts/recon_pipeline.py --target 192.168.1.1
    python scripts/recon_pipeline.py --target 192.168.1.0/24 --output reports/
    python scripts/recon_pipeline.py --target example.com --ports 80,443,8080

IMPORTANT: Only run against systems you own or have explicit written
           authorisation to test. Unauthorised scanning is illegal.
"""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ── Configuration ─────────────────────────────────────────────
# SPECTRE model always calls local Ollama directly.
# This endpoint is NEVER routed to any cloud service.
SPECTRE_CLIENT = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="none",  # Ollama doesn't require auth
)
SPECTRE_MODEL = "spectre"  # The custom Ollama persona

SPECTRE_SYSTEM_PROMPT = """You are SPECTRE, an elite penetration tester and vulnerability researcher.
You have been given Nmap scan results. Your task is to:

1. Identify all open services and their versions
2. List known CVEs for each service with CVSS score and exploitability rating
3. For each critical/high CVE, provide:
   - CVE identifier
   - Vulnerability description
   - Working Metasploit module name (if available) OR working PoC script
   - Exploitation difficulty: Easy / Medium / Hard
4. Recommend an attack order (highest impact, lowest complexity first)
5. Identify any quick wins (default credentials, unpatched services, misconfigurations)

Return your analysis as structured JSON matching this schema:
{
  "target": "string",
  "scan_time": "string",
  "open_services": [...],
  "vulnerabilities": [...],
  "attack_priority": [...],
  "quick_wins": [...]
}"""


def run_nmap(target: str, ports: str | None = None, output_dir: Path | None = None) -> tuple[str, Path]:
    """
    Execute Nmap scan and return (xml_output_string, xml_file_path).
    Runs: nmap -sV -sC -O --script=vuln -p<ports> <target> -oX <file>
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_target = target.replace("/", "_").replace(".", "_")

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        xml_path = output_dir / f"nmap_{safe_target}_{timestamp}.xml"
    else:
        xml_path = Path(f"/tmp/nmap_{safe_target}_{timestamp}.xml")

    port_arg = f"-p{ports}" if ports else "-p-"  # -p- = all 65535 ports

    cmd = [
        "nmap",
        "-sV",           # Service version detection
        "-sC",           # Default scripts
        "-O",            # OS detection
        "--script=vuln", # Vulnerability scripts
        port_arg,
        target,
        "-oX", str(xml_path),
        "--open",        # Only show open ports
    ]

    print(f"\n[SPECTRE RECON] Starting Nmap scan of {target}...")
    print(f"  Command: {' '.join(cmd)}")
    print(f"  Output:  {xml_path}")
    print(f"  This may take several minutes for a full port scan...\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0 and not xml_path.exists():
            print(f"[!] Nmap error: {result.stderr}")
            sys.exit(1)
    except FileNotFoundError:
        print("[!] Nmap not found. Install it: https://nmap.org/download.html")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("[!] Nmap scan timed out after 10 minutes. Try narrowing the port range.")
        sys.exit(1)

    return xml_path.read_text(), xml_path


def parse_nmap_xml(xml_string: str) -> dict:
    """Parse Nmap XML output into a structured dictionary."""
    root = ET.fromstring(xml_string)
    results = {
        "hosts": [],
        "scan_args": root.get("args", ""),
        "scan_start": root.get("startstr", ""),
    }

    for host in root.findall("host"):
        # Get IP/hostname
        addresses = {}
        for addr in host.findall("address"):
            addr_type = addr.get("addrtype", "")
            addresses[addr_type] = addr.get("addr", "")

        hostnames = []
        for hn in host.findall(".//hostname"):
            hostnames.append(hn.get("name", ""))

        # Get open ports and services
        ports = []
        for port in host.findall(".//port"):
            state = port.find("state")
            if state is None or state.get("state") != "open":
                continue

            service = port.find("service")
            service_info = {}
            if service is not None:
                service_info = {
                    "name": service.get("name", "unknown"),
                    "product": service.get("product", ""),
                    "version": service.get("version", ""),
                    "extrainfo": service.get("extrainfo", ""),
                    "cpe": service.get("cpe", ""),
                }

            # Get script output (vuln scripts)
            scripts = {}
            for script in port.findall("script"):
                scripts[script.get("id", "")] = script.get("output", "")

            ports.append({
                "port": port.get("portid"),
                "protocol": port.get("protocol"),
                "service": service_info,
                "scripts": scripts,
            })

        # OS detection
        os_matches = []
        for osmatch in host.findall(".//osmatch"):
            os_matches.append({
                "name": osmatch.get("name", ""),
                "accuracy": osmatch.get("accuracy", ""),
            })

        results["hosts"].append({
            "addresses": addresses,
            "hostnames": hostnames,
            "ports": ports,
            "os_matches": os_matches[:3],  # Top 3 OS guesses
        })

    return results


def analyse_with_spectre(parsed_scan: dict, target: str) -> dict:
    """
    Send parsed scan data to SPECTRE model for CVE mapping and exploit identification.
    Returns structured JSON analysis.
    """
    scan_summary = json.dumps(parsed_scan, indent=2)

    prompt = f"""Target: {target}

Nmap Scan Results:
{scan_summary}

Provide your complete penetration testing analysis."""

    print("\n[SPECTRE AI] Sending scan results to SPECTRE model for analysis...")
    print("  (Running locally — no data sent externally)\n")

    try:
        response = SPECTRE_CLIENT.chat.completions.create(
            model=SPECTRE_MODEL,
            messages=[
                {"role": "system", "content": SPECTRE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # Low temp for precise, factual CVE output
            max_tokens=4096,
            stream=True,
        )

        # Stream output to terminal as it generates
        full_response = ""
        print("  SPECTRE Analysis:")
        print("  " + "─" * 60)
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            print(delta, end="", flush=True)
            full_response += delta
        print("\n  " + "─" * 60)

        # Try to parse as JSON, fall back to raw text
        try:
            # Find JSON block in response
            start = full_response.find("{")
            end = full_response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(full_response[start:end])
        except json.JSONDecodeError:
            pass

        return {"raw_analysis": full_response, "target": target}

    except Exception as e:
        print(f"\n[!] Error calling SPECTRE model: {e}")
        print("    Is Ollama running? Check: docker ps | grep ollama")
        return {"error": str(e), "target": target}


def save_report(analysis: dict, target: str, output_dir: Path | None = None) -> Path:
    """Save the analysis report as JSON and human-readable Markdown."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_target = target.replace("/", "_").replace(".", "_")

    report_dir = output_dir or Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = report_dir / f"recon_{safe_target}_{timestamp}.json"
    json_path.write_text(json.dumps(analysis, indent=2))

    # Markdown report
    md_path = report_dir / f"recon_{safe_target}_{timestamp}.md"
    md_content = f"""# SPECTRE Reconnaissance Report
**Target:** {target}  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Classification:** CONFIDENTIAL — Authorized Testing Only

---

## AI Analysis (SPECTRE Model)

```json
{json.dumps(analysis, indent=2)}
```
"""
    md_path.write_text(md_content)

    return md_path


def main():
    parser = argparse.ArgumentParser(
        description="SPECTRE Recon Pipeline — Nmap → AI CVE Analysis"
    )
    parser.add_argument("--target", required=True, help="Target IP, hostname, or CIDR range")
    parser.add_argument("--ports", help="Port range (e.g. 80,443 or 1-1000). Default: all ports")
    parser.add_argument("--output", help="Output directory for reports", default="reports")
    parser.add_argument("--skip-nmap", help="Skip Nmap, use existing XML file", metavar="XML_FILE")
    args = parser.parse_args()

    output_dir = Path(args.output)

    print("\n" + "=" * 60)
    print("  SPECTRE RECONNAISSANCE PIPELINE")
    print("  ⚠  FOR AUTHORIZED PENETRATION TESTING ONLY")
    print("=" * 60)

    # Get scan data
    if args.skip_nmap:
        print(f"\n[*] Loading existing scan: {args.skip_nmap}")
        xml_string = Path(args.skip_nmap).read_text()
        xml_path = Path(args.skip_nmap)
    else:
        xml_string, xml_path = run_nmap(args.target, args.ports, output_dir)

    # Parse Nmap XML
    print("[*] Parsing scan results...")
    parsed = parse_nmap_xml(xml_string)

    total_open = sum(len(h["ports"]) for h in parsed["hosts"])
    print(f"  Found {len(parsed['hosts'])} host(s), {total_open} open port(s)")

    if total_open == 0:
        print("\n[!] No open ports found. Target may be down or blocking scans.")
        sys.exit(0)

    # SPECTRE AI analysis
    analysis = analyse_with_spectre(parsed, args.target)
    analysis["nmap_xml_path"] = str(xml_path)

    # Save reports
    report_path = save_report(analysis, args.target, output_dir)
    print(f"\n✓ Report saved: {report_path}")
    print(f"  JSON:     {report_path.with_suffix('.json')}")
    print(f"  Markdown: {report_path}")
    print("\n[SPECTRE] Reconnaissance complete.\n")


if __name__ == "__main__":
    main()
