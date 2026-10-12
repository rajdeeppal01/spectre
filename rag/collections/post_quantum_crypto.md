# NIST Post-Quantum Cryptography (PQC) Specification & Migration Guide

## 1. Executive Summary & Standards Landscape (2024–2026)
In August 2024, the U.S. National Institute of Standards and Technology (NIST) officially released the world's first finalized post-quantum cryptography standards. These standards are designed to secure modern computing infrastructure against attacks by Cryptanalytically Relevant Quantum Computers (CRQCs).

| Standard | Algorithm Name | Former Name | Category | Primary Purpose |
|---|---|---|---|---|
| **FIPS 203** | **ML-KEM** | CRYSTALS-Kyber | Key Encapsulation (KEM) | General public-key encryption & TLS key exchange |
| **FIPS 204** | **ML-DSA** | CRYSTALS-Dilithium | Digital Signature Algorithm | General identity, code signing & document authentication |
| **FIPS 205** | **SLH-DSA** | SPHINCS+ | Stateless Hash-Based Signature | Backup signature scheme (no lattice assumptions) |
| *Draft FIPS 206* | *FN-DSA* | FALCON | Lattice-Based Fast Signature | Compact signature sizes (constrained environments) |

---

## 2. Threat Analysis: Shor's Algorithm vs. Grover's Algorithm

### A. Shor's Algorithm (Polynomial Time Collapse)
- **Target:** Integer factorization (RSA) and discrete logarithms (Diffie-Hellman, ECDH, DSA, ECDSA, Ed25519).
- **Quantum Complexity:** $\mathcal{O}((\log N)^3)$ operations using the Quantum Fourier Transform (QFT).
- **Implication:** Every classical asymmetric algorithm currently used for TLS, SSH, VPNs, and cryptocurrencies will be broken once a CRQC with ~4,000 logical qubits is built.
- **Harvest Now, Decrypt Later (HNDL):** Adversarial state actors intercept and store encrypted internet traffic today. When CRQCs become functional, this recorded data will be decrypted retroactively. **PQC key exchange must be deployed immediately to defeat HNDL.**

### B. Grover's Algorithm (Quadratic Speedup)
- **Target:** Symmetric encryption (AES) and cryptographic hash preimages (SHA-256, SHA-3).
- **Quantum Complexity:** $\mathcal{O}(\sqrt{N})$ iterations vs classical $\mathcal{O}(N)$ brute-force.
- **Implication:** Effective security is halved.
  - **AES-128:** Reduced to $2^{64}$ operations — considered borderline insecure against large-scale quantum computers.
  - **AES-256:** Reduced to $2^{128}$ operations — **completely quantum-safe**.
  - **SHA-256 / SHA-384 / SHA-512:** Maintain at least 128 bits of quantum collision and preimage resistance.

---

## 3. NIST FIPS 203: ML-KEM Parameter Sets

ML-KEM is based on the **Module Learning With Errors (M-LWE)** lattice problem. Security levels are categorized by NIST equivalence to AES brute-force:

| Parameter Set | Module Rank ($k$) | Public Key (bytes) | Ciphertext (bytes) | NIST Security Level | Classical Equivalent |
|---|---|---|---|---|---|
| **ML-KEM-512** | 2 | 800 | 768 | Level 1 | AES-128 |
| **ML-KEM-768** | 3 | 1,184 | 1,088 | Level 3 (**Recommended Default**) | AES-192 |
| **ML-KEM-1024** | 4 | 1,568 | 1,568 | Level 5 | AES-256 |

### Hybrid TLS 1.3 Deployment (`X25519MLKEM768`)
During the transition phase, standards mandate combining classical X25519 with ML-KEM-768 in a single Key Encapsulation. If either algorithm remains secure, the entire session remains secure against both classical and quantum adversaries.
- Supported natively in **Chromium browsers (v124+)**, **Cloudflare**, and **OpenSSL 3.2+**.

---

## 4. NIST FIPS 204: ML-DSA Parameter Sets

ML-DSA is based on the **Module Short Integer Solution (M-SIS)** lattice problem using the Fiat-Shamir with Aborts framework.

| Parameter Set | Matrix Dim ($k \times l$) | Public Key (bytes) | Signature (bytes) | NIST Security Level |
|---|---|---|---|---|
| **ML-DSA-44** | $4 \times 4$ | 1,312 | 2,420 | Level 2 |
| **ML-DSA-65** | $6 \times 5$ | 1,952 | 3,309 | Level 3 (**Recommended Default**) |
| **ML-DSA-87** | $8 \times 7$ | 2,592 | 4,627 | Level 5 |

---

## 5. Implementation Guide & Code Patterns

### Python Integration via `liboqs-python`
```python
import oqs

# 1. Key Encapsulation (ML-KEM-768)
kem_name = "ML-KEM-768"
with oqs.KeyEncapsulation(kem_name) as client:
    public_key = client.generate_keypair()
    
    # Server side: encapsulate shared secret
    with oqs.KeyEncapsulation(kem_name) as server:
        ciphertext, shared_secret_server = server.encap_secret(public_key)
        
    # Client side: decapsulate shared secret
    shared_secret_client = client.decap_secret(ciphertext)
    assert shared_secret_client == shared_secret_server
    print(f"[+] Established PQC Shared Secret: {shared_secret_client.hex()[:32]}...")
```

### Go 1.24+ Native TLS Hybrid Configuration
```go
package main

import (
    "crypto/tls"
    "net/http"
)

func main() {
    config := &tls.Config{
        MinVersion: tls.VersionTLS13,
        CurvePreferences: []tls.CurveID{
            tls.X25519MLKEM768, // Hybrid Post-Quantum Key Exchange
            tls.X25519,
        },
    }
    server := &http.Server{
        Addr:      ":8443",
        TLSConfig: config,
    }
    server.ListenAndServeTLS("cert.pem", "key.pem")
}
```

---

## 6. SPECTRE Audit Checklist for Legacy Codebases
1. **Flag all RSA key generations** (`rsa.generate`, `Crypto.PublicKey.RSA`, `crypto/rsa`).
2. **Flag classical Diffie-Hellman / ECDH** without hybrid wrappers.
3. **Audit TLS ciphers** for classical-only suites (`ECDHE-RSA-AES128-GCM-SHA256`).
4. **Upgrade symmetric keys** from 128-bit to 256-bit AES-GCM.
5. **Verify non-lattice hash-based signatures** (SLH-DSA) are planned as fallback for high-value root certificates.
