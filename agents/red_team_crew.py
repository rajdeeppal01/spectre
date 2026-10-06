"""
SPECTRE — Red Team Multi-Agent Crew
An automated penetration testing pipeline using CrewAI.
Connects 4 specialised agents to analyse a target, find exploits,
verify them, and write a report.

IMPORTANT: All agents communicate exclusively with local Ollama models.
           No data leaves the local network.

Usage:
    pip install crewai langchain-community
    python agents/red_team_crew.py --target "192.168.1.100"
"""

import argparse
import os
from pathlib import Path
from datetime import datetime

from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

# ── Configuration ─────────────────────────────────────────────
# Force all agents to use local Ollama
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "none"

# Initialize local LLMs
spectre_llm = Ollama(model="whiterabbitneo2:8b-q4_K_M") # Offensive
architect_llm = Ollama(model="devstral:7b-q4_K_M")      # Code review
atlas_llm = Ollama(model="qwen2.5:7b-instruct-q4_K_M")  # Reporting


def create_red_team_crew(target: str) -> Crew:
    """Instantiate the 4 agents and their tasks."""

    # ── Agents ────────────────────────────────────────────────
    scout = Agent(
        role="Reconnaissance Specialist (SCOUT)",
        goal=f"Analyze the attack surface of {target} and identify the 3 highest probability attack vectors.",
        backstory="You are an elite network reconnaissance expert. You map systems, identify running services, and correlate them with known CVEs.",
        verbose=True,
        allow_delegation=False,
        llm=spectre_llm
    )

    exploiter = Agent(
        role="Exploit Developer (EXPLOIT)",
        goal="Write working, weaponised proof-of-concept exploit code for the identified vulnerabilities.",
        backstory="You are a seasoned exploit developer. You take vulnerability reports and turn them into functional Python, Bash, or C payloads.",
        verbose=True,
        allow_delegation=False,
        llm=spectre_llm
    )

    reviewer = Agent(
        role="Security Code Reviewer (ARCHITECT)",
        goal="Review the exploit code for syntax errors, logic bugs, and operational safety.",
        backstory="You are a senior software engineer. You ensure that code is stable, handles errors gracefully, and won't crash the target system unintentionally.",
        verbose=True,
        allow_delegation=False,
        llm=architect_llm
    )

    reporter = Agent(
        role="Lead Penetration Tester (REPORTER)",
        goal="Synthesise all findings into a professional, client-ready penetration testing report.",
        backstory="You are the lead consultant. You translate deep technical findings into business risk and actionable remediation steps.",
        verbose=True,
        allow_delegation=False,
        llm=atlas_llm
    )

    # ── Tasks ─────────────────────────────────────────────────
    recon_task = Task(
        description=f"Assume an Nmap scan has been run against {target} revealing ports 22 (SSH OpenSSH 8.2), 80 (HTTP Apache 2.4.41), and 445 (SMB Samba 4.7.6). Identify the CVEs associated with these versions and select the most viable initial access vector.",
        expected_output="A list of 3 ranked vulnerabilities with CVE IDs and a selected primary attack path.",
        agent=scout
    )

    exploit_task = Task(
        description="Take the primary attack path identified by the Scout. Write a complete, standalone Python exploit script to gain initial access.",
        expected_output="A working Python exploit script with usage instructions.",
        agent=exploiter
    )

    review_task = Task(
        description="Review the Python exploit script written by the Exploit Developer. Fix any syntax errors, add exception handling, and ensure it accepts target IP as a command-line argument.",
        expected_output="The final, corrected, production-ready Python exploit script.",
        agent=reviewer
    )

    report_task = Task(
        description="Write an executive summary and technical details section for the final report. Include the vulnerability details, the exploit methodology (using the reviewed code), and remediation advice.",
        expected_output="A Markdown formatted penetration testing report.",
        agent=reporter
    )

    # ── Crew ──────────────────────────────────────────────────
    return Crew(
        agents=[scout, exploiter, reviewer, reporter],
        tasks=[recon_task, exploit_task, review_task, report_task],
        process=Process.sequential,
        verbose=True
    )


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Red Team Crew")
    parser.add_argument("--target", required=True, help="Target IP or hostname")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  SPECTRE RED TEAM CREW")
    print("  ⚠  FOR AUTHORIZED PENETRATION TESTING ONLY")
    print("=" * 60 + "\n")

    crew = create_red_team_crew(args.target)
    result = crew.kickoff()

    # Save output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"red_team_report_{timestamp}.md"
    
    out_file.write_text(f"# SPECTRE Red Team Operation: {args.target}\n\n{result}")
    print(f"\n[+] Operation complete. Report saved to {out_file}")


if __name__ == "__main__":
    main()
