"""
SPECTRE Test Suite — PQC Audit Scanner
Unit tests for ``scripts.pqc_audit.PQCAuditor.scan_file``.

TestScanFilePatterns verifies that each of the six PQC-VULN signatures
correctly fires on a true-positive snippet and stays silent on a
true-negative snippet.

Validates: Requirements 4.1
"""

import pytest
from pathlib import Path

from scripts.pqc_audit import PQCAuditor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auditor(tmp_path: Path) -> PQCAuditor:
    """Return a fresh, AI-disabled auditor rooted at *tmp_path*."""
    return PQCAuditor(target_path=str(tmp_path), ai_assist=False)


def _findings_for(auditor: PQCAuditor, file_path: Path, vuln_id: str):
    """Scan *file_path* and return only findings for the given *vuln_id*."""
    auditor.scan_file(file_path)
    return [f for f in auditor.findings if f["vuln_id"] == vuln_id]


# ---------------------------------------------------------------------------
# TestScanFilePatterns
# ---------------------------------------------------------------------------

class TestScanFilePatterns:
    """True-positive and true-negative coverage for all 6 PQC-VULN patterns."""

    # ── PQC-VULN-001 · RSA Encryption / Decryption ──────────────────────────

    def test_vuln_001_positive_rsa_import(self, tmp_py_file, tmp_path):
        """Importing RSA from PyCryptodome triggers PQC-VULN-001."""
        path = tmp_py_file("from Crypto.PublicKey import RSA\nkey = RSA.generate(2048)\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-001")
        assert findings, "Expected at least one PQC-VULN-001 finding"
        assert findings[0]["vuln_id"] == "PQC-VULN-001"
        assert findings[0]["severity"] == "CRITICAL"

    def test_vuln_001_negative_ec_import(self, tmp_py_file, tmp_path):
        """Importing the EC module (not RSA) does not trigger PQC-VULN-001."""
        path = tmp_py_file("from cryptography.hazmat.primitives.asymmetric import ec\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-001")
        assert not findings, "Expected no PQC-VULN-001 findings for EC import"

    # ── PQC-VULN-002 · Classical Diffie-Hellman / ECDH ──────────────────────

    def test_vuln_002_positive_diffie_hellman(self, tmp_py_file, tmp_path):
        """Using DiffieHellman directly triggers PQC-VULN-002."""
        path = tmp_py_file("dh = DiffieHellman()\nparams = dh.generate_parameters()\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-002")
        assert findings, "Expected at least one PQC-VULN-002 finding"
        assert findings[0]["vuln_id"] == "PQC-VULN-002"
        assert findings[0]["severity"] == "CRITICAL"

    def test_vuln_002_negative_sha256_import(self, tmp_py_file, tmp_path):
        """Importing SHA256 from hazmat hashes does not trigger PQC-VULN-002."""
        path = tmp_py_file(
            "from cryptography.hazmat.primitives.hashes import SHA256\n"
            "digest = SHA256()\n"
        )
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-002")
        assert not findings, "Expected no PQC-VULN-002 findings for SHA256 import"

    # ── PQC-VULN-003 · ECDSA / RSA Signatures ───────────────────────────────

    def test_vuln_003_positive_pkcs1_v1_5(self, tmp_py_file, tmp_path):
        """Using PKCS1_v1_5 from PyCryptodome triggers PQC-VULN-003."""
        path = tmp_py_file("from Crypto.Signature import PKCS1_v1_5\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-003")
        assert findings, "Expected at least one PQC-VULN-003 finding"
        assert findings[0]["vuln_id"] == "PQC-VULN-003"
        assert findings[0]["severity"] == "HIGH"

    def test_vuln_003_negative_padding_import(self, tmp_py_file, tmp_path):
        """Importing the generic 'padding' module does not trigger PQC-VULN-003."""
        path = tmp_py_file(
            "from cryptography.hazmat.primitives.asymmetric import padding\n"
        )
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-003")
        assert not findings, "Expected no PQC-VULN-003 findings for padding import"

    # ── PQC-VULN-004 · Ed25519 / Ed448 Classical Edwards Curves ─────────────

    def test_vuln_004_positive_ed25519_private_key(self, tmp_py_file, tmp_path):
        """Importing Ed25519PrivateKey triggers PQC-VULN-004."""
        path = tmp_py_file(
            "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey\n"
            "private_key = Ed25519PrivateKey.generate()\n"
        )
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-004")
        assert findings, "Expected at least one PQC-VULN-004 finding"
        assert findings[0]["vuln_id"] == "PQC-VULN-004"
        assert findings[0]["severity"] == "HIGH"

    def test_vuln_004_negative_ed448_private_key(self, tmp_py_file, tmp_path):
        """Importing Ed448PrivateKey (not Ed25519) does not trigger PQC-VULN-004."""
        path = tmp_py_file(
            "from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey\n"
        )
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-004")
        assert not findings, "Expected no PQC-VULN-004 findings for Ed448 import"

    # ── PQC-VULN-005 · Short Symmetric Key / AES-128 ────────────────────────

    def test_vuln_005_positive_aes128_gcm_constant(self, tmp_py_file, tmp_path):
        """Using the AES128_GCM constant triggers PQC-VULN-005."""
        path = tmp_py_file("cipher = AES128_GCM(key)\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-005")
        assert findings, "Expected at least one PQC-VULN-005 finding"
        assert findings[0]["vuln_id"] == "PQC-VULN-005"
        assert findings[0]["severity"] == "MEDIUM"

    def test_vuln_005_negative_aes_gcm_no_key_size(self, tmp_py_file, tmp_path):
        """AES.new() in GCM mode without a key_size=128 reference does not trigger PQC-VULN-005."""
        path = tmp_py_file("cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-005")
        assert not findings, "Expected no PQC-VULN-005 findings for AES-GCM without 128-bit indicator"

    # ── PQC-VULN-006 · Legacy Hashes (MD5, SHA-1, DES, RC4) ─────────────────

    def test_vuln_006_positive_hashlib_md5(self, tmp_py_file, tmp_path):
        """Using hashlib.md5 triggers PQC-VULN-006."""
        path = tmp_py_file("import hashlib\nh = hashlib.md5(data)\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-006")
        assert findings, "Expected at least one PQC-VULN-006 finding"
        assert findings[0]["vuln_id"] == "PQC-VULN-006"
        assert findings[0]["severity"] == "HIGH"

    def test_vuln_006_negative_hashlib_sha3_256(self, tmp_py_file, tmp_path):
        """Using hashlib.sha3_256 (quantum-safe hash) does not trigger PQC-VULN-006."""
        path = tmp_py_file("import hashlib\nh = hashlib.sha3_256(data)\n")
        auditor = _auditor(tmp_path)
        findings = _findings_for(auditor, path, "PQC-VULN-006")
        assert not findings, "Expected no PQC-VULN-006 findings for sha3_256"
