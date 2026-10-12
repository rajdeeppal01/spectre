"""
SPECTRE — Universal RAG Ingestion & Vector Retrieval Engine
Parses curated knowledge documents, computes dense embeddings using
Ollama's local `nomic-embed-text` model, and provides high-speed offline
semantic similarity search across cybersecurity, web dev, and quantum collections.

Usage:
    python scripts/init_rag.py --build
    python scripts/init_rag.py --query "How does ML-KEM protect against Shor's algorithm?"
    python scripts/init_rag.py --query "How to exploit vsftpd 2.3.4?" --top-k 3
    python scripts/init_rag.py --sync-openwebui --url http://localhost:3000
"""

import os
import re
import sys
import math
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import urllib.request
import urllib.error

COLLECTIONS_DIR = Path(__file__).resolve().parent.parent / "rag" / "collections"
VECTOR_INDEX_PATH = Path(__file__).resolve().parent.parent / "rag" / "vector_store.json"
OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")


def chunk_markdown(file_path: Path, max_chars: int = 1200, overlap: int = 200) -> List[Dict[str, Any]]:
    """Chunks a markdown file respecting section headers and paragraph boundaries."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    collection_name = file_path.stem

    sections = re.split(r'\n(?=#{1,3}\s+)', text)
    chunks = []
    chunk_idx = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Extract title from the first heading if available
        header_match = re.match(r'^#{1,3}\s+(.+)', section)
        header_title = header_match.group(1).strip() if header_match else "General"

        if len(section) <= max_chars:
            chunks.append({
                "id": f"{collection_name}_{chunk_idx}",
                "collection": collection_name,
                "file": file_path.name,
                "header": header_title,
                "text": section
            })
            chunk_idx += 1
        else:
            # Sub-split long sections by paragraphs
            paragraphs = section.split("\n\n")
            curr_chunk = ""
            for p in paragraphs:
                if len(curr_chunk) + len(p) + 2 <= max_chars:
                    curr_chunk += ("\n\n" if curr_chunk else "") + p
                else:
                    if curr_chunk:
                        chunks.append({
                            "id": f"{collection_name}_{chunk_idx}",
                            "collection": collection_name,
                            "file": file_path.name,
                            "header": header_title,
                            "text": curr_chunk
                        })
                        chunk_idx += 1
                    curr_chunk = p
            if curr_chunk:
                chunks.append({
                    "id": f"{collection_name}_{chunk_idx}",
                    "collection": collection_name,
                    "file": file_path.name,
                    "header": header_title,
                    "text": curr_chunk
                })
                chunk_idx += 1

    return chunks


def get_ollama_embedding(text: str) -> Optional[List[float]]:
    """Fetch 768-dim vector embedding from local Ollama instance."""
    payload = {
        "model": EMBEDDING_MODEL,
        "prompt": text
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_API_BASE}/api/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding")
    except Exception:
        return None


STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
    "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these",
    "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves"
}


def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into clean tokens."""
    # Split by whitespace, punctuation, hyphens
    tokens = re.findall(r'[a-zA-Z0-9_\-]+', text.lower())
    result = []
    for t in tokens:
        clean = t.strip("-_")
        if len(clean) >= 2 and clean not in STOPWORDS:
            result.append(clean)
            # Also add unhyphenated subparts (e.g. "ml", "kem" for "ml-kem")
            if "-" in clean:
                for sub in clean.split("-"):
                    if len(sub) >= 2 and sub not in STOPWORDS:
                        result.append(sub)
    return result


def compute_bm25_features(text: str) -> Dict[str, float]:
    """Lightweight local bag-of-words vectorizer used for fallback ranking."""
    tokens = tokenize(text)
    counts: Dict[str, int] = {}
    for w in tokens:
        counts[w] = counts.get(w, 0) + 1
    total = len(tokens) or 1
    return {w: c / total for w, c in counts.items()}


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute standard cosine similarity between two dense vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def build_vector_store():
    """Scans collections directory, generates embeddings, and saves vector index."""
    if not COLLECTIONS_DIR.exists():
        print(f"[!] Collections directory not found: {COLLECTIONS_DIR}")
        return

    md_files = list(COLLECTIONS_DIR.glob("*.md"))
    print(f"[*] Found {len(md_files)} knowledge collection files in {COLLECTIONS_DIR}")
    
    all_chunks = []
    for f in md_files:
        chunks = chunk_markdown(f)
        all_chunks.extend(chunks)
        print(f"    - Parsed {f.name}: {len(chunks)} chunks")

    print(f"\n[*] Generating embeddings for {len(all_chunks)} chunks via Ollama ({EMBEDDING_MODEL})...")
    ollama_online = False
    
    # Test Ollama connection
    test_vec = get_ollama_embedding("test probe")
    if test_vec:
        ollama_online = True
        print("[+] Connected to local Ollama embedding engine.")
    else:
        print("[!] Ollama embedding endpoint offline or model not loaded. Using local BM25 fallback engine.")

    for i, chunk in enumerate(all_chunks, 1):
        if ollama_online:
            vec = get_ollama_embedding(chunk["text"])
            chunk["embedding"] = vec
        else:
            chunk["embedding"] = None
        
        # Always store BM25 lexical signature for hybrid search
        chunk["bow"] = compute_bm25_features(chunk["text"])
        
        if i % 10 == 0 or i == len(all_chunks):
            print(f"    Indexed {i}/{len(all_chunks)} chunks...")

    # Save index to disk
    VECTOR_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VECTOR_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\n[+] Vector store built successfully! Saved {len(all_chunks)} records to {VECTOR_INDEX_PATH}")


def search_vector_store(query: str, top_k: int = 3, collection_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Performs semantic similarity search over stored vectors."""
    if not VECTOR_INDEX_PATH.exists():
        print("[!] Vector index not found. Building index first...")
        build_vector_store()

    try:
        with open(VECTOR_INDEX_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        print(f"[!] Error reading vector store: {e}")
        return []

    if collection_filter:
        records = [r for r in records if r.get("collection") == collection_filter]

    query_vec = get_ollama_embedding(query)
    query_bow = compute_bm25_features(query)

    scored = []
    for r in records:
        score = 0.0
        # If dense embedding is available, use cosine similarity
        if query_vec and r.get("embedding"):
            score = cosine_similarity(query_vec, r["embedding"])
        else:
            # BM25 dot-product overlap score
            r_bow = r.get("bow", {})
            header_tokens = tokenize(r.get("header", ""))
            collection_tokens = tokenize(r.get("collection", ""))
            for w, weight in query_bow.items():
                if w in r_bow:
                    score += weight * r_bow[w] * 10.0
                if w in header_tokens:
                    score += 0.25  # Substantial boost for matching header
                if w in collection_tokens:
                    score += 0.20  # Boost for matching collection topic

        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": s, "record": r} for s, r in scored[:top_k]]


def sync_to_openwebui(openwebui_url: str, api_key: Optional[str] = None):
    """Syncs markdown knowledge collections directly into Open WebUI knowledge collections."""
    print(f"[*] Synchronizing RAG collections to Open WebUI at {openwebui_url}...")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    md_files = list(COLLECTIONS_DIR.glob("*.md"))
    for f in md_files:
        name = f.stem.replace("_", " ").title()
        content = f.read_text(encoding="utf-8")
        payload = {
            "name": name,
            "description": f"SPECTRE knowledge collection: {f.name}",
            "data": {"content": content}
        }
        try:
            req = urllib.request.Request(
                f"{openwebui_url}/api/v1/knowledge/create",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"[+] Synced collection '{name}' to Open WebUI.")
        except Exception as e:
            print(f"[-] Could not auto-sync '{name}' directly via API: {e} (Import file manually via Open WebUI UI)")


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Universal RAG Ingestion & Search Engine")
    parser.add_argument("--build", action="store_true", help="Build/rebuild the vector store from markdown collections")
    parser.add_argument("--query", help="Semantic query to search across all RAG collections")
    parser.add_argument("--collection", help="Filter search to a specific collection (e.g. post_quantum_crypto, security_standards)")
    parser.add_argument("--top-k", type=int, default=3, help="Number of search results to return (default: 3)")
    parser.add_argument("--sync-openwebui", action="store_true", help="Sync collections to Open WebUI instance")
    parser.add_argument("--url", default="http://localhost:3000", help="Open WebUI URL (default: http://localhost:3000)")

    args = parser.parse_args()

    if args.build or not VECTOR_INDEX_PATH.exists():
        build_vector_store()
        if not args.query and not args.sync_openwebui:
            return

    if args.sync_openwebui:
        api_key = os.environ.get("OPENWEBUI_API_KEY")
        sync_to_openwebui(args.url, api_key)
        return

    if args.query:
        print(f"\n[*] Executing semantic search for query: '{args.query}'")
        results = search_vector_store(args.query, top_k=args.top_k, collection_filter=args.collection)
        print("=" * 75)
        for i, res in enumerate(results, 1):
            r = res["record"]
            score = res["score"]
            print(f"[{i}] Relevance Score: {score:.4f} | Collection: [{r['collection']}] | Section: {r['header']}")
            print(f"    File: {r['file']}")
            print("-" * 75)
            # Print snippet
            lines = r["text"].splitlines()
            snippet = "\n    ".join(lines[:6])
            print(f"    {snippet}...")
            print("=" * 75)


if __name__ == "__main__":
    main()
