---
name: Post-Quantum Cryptography Audit & Migration
description: Comprehensive workflow for scanning codebases for legacy cryptographic algorithms (RSA, ECC, Diffie-Hellman) and migrating to NIST Post-Quantum standards (ML-KEM, ML-DSA / CRYSTALS-Kyber, CRYSTALS-Dilithium).
---

# Post-Quantum Cryptography (PQC) Audit & Migration Workflow

When performing a post-quantum cryptographic audit, adhere to the following phased procedure:

## 1. Discovery & Inventory
- Search for deprecated and quantum-vulnerable cryptography patterns:
  - RSA key generation: `grep_search` for `RSA`, `2048`, `4096`, `PKCS1`
  - Elliptic Curve: `grep_search` for `secp256k1`, `prime256v1`, `ECDSA`, `ECDH`
  - Classical Hashes: `grep_search` for `MD5`, `SHA1`, `DES`, `3DES`
- Execute the internal SPECTRE PQC auditor:
  ```powershell
  python scripts/pqc_audit.py --path .
  ```

## 2. Risk Scoring & Mapping
- Classify findings into NIST PQC migration tiers:
  - **Critical (Harvest Now, Decrypt Later)**: Long-lived TLS session keys, master database encryption keys, asymmetric signatures.
  - **High**: Ephemeral session negotiation using classical DH/ECDH.
  - **Medium**: Internal microservice authentication tokens using RS256.

## 3. Post-Quantum Migration Target Standards
- **Key Encapsulation Mechanism (KEM)**: Migrate to **ML-KEM** (FIPS 203 / Kyber-768 or Kyber-1024) or hybrid X25519+ML-KEM-768.
- **Digital Signatures**: Migrate to **ML-DSA** (FIPS 204 / Dilithium) or **SLH-DSA** (FIPS 205 / SPHINCS+).
- **Symmetric Keys**: Enforce AES-256-GCM or ChaCha20-Poly1305 with true entropy generated from quantum sources.

## 4. Verification & Validation
- Run `verify_build` to guarantee all cryptographic wrapper modifications compile cleanly.
- Run `handoff_to_spectre` to confirm zero hardcoded private keys or test keys remain in source files.
