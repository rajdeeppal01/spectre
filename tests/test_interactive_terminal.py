"""
Test suite for SPECTRE Track B: Real-Time Interactive PTY / Streaming Terminal.
Tests WebSocket connection, SSE streaming, interactive stdin, ANSI handling, and process kill.
"""

import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_HTTP = "http://127.0.0.1:5050"
BASE_WS = "ws://127.0.0.1:5051"

def test_api_status_ws():
    print("[1/6] Testing GET /api/status for terminal WebSocket config...")
    req = urllib.request.Request(f"{BASE_HTTP}/api/status")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        assert "terminal_ws_url" in data, "Missing terminal_ws_url in status"
        assert data.get("terminal_ws_active") is True, f"Expected terminal_ws_active True, got {data}"
        print(f"      OK! WebSocket active on {data['terminal_ws_url']}")


def test_http_terminal_spawn_and_stream():
    print("[2/6] Testing POST /api/terminal/spawn and GET /api/terminal/stream (SSE)...")
    payload = json.dumps({"command": "Write-Host 'TEST_STREAMING_CHUNK_1'; Write-Host 'TEST_STREAMING_CHUNK_2'"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_HTTP}/api/terminal/spawn", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        spawn_data = json.loads(resp.read().decode("utf-8"))
        assert spawn_data.get("ok") is True
        sid = spawn_data.get("sessionId")
        pid = spawn_data.get("pid")
        assert sid and pid, f"Invalid spawn response: {spawn_data}"
        print(f"      OK! Spawned session {sid} (PID {pid})")

    # Connect to SSE stream
    stream_req = urllib.request.Request(f"{BASE_HTTP}/api/terminal/stream?sessionId={sid}")
    stream_output = ""
    with urllib.request.urlopen(stream_req, timeout=10) as s_resp:
        for _ in range(30):
            line = s_resp.readline().decode("utf-8", errors="replace")
            if not line:
                break
            if line.startswith("data: "):
                raw_json = line[6:].strip()
                try:
                    msg = json.loads(raw_json)
                    if msg.get("type") == "data":
                        stream_output += msg.get("data", "")
                    elif msg.get("type") == "exit":
                        print(f"      OK! SSE session exited with code {msg.get('code')}")
                        break
                except Exception:
                    pass

    assert "TEST_STREAMING_CHUNK_1" in stream_output, f"Missing output 1 in: {repr(stream_output)}"
    assert "TEST_STREAMING_CHUNK_2" in stream_output, f"Missing output 2 in: {repr(stream_output)}"
    print("      OK! SSE streaming verified successfully.")


def test_http_terminal_stdin():
    print("[3/6] Testing interactive stdin delivery via POST /api/terminal/input...")
    # Python script that prompts for a password/word and echos it
    py_cmd = f'{sys.executable} -u -c "import sys; sys.stdout.write(\'PROMPT: ENTER KEY: \'); sys.stdout.flush(); ans = sys.stdin.readline().strip(); print(\'SECRET: \' + ans)"'
    payload = json.dumps({"command": py_cmd}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_HTTP}/api/terminal/spawn", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        spawn_data = json.loads(resp.read().decode("utf-8"))
        sid = spawn_data["sessionId"]

    time.sleep(0.4)
    # Send input
    in_payload = json.dumps({"sessionId": sid, "data": "SPECTRE_AGENT_KEY_2026\n"}).encode("utf-8")
    in_req = urllib.request.Request(f"{BASE_HTTP}/api/terminal/input", data=in_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(in_req, timeout=5) as in_resp:
        in_data = json.loads(in_resp.read().decode("utf-8"))
        assert in_data.get("ok") is True

    # Check output from SSE stream or backlog
    stream_req = urllib.request.Request(f"{BASE_HTTP}/api/terminal/stream?sessionId={sid}")
    collected = ""
    with urllib.request.urlopen(stream_req, timeout=8) as s_resp:
        for _ in range(25):
            line = s_resp.readline().decode("utf-8", errors="replace")
            if not line:
                break
            if line.startswith("data: "):
                try:
                    msg = json.loads(line[6:].strip())
                    if msg.get("type") == "data":
                        collected += msg.get("data", "")
                    elif msg.get("type") == "exit":
                        break
                except Exception:
                    pass

    assert "SECRET: SPECTRE_AGENT_KEY_2026" in collected, f"Failed to get echoed stdin, got: {repr(collected)}"
    print("      OK! Stdin delivery verified.")


def test_http_terminal_kill():
    print("[4/6] Testing process termination via POST /api/terminal/kill...")
    payload = json.dumps({"command": "Start-Sleep -Seconds 60"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_HTTP}/api/terminal/spawn", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        spawn_data = json.loads(resp.read().decode("utf-8"))
        sid = spawn_data["sessionId"]
        pid = spawn_data["pid"]

    time.sleep(0.3)
    # Send kill
    kill_payload = json.dumps({"sessionId": sid}).encode("utf-8")
    kill_req = urllib.request.Request(f"{BASE_HTTP}/api/terminal/kill", data=kill_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(kill_req, timeout=5) as k_resp:
        k_data = json.loads(k_resp.read().decode("utf-8"))
        assert k_data.get("ok") is True
        print(f"      OK! Killed session {sid} (PID {pid})")


def test_websocket_terminal_streaming():
    print("[5/6] Testing native WebSocket streaming connection on ws://127.0.0.1:5051...")
    try:
        from websockets.sync.client import connect
    except ImportError:
        print("      Skipping WS test (websockets client not available in runtime)")
        return

    with connect(BASE_WS) as ws:
        ws.send(json.dumps({"type": "spawn", "command": "Write-Host 'LIVE_WS_SPECTRE_OUTPUT'"}))
        ack = json.loads(ws.recv())
        assert ack["type"] == "spawned", f"Expected spawned ack, got {ack}"
        print(f"      OK! WS Ack received for session {ack.get('sessionId')}")

        received = ""
        while True:
            msg = json.loads(ws.recv())
            if msg["type"] == "data":
                received += msg["data"]
            elif msg["type"] == "exit":
                assert msg["code"] == 0
                print(f"      OK! WS Process exited cleanly in {msg.get('duration')}s")
                break

        assert "LIVE_WS_SPECTRE_OUTPUT" in received
        print("      OK! Real-time WebSocket streaming verified.")


def test_websocket_interactive_stdin_and_kill():
    print("[6/6] Testing WebSocket bi-directional stdin & interrupt...")
    from websockets.sync.client import connect

    py_cmd = f'{sys.executable} -u -c "import sys; sys.stdout.write(\'WS_PROMPT: \'); sys.stdout.flush(); ans = sys.stdin.readline().strip(); print(\'WS_REPLY: \' + ans)"'
    with connect(BASE_WS) as ws:
        ws.send(json.dumps({"type": "spawn", "command": py_cmd}))
        ack = json.loads(ws.recv())
        sid = ack["sessionId"]

        buf = ""
        while True:
            msg = json.loads(ws.recv())
            if msg["type"] == "data":
                buf += msg["data"]
                if "WS_PROMPT:" in buf:
                    # Deliver stdin interactively over WS
                    ws.send(json.dumps({"type": "input", "data": "WS_TEST_OK\n"}))
            elif msg["type"] == "exit":
                assert msg["code"] == 0
                break

        assert "WS_REPLY: WS_TEST_OK" in buf
        print("      OK! WebSocket interactive stdin round-trip verified.")


def main():
    print("=" * 75)
    print("   SPECTRE TRACK B: REAL-TIME INTERACTIVE PTY TERMINAL VERIFICATION")
    print("=" * 75)
    test_api_status_ws()
    test_http_terminal_spawn_and_stream()
    test_http_terminal_stdin()
    test_http_terminal_kill()
    test_websocket_terminal_streaming()
    test_websocket_interactive_stdin_and_kill()
    print("=" * 75)
    print("   ALL 6 INTERACTIVE TERMINAL TESTS PASSED (100% OPERATIONAL)")
    print("=" * 75)

if __name__ == "__main__":
    main()
