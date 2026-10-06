"""
SPECTRE — Web Audit Bridge
Bridges Burp Suite HTTP history to the SPECTRE AI for automated
vulnerability discovery (SQLi, XSS, CSRF, IDOR, Logic Flaws).

Usage:
    1. In Burp Suite: Project Options -> Save project / Export HTTP history (XML)
    2. python agents/web_audit_bridge.py --history burp_history.xml
"""

import argparse
import xml.etree.ElementTree as ET
import json
import base64
from pathlib import Path
from openai import OpenAI

# ── Configuration ─────────────────────────────────────────────
# Force all requests to local SPECTRE model
CLIENT = OpenAI(base_url="http://localhost:11434/v1", api_key="none")
MODEL = "spectre"

SYSTEM_PROMPT = """You are SPECTRE, an elite web application security researcher.
Analyze this HTTP Request/Response pair. Look for:
1. SQL Injection / NoSQL Injection
2. Cross-Site Scripting (XSS)
3. Broken Authentication / JWT weaknesses
4. Insecure Direct Object References (IDOR)
5. Business Logic Flaws

If a vulnerability is found, explain WHY it is vulnerable and provide a 
Proof of Concept payload to verify it. If no vulnerability is apparent, state "No obvious vulnerabilities found."
Keep answers concise and technical."""

def parse_burp_xml(xml_path: str) -> list[dict]:
    """Parse Burp Suite XML export into a list of request/response dicts."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    items = []
    
    for item in root.findall('item'):
        # Burp Base64 encodes requests/responses
        req_b64 = item.find('request').text
        res_b64 = item.find('response').text
        
        try:
            req = base64.b64decode(req_b64).decode('utf-8', errors='replace') if req_b64 else ""
            res = base64.b64decode(res_b64).decode('utf-8', errors='replace') if res_b64 else ""
        except Exception:
            req, res = "", ""
            
        url = item.find('url').text
        method = item.find('method').text
        
        items.append({
            "url": url,
            "method": method,
            "request": req,
            "response": res
        })
    return items

def analyze_traffic(item: dict) -> str:
    """Send HTTP traffic to SPECTRE for analysis."""
    prompt = f"""URL: {item['url']}
Method: {item['method']}

--- HTTP REQUEST ---
{item['request'][:2000]}  # Truncate to avoid massive token usage

--- HTTP RESPONSE (Truncated) ---
{item['response'][:2000]}
"""
    
    try:
        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing request: {e}"

def main():
    parser = argparse.ArgumentParser(description="SPECTRE Web Audit Bridge")
    parser.add_argument("--history", required=True, help="Path to Burp Suite XML history export")
    parser.add_argument("--out", default="web_audit_report.md", help="Output Markdown report")
    args = parser.parse_args()
    
    print(f"[*] Loading Burp history from {args.history}...")
    try:
        items = parse_burp_xml(args.history)
    except Exception as e:
        print(f"[!] Failed to parse XML: {e}")
        return
        
    print(f"[*] Found {len(items)} HTTP items. Starting SPECTRE analysis...")
    
    report_content = f"# SPECTRE Web Application Audit\n**Source:** {args.history}\n\n"
    
    for i, item in enumerate(items, 1):
        print(f"  [{i}/{len(items)}] Analyzing {item['method']} {item['url']}...")
        analysis = analyze_traffic(item)
        
        report_content += f"## {i}. {item['method']} {item['url']}\n"
        report_content += f"```http\n{item['request'].splitlines()[0]} ...\n```\n"
        report_content += f"**SPECTRE Analysis:**\n{analysis}\n\n---\n"
        
    Path(args.out).write_text(report_content)
    print(f"\n[+] Audit complete. Report saved to {args.out}")

if __name__ == "__main__":
    main()
