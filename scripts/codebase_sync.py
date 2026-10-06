"""
SPECTRE — Codebase RAG Sync
Watches your project directories and automatically re-indexes changed
source files into Open WebUI's RAG knowledge base.

Run once at startup:
    python scripts/codebase_sync.py --watch /path/to/your/project

Or one-shot index an entire directory:
    python scripts/codebase_sync.py --index /path/to/your/project
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# ── Configuration ─────────────────────────────────────────────
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://localhost:3000")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "")  # Set after first login
COLLECTION_NAME = "My Codebases"

# File extensions to index
WATCHED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".rs", ".java", ".cpp", ".c", ".h",
    ".html", ".css", ".scss",
    ".sql", ".graphql",
    ".yaml", ".yml", ".json", ".toml",
    ".md", ".txt"
}

# Directories to ignore
IGNORED_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", ".nuxt",
    "dist", "build", ".venv", "venv", "env", ".mypy_cache",
    "coverage", ".pytest_cache", "target"
}

# Track indexed file hashes to avoid re-indexing unchanged files
_indexed_hashes: dict[str, str] = {}


def get_file_hash(path: Path) -> str:
    """SHA256 hash of file contents — used to detect real changes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_index(path: Path) -> bool:
    """Return True if this file should be indexed into RAG."""
    if path.suffix not in WATCHED_EXTENSIONS:
        return False
    for ignored in IGNORED_DIRS:
        if ignored in path.parts:
            return False
    if path.stat().st_size > 500_000:  # Skip files > 500KB
        return False
    return True


def index_file(path: Path) -> bool:
    """
    Upload a single file to Open WebUI's RAG knowledge base.
    Returns True on success.
    """
    if not OPENWEBUI_API_KEY:
        print(f"  [!] OPENWEBUI_API_KEY not set — skipping RAG sync for {path.name}")
        print("      Get your key from Open WebUI → Settings → Account → API Key")
        return False

    file_hash = get_file_hash(path)

    # Skip if file hasn't changed since last index
    if _indexed_hashes.get(str(path)) == file_hash:
        return True

    try:
        with open(path, "rb") as f:
            response = requests.post(
                f"{OPENWEBUI_URL}/api/v1/memories/",
                headers={"Authorization": f"Bearer {OPENWEBUI_API_KEY}"},
                files={"file": (path.name, f, "text/plain")},
                data={"collection_name": COLLECTION_NAME},
                timeout=30,
            )

        if response.status_code in (200, 201):
            _indexed_hashes[str(path)] = file_hash
            print(f"  ✓ Indexed: {path.name}")
            return True
        else:
            print(f"  ✗ Failed to index {path.name}: {response.status_code} {response.text[:100]}")
            return False

    except requests.RequestException as e:
        print(f"  ✗ Connection error indexing {path.name}: {e}")
        return False


def index_directory(root: Path) -> int:
    """Recursively index all qualifying files under root. Returns count indexed."""
    count = 0
    for path in root.rglob("*"):
        if path.is_file() and should_index(path):
            if index_file(path):
                count += 1
    return count


class CodebaseHandler(FileSystemEventHandler):
    """Watchdog handler — re-indexes files on save."""

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if should_index(path):
            print(f"\n[~] File changed: {path.name}")
            index_file(path)

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if should_index(path):
            print(f"\n[+] New file: {path.name}")
            index_file(path)


def main():
    parser = argparse.ArgumentParser(
        description="SPECTRE Codebase RAG Sync — keeps your AI knowledge base current"
    )
    parser.add_argument("--watch", metavar="DIR", help="Watch a directory for changes (runs continuously)")
    parser.add_argument("--index", metavar="DIR", help="One-shot index an entire directory and exit")
    parser.add_argument("--api-key", help="Open WebUI API key (or set OPENWEBUI_API_KEY env var)")
    args = parser.parse_args()

    global OPENWEBUI_API_KEY
    if args.api_key:
        OPENWEBUI_API_KEY = args.api_key

    if args.index:
        root = Path(args.index).resolve()
        print(f"\n[SPECTRE RAG] Indexing {root} into '{COLLECTION_NAME}'...")
        count = index_directory(root)
        print(f"\n✓ Done — {count} files indexed into '{COLLECTION_NAME}'")
        return

    if args.watch:
        root = Path(args.watch).resolve()
        print(f"\n[SPECTRE RAG] Initial index of {root}...")
        count = index_directory(root)
        print(f"✓ Initial index complete — {count} files")
        print(f"\n[SPECTRE RAG] Watching {root} for changes (Ctrl+C to stop)...\n")

        event_handler = CodebaseHandler()
        observer = Observer()
        observer.schedule(event_handler, str(root), recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
