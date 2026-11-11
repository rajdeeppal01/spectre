"""
tests/scripts/test_continuous_security.py
Unit tests for scripts.continuous_security — SEC rule true-positive and
true-negative checks via scan_file_content.

Validates: Requirements 3.1
"""

import sys
from pathlib import Path
from typing import Callable

# Ensure the workspace root is on sys.path so `scripts.continuous_security` is importable.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from scripts.continuous_security import SECURITY_RULES, scan_file_content


# ── Helpers ───────────────────────────────────────────────────────────────────

def rule_ids_in_findings(findings: list) -> set:
    """Return the set of rule_ids present in a findings list."""
    return {f["rule_id"] for f in findings}


# ── Task 4.1 — TestScanFileContentRules ──────────────────────────────────────


class TestScanFileContentRules:
    """
    True-positive and true-negative tests for every SEC rule.

    For each SEC-001 through SEC-008 there is one test that confirms a
    matching snippet produces at least one finding whose rule_id equals the
    rule under test, and one test that confirms a benign snippet produces no
    finding for that rule_id.

    The ``tmp_py_file`` fixture writes the snippet to a real temporary file so
    that ``scan_file_content`` exercises its full filesystem + regex path.

    Validates: Requirements 3.1
    """

    # ── SEC-001 : Hardcoded Secret / API Key ──────────────────────────────────

    def test_sec001_positive_named_key_with_long_value(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        A named credential (api_key) assigned a value of 16+ alphanumeric
        characters must trigger SEC-001.

        The regex arm that fires here::

            (?:api[_-]?key|...)\\s*[:=]\\s*['"][A-Za-z0-9_\\-\\.]{16,}['"]
        """
        path = tmp_py_file('api_key = "EXAMPLE_sk_live_XXXXXXXXXXXXXXXXXXXX"')
        findings = scan_file_content(path)
        assert "SEC-001" in rule_ids_in_findings(findings), (
            "Expected SEC-001 finding for hardcoded api_key with long value"
        )

    def test_sec001_negative_short_value(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        A credential key whose value is fewer than 16 characters must NOT
        trigger SEC-001.
        """
        path = tmp_py_file('api_key = "short"')
        findings = scan_file_content(path)
        assert "SEC-001" not in rule_ids_in_findings(findings), (
            "SEC-001 must not fire for short credential value"
        )

    # ── SEC-002 : SQL Injection (Unsanitized Concatenation) ───────────────────

    def test_sec002_positive_string_concatenation_in_execute(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``cursor.execute("SELECT … " + variable)`` must trigger SEC-002.

        The regex arm that fires here::

            cursor\\.execute\\s*\\(\\s*".*SELECT.*"\\s*\\+\\s*
        """
        path = tmp_py_file(
            'result = cursor.execute("SELECT * FROM users WHERE id=" + user_id)'
        )
        findings = scan_file_content(path)
        assert "SEC-002" in rule_ids_in_findings(findings), (
            "Expected SEC-002 finding for SQL string concatenation"
        )

    def test_sec002_negative_parameterized_query(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        A parameterized query using bound parameters must NOT trigger SEC-002.
        """
        path = tmp_py_file(
            'result = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))'
        )
        findings = scan_file_content(path)
        assert "SEC-002" not in rule_ids_in_findings(findings), (
            "SEC-002 must not fire for a parameterized query"
        )

    # ── SEC-003 : Command Injection (Shell Execution) ─────────────────────────

    def test_sec003_positive_os_system_call(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``os.system(…)`` must trigger SEC-003 regardless of the argument.

        The regex arm that fires here: ``os\\.system\\s*(``
        """
        path = tmp_py_file("os.system(user_input)")
        findings = scan_file_content(path)
        assert "SEC-003" in rule_ids_in_findings(findings), (
            "Expected SEC-003 finding for os.system call"
        )

    def test_sec003_negative_subprocess_run_without_shell(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``subprocess.run([…], shell=False)`` must NOT trigger SEC-003.
        The rule only fires when ``shell=True`` is present.
        """
        path = tmp_py_file('subprocess.run(["ls", "-la"], shell=False)')
        findings = scan_file_content(path)
        assert "SEC-003" not in rule_ids_in_findings(findings), (
            "SEC-003 must not fire for subprocess.run with shell=False"
        )

    # ── SEC-004 : Cross-Site Scripting (XSS / Raw HTML) ───────────────────────

    def test_sec004_positive_innerhtml_assignment(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``element.innerHTML = …`` must trigger SEC-004.

        The regex arm that fires here: ``innerHTML\\s*=``
        """
        path = tmp_py_file("element.innerHTML = user_data", suffix=".js")
        findings = scan_file_content(path)
        assert "SEC-004" in rule_ids_in_findings(findings), (
            "Expected SEC-004 finding for innerHTML assignment"
        )

    def test_sec004_negative_textcontent_assignment(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``element.textContent = …`` is safe and must NOT trigger SEC-004.
        """
        path = tmp_py_file("element.textContent = user_data", suffix=".js")
        findings = scan_file_content(path)
        assert "SEC-004" not in rule_ids_in_findings(findings), (
            "SEC-004 must not fire for textContent assignment"
        )

    # ── SEC-005 : Path Traversal (Unvalidated File Open) ─────────────────────

    def test_sec005_positive_open_with_request_args(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``open(f"/data/{request.args['file']}")`` must trigger SEC-005 because
        it opens a file constructed from unvalidated user-supplied input.

        The regex arm that fires here::

            open\\s*\\(\\s*f['"].*\\{
        """
        path = tmp_py_file("open(f\"/data/{request.args['file']}\")")
        findings = scan_file_content(path)
        assert "SEC-005" in rule_ids_in_findings(findings), (
            "Expected SEC-005 finding for open() with unvalidated request.args"
        )

    def test_sec005_negative_open_with_static_path(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``open("/data/static_file.txt")`` uses a hard-coded path and must NOT
        trigger SEC-005.
        """
        path = tmp_py_file('open("/data/static_file.txt")')
        findings = scan_file_content(path)
        assert "SEC-005" not in rule_ids_in_findings(findings), (
            "SEC-005 must not fire for open() with a static path"
        )

    # ── SEC-006 : Insecure / Quantum-Vulnerable Cryptography ─────────────────

    def test_sec006_positive_hashlib_md5(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``hashlib.md5(…)`` must trigger SEC-006.

        The regex arm that fires here: ``hashlib\\.md5\\b``
        """
        path = tmp_py_file("hashlib.md5(data)")
        findings = scan_file_content(path)
        assert "SEC-006" in rule_ids_in_findings(findings), (
            "Expected SEC-006 finding for hashlib.md5 usage"
        )

    def test_sec006_negative_hashlib_sha256(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``hashlib.sha256(…)`` is a secure modern hash and must NOT trigger
        SEC-006.
        """
        path = tmp_py_file("hashlib.sha256(data)")
        findings = scan_file_content(path)
        assert "SEC-006" not in rule_ids_in_findings(findings), (
            "SEC-006 must not fire for hashlib.sha256"
        )

    # ── SEC-007 : Server-Side Request Forgery (SSRF) ─────────────────────────

    def test_sec007_positive_requests_get_with_user_url(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``requests.get(request.args['url'])`` must trigger SEC-007 because the
        URL originates from untrusted user input.

        The regex arm that fires here::

            requests\\.get\\s*\\(\\s*request\\.
        """
        path = tmp_py_file("requests.get(request.args['url'])")
        findings = scan_file_content(path)
        assert "SEC-007" in rule_ids_in_findings(findings), (
            "Expected SEC-007 finding for requests.get with user-supplied URL"
        )

    def test_sec007_negative_requests_get_with_hardcoded_url(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``requests.get("https://api.example.com/…")`` uses a hard-coded
        URL and must NOT trigger SEC-007.
        """
        path = tmp_py_file('requests.get("https://api.example.com/data")')
        findings = scan_file_content(path)
        assert "SEC-007" not in rule_ids_in_findings(findings), (
            "SEC-007 must not fire for a hard-coded requests.get URL"
        )

    # ── SEC-008 : Production Debug Mode Enabled ───────────────────────────────

    def test_sec008_positive_debug_true(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``DEBUG = True`` must trigger SEC-008.

        The regex arm that fires here: ``DEBUG\\s*=\\s*True``
        """
        path = tmp_py_file("DEBUG = True")
        findings = scan_file_content(path)
        assert "SEC-008" in rule_ids_in_findings(findings), (
            "Expected SEC-008 finding for DEBUG = True"
        )

    def test_sec008_negative_log_level_info(
        self, tmp_py_file: Callable[[str, str], Path]
    ):
        """
        ``LOG_LEVEL = "INFO"`` must NOT trigger SEC-008.
        """
        path = tmp_py_file('LOG_LEVEL = "INFO"')
        findings = scan_file_content(path)
        assert "SEC-008" not in rule_ids_in_findings(findings), (
            "SEC-008 must not fire for a non-debug configuration line"
        )
