import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://127.0.0.1:5050"

def test_workspace_tree_api():
    print("[1/6] Testing GET /api/workspace/tree ...")
    req = urllib.request.Request(f"{BASE_URL}/api/workspace/tree")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True, f"Expected ok: True, got {data}"
        assert "tree" in data, "Missing 'tree' in response"
        tree = data["tree"]
        assert len(tree) > 0, "Tree should have items"
        
        # Verify entries have expected schema
        names = [item["name"] for item in tree]
        assert "scripts" in names or "dashboard" in names or ".gitignore" in names, f"Expected common files, found {names}"
        print(f"      OK! Found {len(tree)} top-level workspace entries.")

def test_workspace_file_content_api():
    print("[2/6] Testing GET /api/workspace/file for text file ...")
    url = f"{BASE_URL}/api/workspace/file?path=scripts/spectre_dashboard.py"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True, f"Expected ok: True, got {data}"
        assert data.get("is_image") is False, "Expected is_image: False for python script"
        assert "import" in data.get("content", ""), "Expected python script content"
        assert data.get("lines_count", 0) > 1000, f"Expected >1000 lines, got {data.get('lines_count')}"
        assert data.get("size", 0) > 50000, f"Expected size >50KB, got {data.get('size')}"
        print(f"      OK! Loaded scripts/spectre_dashboard.py: {data['lines_count']} lines, {data['size']} bytes.")

def test_workspace_image_preview_api():
    print("[3/6] Testing GET /api/workspace/file for image preview ...")
    url = f"{BASE_URL}/api/workspace/file?path=dashboard/screenshots/shot_1793036320092_8648.png"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True, f"Expected ok: True, got {data}"
        assert data.get("is_image") is True, "Expected is_image: True for PNG file"
        assert data.get("data_url", "").startswith("data:image/png;base64,"), "Expected valid base64 data URL"
        assert data.get("size", 0) > 10000, f"Expected size >10KB, got {data.get('size')}"
        print(f"      OK! Image preview returned base64 data URL ({data['size']} bytes).")

def test_workspace_file_not_found():
    print("[4/6] Testing GET /api/workspace/file for non-existent file ...")
    url = f"{BASE_URL}/api/workspace/file?path=nonexistent_test_file_123.xyz"
    try:
        urllib.request.urlopen(url, timeout=5)
        assert False, "Expected 404 HTTPError"
    except urllib.error.HTTPError as err:
        assert err.code == 404, f"Expected code 404, got {err.code}"
        body = json.loads(err.read().decode("utf-8"))
        assert body.get("ok") is False, f"Expected ok: False, got {body}"
        print(f"      OK! Received 404 as expected: {body.get('error')}")

def test_workspace_path_traversal_protection():
    print("[5/6] Testing path traversal security ...")
    # Path traversal should be rejected safely by _safe_resolve_path
    url = f"{BASE_URL}/api/workspace/file?path=../../Windows/System32/calc.exe"
    try:
        urllib.request.urlopen(url, timeout=5)
        assert False, "Expected path traversal to fail"
    except urllib.error.HTTPError as err:
        assert err.code in (404, 400), f"Expected 404/400 for path traversal, got {err.code}"
        print("      OK! Traversal outside workspace blocked safely.")

def test_dashboard_html_components():
    print("[6/6] Verifying dashboard/index.html UI components ...")
    index_path = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"
    assert index_path.exists(), f"Missing index.html at {index_path}"
    html = index_path.read_text(encoding="utf-8")

    # Check key elements and IDs
    required_ids = [
        'id="btn-files-toggle"',
        'id="files-drawer"',
        'id="files-header"',
        'id="files-tree-panel"',
        'id="files-filter-input"',
        'id="files-tree-list"',
        'id="files-viewer-panel"',
        'id="files-code-container"',
        'id="files-line-numbers"',
        'id="files-code-block"',
        'id="files-image-container"',
        'id="files-image-preview"',
        'id="btn-files-copy"',
        'id="btn-files-download"',
        'id="btn-files-expand"',
    ]
    for req_id in required_ids:
        assert req_id in html, f"Missing element with {req_id} in index.html"

    # Check key JS functions
    required_funcs = [
        "function toggleFilesDrawer",
        "function toggleFilesExpand",
        "function refreshWorkspaceTree",
        "function loadWorkspaceTree",
        "function renderTreeNodes",
        "function filterFileTree",
        "function openFileInViewer",
        "function copyCurrentCode",
        "function downloadCurrentCode",
        "hljs.highlightElement"
    ]
    for req_func in required_funcs:
        assert req_func in html, f"Missing JS function {req_func} in index.html"

    print("      OK! All HTML markup, styling classes, and JS functions verified.")

if __name__ == "__main__":
    print("\n--- Running Option 4 Verification Suite ---")
    test_workspace_tree_api()
    test_workspace_file_content_api()
    test_workspace_image_preview_api()
    test_workspace_file_not_found()
    test_workspace_path_traversal_protection()
    test_dashboard_html_components()
    print("\n[ALL TESTS PASSED] In-Dashboard Workspace File Tree & Code Viewer is 100% operational!\n")
