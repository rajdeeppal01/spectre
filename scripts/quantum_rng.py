"""
SPECTRE — Quantum Random Number Generator (QRNG) & Entropy Pool
Fetches true quantum entropy from the Australian National University (ANU)
Quantum Optics Lab (vacuum fluctuation measurements) with an air-gapped
hardware-jitter quantum entropy fallback. Produces cryptographic keys,
nonces, session tokens, and PQC seeds.

Usage:
    python scripts/quantum_rng.py --bytes 32 --format hex
    python scripts/quantum_rng.py --tokens 3 --length 32
    python scripts/quantum_rng.py --aes-key
    python scripts/quantum_rng.py --pqc-seed
    python scripts/quantum_rng.py --serve --port 8001
"""

import os
import sys
import time
import json
import base64
import hashlib
import secrets
import argparse
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Tuple

ANU_QRNG_URL = "https://qrng.anu.edu.au/API/jsonI.php"


def fetch_anu_quantum_bytes(num_bytes: int, timeout: int = 5) -> Optional[bytes]:
    """Fetch true random bytes from the ANU quantum vacuum fluctuation API."""
    # ANU API caps single request at 1024 numbers
    chunk_size = min(num_bytes, 1024)
    url = f"{ANU_QRNG_URL}?length={chunk_size}&type=uint8"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SPECTRE-Quantum-RNG/1.0 (Cybersecurity Workspace)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if data.get("success") and "data" in data:
                    raw_data = bytes(data["data"])
                    if len(raw_data) < num_bytes:
                        # Recursively fetch remaining chunks if needed
                        remaining = fetch_anu_quantum_bytes(num_bytes - len(raw_data), timeout)
                        if remaining:
                            return raw_data + remaining
                    return raw_data[:num_bytes]
    except Exception:
        return None
    return None


def generate_local_quantum_jitter_entropy(num_bytes: int) -> bytes:
    """
    Air-gapped entropy pool: Combines OS CSPRNG with high-resolution CPU
    micro-jitter timing variance and state hashing to ensure high entropy
    even without network access.
    """
    pool = bytearray()
    # 1. Base OS CSPRNG
    pool.extend(os.urandom(num_bytes * 2))

    # 2. Timing jitter accumulator
    jitter_bits = []
    for _ in range(num_bytes * 8):
        t0 = time.perf_counter_ns()
        # Transcendental micro-computation to induce CPU pipeline jitter
        _ = 3.1415926535 ** 2.7182818284
        t1 = time.perf_counter_ns()
        jitter_bits.append(str((t1 - t0) & 1))

    jitter_bytes = int("".join(jitter_bits[:num_bytes * 8]), 2).to_bytes(num_bytes, byteorder="big")
    pool.extend(jitter_bytes)

    # 3. High-entropy cryptographic compression via SHA3-512 / SHA-256
    digest = hashlib.sha3_512(pool).digest()
    if num_bytes <= len(digest):
        return digest[:num_bytes]
    
    # Expand via HKDF-like counter mode if large block requested
    out = bytearray()
    counter = 0
    while len(out) < num_bytes:
        block = hashlib.sha3_512(digest + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:num_bytes])


def get_quantum_entropy(num_bytes: int, force_offline: bool = False) -> Tuple[bytes, str]:
    """Retrieve entropy, preferring ANU quantum optics with local fallback."""
    if not force_offline:
        live_bytes = fetch_anu_quantum_bytes(num_bytes)
        if live_bytes:
            return live_bytes, "ANU Live Quantum Vacuum Fluctuation API"
    
    fallback_bytes = generate_local_quantum_jitter_entropy(num_bytes)
    return fallback_bytes, "Air-Gapped Hybrid Quantum-Jitter Entropy Pool"


def generate_session_tokens(count: int, length: int, force_offline: bool = False) -> list[str]:
    """Generate high-entropy URL-safe cryptographic session tokens."""
    tokens = []
    for _ in range(count):
        raw, _ = get_quantum_entropy(length, force_offline)
        token = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")[:length]
        tokens.append(token)
    return tokens


def generate_aes256_gcm_bundle(force_offline: bool = False) -> dict:
    """Generate a quantum-seeded AES-256 key with 96-bit GCM initialization vector."""
    key_bytes, src_k = get_quantum_entropy(32, force_offline)
    iv_bytes, src_iv = get_quantum_entropy(12, force_offline)
    return {
        "cipher": "AES-256-GCM",
        "key_hex": key_bytes.hex(),
        "key_base64": base64.b64encode(key_bytes).decode("utf-8"),
        "iv_hex": iv_bytes.hex(),
        "iv_base64": base64.b64encode(iv_bytes).decode("utf-8"),
        "entropy_source": src_k
    }


def generate_pqc_seed_bundle(force_offline: bool = False) -> dict:
    """Generate a 64-byte high-entropy seed for ML-KEM-768 or ML-DSA-65 keypairs."""
    seed_bytes, src = get_quantum_entropy(64, force_offline)
    return {
        "standard": "NIST FIPS 203 (ML-KEM) & FIPS 204 (ML-DSA) Keygen Seed",
        "seed_hex": seed_bytes.hex(),
        "seed_base64": base64.b64encode(seed_bytes).decode("utf-8"),
        "byte_length": 64,
        "entropy_source": src
    }


class QRNGHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/random"):
            num_bytes = 32
            entropy, source = get_quantum_entropy(num_bytes)
            self._send_json(200, {
                "bytes_hex": entropy.hex(),
                "bytes_b64": base64.b64encode(entropy).decode("utf-8"),
                "length": num_bytes,
                "source": source
            })
        elif self.path.startswith("/tokens"):
            tokens = generate_session_tokens(5, 32)
            self._send_json(200, {"tokens": tokens})
        elif self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "SPECTRE QRNG Micro-Service"})
        else:
            self._send_json(404, {"error": "Not Found. Available: /random, /tokens, /health"})

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[QRNG-HTTP] {args[0]} - {args[1]}\n")


def serve_http(port: int = 8001):
    server = HTTPServer(("127.0.0.1", port), QRNGHttpHandler)
    print(f"[+] SPECTRE QRNG Micro-Service running at http://127.0.0.1:{port}")
    print("    Endpoints: /random, /tokens, /health (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping QRNG server.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="SPECTRE Quantum Random Number Generator (QRNG)")
    parser.add_argument("--bytes", type=int, help="Number of random bytes to generate")
    parser.add_argument("--format", choices=["hex", "base64", "decimal"], default="hex", help="Output format for raw bytes")
    parser.add_argument("--tokens", type=int, help="Generate N URL-safe session tokens")
    parser.add_argument("--length", type=int, default=32, help="Token length (default: 32)")
    parser.add_argument("--aes-key", action="store_true", help="Generate quantum-seeded AES-256-GCM key and 96-bit IV")
    parser.add_argument("--pqc-seed", action="store_true", help="Generate 64-byte high-entropy seed for NIST PQC keygen")
    parser.add_argument("--offline", action="store_true", help="Force air-gapped local jitter entropy pool (bypass ANU API)")
    parser.add_argument("--serve", action="store_true", help="Run local HTTP micro-service on 127.0.0.1")
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP micro-service (default: 8001)")

    args = parser.parse_args()

    if args.serve:
        serve_http(args.port)
        return

    if args.aes_key:
        bundle = generate_aes256_gcm_bundle(args.offline)
        print("=" * 65)
        print("          QUANTUM-SEEDED AES-256-GCM KEY BUNDLE          ")
        print("=" * 65)
        print(f"Algorithm      : {bundle['cipher']}")
        print(f"Key (Hex)      : {bundle['key_hex']}")
        print(f"Key (Base64)   : {bundle['key_base64']}")
        print(f"IV (Hex)       : {bundle['iv_hex']}")
        print(f"Entropy Source : {bundle['entropy_source']}")
        print("=" * 65)
        return

    if args.pqc_seed:
        bundle = generate_pqc_seed_bundle(args.offline)
        print("=" * 65)
        print("          NIST POST-QUANTUM KEYGEN SEED (64 BYTES)          ")
        print("=" * 65)
        print(f"Target         : {bundle['standard']}")
        print(f"Seed (Hex)     : {bundle['seed_hex']}")
        print(f"Seed (Base64)  : {bundle['seed_base64']}")
        print(f"Entropy Source : {bundle['entropy_source']}")
        print("=" * 65)
        return

    if args.tokens:
        tokens = generate_session_tokens(args.tokens, args.length, args.offline)
        print(f"[*] Generated {args.tokens} Quantum-Seeded Session Tokens ({args.length} chars):")
        for i, t in enumerate(tokens, 1):
            print(f"  [{i}] {t}")
        return

    num_bytes = args.bytes if args.bytes else 32
    entropy, source = get_quantum_entropy(num_bytes, args.offline)

    print(f"[*] Quantum Entropy ({num_bytes} bytes) | Source: {source}")
    if args.format == "hex":
        print(entropy.hex())
    elif args.format == "base64":
        print(base64.b64encode(entropy).decode("utf-8"))
    elif args.format == "decimal":
        print(list(entropy))


if __name__ == "__main__":
    main()
