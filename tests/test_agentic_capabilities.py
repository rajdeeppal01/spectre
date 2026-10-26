"""
Test Suite: SPECTRE Agentic Capabilities (Phases 1 - 4)
Verifies:
  Phase 1: manage_task (start, status, list, stop)
  Phase 2: browser_open & browser_interact (Playwright, DOM, screenshot, get_content)
  Phase 3: _compact_conversation_history (Context compaction & checkpoint generation)
  Phase 4: delegate_subagent (red_team_crew, web_audit, code_reviewer)
"""

import os
import sys
import time
from pathlib import Path

# Add scripts directory to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from spectre_dashboard import (
    _exec_manage_task,
    _exec_browser_open,
    _exec_browser_interact,
    _compact_conversation_history,
    _exec_delegate_subagent,
    _BACKGROUND_TASKS,
    OLLAMA_TOOLS,
    GEMINI_TOOLS
)

def test_phase1_manage_task():
    print("\n--- [Phase 1 Test: Background Task Daemon (manage_task)] ---")
    
    # 1. Start a simple HTTP server in background
    cmd = "python -m http.server 8765"
    start_res = _exec_manage_task("start", command=cmd)
    print("Start result exit code:", start_res.get("exit_code"))
    assert start_res.get("exit_code") == 0, f"Failed to start task: {start_res}"
    tid = start_res.get("task_id")
    assert tid is not None, "Missing task_id in start result"
    print(f"Task started with ID: {tid}, PID: {start_res.get('pid')}")

    # 2. Check task status & logs
    time.sleep(1.0)
    status_res = _exec_manage_task("status", task_id=tid, lines=10)
    print("Status result exit code:", status_res.get("exit_code"))
    assert status_res.get("exit_code") == 0, f"Failed to get status: {status_res}"
    print(f"Task status: {status_res.get('status')}, Uptime: {status_res.get('uptime')}s")

    # 3. List active tasks
    list_res = _exec_manage_task("list")
    assert list_res.get("exit_code") == 0, f"Failed to list tasks: {list_res}"
    assert tid in list_res.get("tasks", []), f"Task {tid} not found in task list"
    print("List tasks verified. Tracked tasks count:", len(list_res.get("tasks", [])))

    # 4. Stop background task
    stop_res = _exec_manage_task("stop", task_id=tid)
    assert stop_res.get("exit_code") == 0, f"Failed to stop task: {stop_res}"
    print(f"Task stopped: {stop_res.get('status')}")
    print("Phase 1 (manage_task): PASSED [OK]")

def test_phase2_browser_automation():
    print("\n--- [Phase 2 Test: Headless Browser & Visual Verification] ---")
    
    # Test navigating to local dashboard (assuming 127.0.0.1:5050 is active)
    target_url = "http://127.0.0.1:5050"
    open_res = _exec_browser_open(target_url, wait_ms=1000)
    print("Browser open exit code:", open_res.get("exit_code"))
    assert open_res.get("exit_code") == 0, f"Browser open failed: {open_res}"
    
    title = open_res.get("title", "")
    print(f"Page Title: '{title}'")
    assert "SPECTRE" in title or "Antigravity" in title or len(title) > 0, f"Unexpected title: {title}"

    shot = open_res.get("screenshot", "")
    print(f"Screenshot URL: {shot}")
    assert shot and shot.startswith("/screenshots/"), f"Invalid screenshot path: {shot}"
    abs_shot_path = ROOT / "dashboard" / shot.lstrip("/")
    assert abs_shot_path.exists(), f"Screenshot file not found on disk: {abs_shot_path}"
    print(f"Verified screenshot saved to disk: {abs_shot_path.stat().st_size} bytes")

    # Test browser interact: get_content
    interact_res = _exec_browser_interact("get_content")
    assert interact_res.get("exit_code") == 0, f"Browser interact failed: {interact_res}"
    print("Browser get_content succeeded (Output len:", len(interact_res.get("output", "")), ")")
    print("Phase 2 (browser_open & browser_interact): PASSED [OK]")

def test_phase3_context_compaction():
    print("\n--- [Phase 3 Test: Context Compaction & Checkpoint Summarizer] ---")
    
    # Construct a simulated 18-turn trajectory
    simulated_contents = [
        {"role": "user", "parts": [{"text": "Create an automated reporting pipeline and verify syntax."}]}
    ]
    for i in range(12):
        simulated_contents.append({
            "role": "model",
            "parts": [{"functionCall": {"name": "run_command", "args": {"command": f"echo step {i}"}}}]
        })
        simulated_contents.append({
            "role": "user",
            "parts": [{"functionResponse": {"name": "run_command", "content": {"output": f"step {i} output"}}}]
        })

    initial_len = len(simulated_contents)
    print(f"Initial conversation trajectory turns: {initial_len}")

    notice = _compact_conversation_history(simulated_contents, max_turns=6)
    print("Compaction notice:", notice)
    assert notice is not None, "Expected context compaction to trigger"
    assert "Consolidated" in notice or "Compacted" in notice

    print(f"Compacted conversation trajectory turns: {len(simulated_contents)}")
    assert len(simulated_contents) < initial_len, "Expected turns count to be reduced"
    
    # Verify checkpoint markdown was injected
    has_checkpoint = any("AUTONOMOUS CONTEXT COMPACTION CHECKPOINT" in str(p) for turn in simulated_contents for p in turn.get("parts", []))
    assert has_checkpoint, "Checkpoint marker missing in compacted history"
    print("Phase 3 (Context Compaction): PASSED [OK]")

def test_phase4_subagent_delegation():
    print("\n--- [Phase 4 Test: Multi-Agent Delegation (delegate_subagent)] ---")
    
    # 1. Test Code Reviewer crew
    print("Testing code_reviewer delegation...")
    cr_res = _exec_delegate_subagent("code_reviewer", "Audit codebase cleanliness and secrets baseline", target=".")
    print("Code reviewer exit code:", cr_res.get("exit_code"))
    assert "code_reviewer" in cr_res.get("subagent", "")
    assert "Code Review" in cr_res.get("output", "")
    print("Code Reviewer report sample:\n", cr_res.get("output")[:200], "\n...")

    # 2. Test Red Team Crew delegation
    print("Testing red_team_crew delegation...")
    rt_res = _exec_delegate_subagent("red_team_crew", "Scan for secret leaks and cryptographic posture", target=".")
    assert "red_team_crew" in rt_res.get("subagent", "")
    assert "Stage 1" in rt_res.get("output", "")
    print("Red Team Crew report sample:\n", rt_res.get("output")[:200], "\n...")

    # 3. Test Web Audit delegation
    print("Testing web_audit delegation...")
    wa_res = _exec_delegate_subagent("web_audit", "Audit frontend accessibility and console health", target="http://127.0.0.1:5050")
    assert wa_res.get("exit_code") == 0
    assert "web_audit" in wa_res.get("subagent", "")
    assert wa_res.get("screenshot", "").startswith("/screenshots/")
    print("Web Audit report sample:\n", wa_res.get("output")[:200], "\n...")

    print("Phase 4 (Multi-Agent Delegation): PASSED [OK]")

def test_tool_declarations():
    print("\n--- [Tool Declarations Verification] ---")
    ollama_names = [t["function"]["name"] for t in OLLAMA_TOOLS]
    gemini_names = [f["name"] for t in GEMINI_TOOLS for f in t["functionDeclarations"]]

    for req_tool in ["manage_task", "browser_open", "browser_interact", "delegate_subagent"]:
        assert req_tool in ollama_names, f"Missing tool in OLLAMA_TOOLS: {req_tool}"
        assert req_tool in gemini_names, f"Missing tool in GEMINI_TOOLS: {req_tool}"
        print(f"Tool verified in Ollama & Gemini declarations: {req_tool} [OK]")

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING SPECTRE AGENTIC CAPABILITIES TEST SUITE (PHASES 1-4)")
    print("=" * 60)
    test_tool_declarations()
    test_phase1_manage_task()
    test_phase2_browser_automation()
    test_phase3_context_compaction()
    test_phase4_subagent_delegation()
    print("=" * 60)
    print("ALL 4 PHASES VERIFIED AND PASSED WITH ZERO ERRORS!")
    print("=" * 60)
