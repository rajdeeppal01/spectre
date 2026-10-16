# Implementation Plan: SPECTRE Test Suite

## Overview

Build a pytest-based test suite covering all core SPECTRE modules — AUTO router, Continuous
Security scanner, PQC Auditor, Quantum Simulator, QRNG, Burp Bridge, and Red Team Crew — with
shared fixture infrastructure, Hypothesis property-based tests, and a GitHub Actions CI workflow.
All unit tests run fully air-gapped (no real network calls); integration tests live behind a
`--run-integration` flag.

---

## Tasks

- [ ] 1. Create test infrastructure
  - [ ] 1.1 Create pyproject.toml pytest configuration
    - Add `[tool.pytest.ini_options]` section with `testpaths = ["tests"]`, `asyncio_mode = "auto"`, `addopts` with `--cov=scripts --cov=agents --cov-report=html:htmlcov --cov-fail-under=70`, and `markers` for `integration`, `unit`, and `pbt`
    - _Requirements: 1.1, 1.3, 1.4, 9.2_

  - [ ] 1.2 Create requirements-test.txt with pinned dependencies
    - Write `requirements-test.txt` at repo root with exact-version pins: `pytest==8.2.2`, `pytest-asyncio==0.23.8`, `pytest-cov==5.0.0`, `hypothesis==6.108.5`, `httpx[asyncio]==0.27.0`
    - _Requirements: 1.5_

  - [ ] 1.3 Create tests/ directory skeleton with __init__.py files
    - Create `tests/__init__.py`, `tests/scripts/__init__.py`, `tests/agents/__init__.py`, `tests/integration/__init__.py`
    - _Requirements: 1.1_

  - [ ] 1.4 Create root tests/conftest.py with all shared fixtures
    - Implement `mock_ollama` fixture: monkeypatch `urllib.request.urlopen` to return `io.BytesIO`-wrapped `{"response": "mock AI analysis", "done": true}` JSON
    - Implement `mock_openai_client` fixture: monkeypatch `agents.web_audit_bridge.CLIENT` with a `MagicMock` whose `.chat.completions.create()` returns a fake `ChatCompletion`-shaped `SimpleNamespace`
    - Implement `mock_anu_success` fixture: monkeypatch `scripts.quantum_rng.urllib.request.urlopen` to return valid ANU JSON `{"success": True, "data": list(range(n))}`
    - Implement `mock_anu_failure` fixture: monkeypatch `scripts.quantum_rng.urllib.request.urlopen` with `side_effect=urllib.error.URLError("unreachable")`
    - Implement `mock_litellm` fixture: monkeypatch `httpx.AsyncClient` to return an async context manager yielding fake SSE chunk `b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'`
    - Implement `tmp_py_file` fixture: factory callable `(content, suffix=".py") -> Path` using `tmp_path`
    - Implement `tmp_dir_with_files` fixture: factory callable `(file_map: dict) -> Path` populating `tmp_path` with named files
    - _Requirements: 1.2_

  - [ ] 1.5 Create tests/integration/conftest.py with skip guard
    - Register `--run-integration` CLI option via `pytest_addoption`
    - Implement `pytest_runtest_setup` hook that calls `pytest.skip()` for any test marked `integration` when `--run-integration` is not passed
    - _Requirements: 1.2, 9.1, 9.2, 9.3_

- [ ] 2. Implement AUTO router unit tests
  - [ ] 2.1 Write example-based routing rule tests
    - Implement `TestChooseModelRouting` class in `tests/scripts/test_auto_router.py`
    - Test 2.1: cybersec keyword → `"spectre"` (use `monkeypatch` on `has_internet`, pass payload with `"exploit payload"`)
    - Test 2.2: `is_private=True` + internet → `"architect"`
    - Test 2.3: offline + short simple prompt → `"atlas"`
    - Test 2.4: offline + complexity-pattern prompt → `"architect"`
    - Test 2.5: online + >1000-word prompt → `"gemini-pro"`
    - Test 2.6: online + <50-word prompt → `"gemini-flash"`
    - Test 2.7: online + 50–1000-word prompt → `"gemini-pro"`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ] 2.2 Write /healthz endpoint test
    - Implement `TestHealthzEndpoint` using `httpx.AsyncClient(app=app, base_url="http://test")`
    - Assert HTTP 200 and response JSON has shape `{"status": "ok", "internet": <bool>}`
    - _Requirements: 2.9_

  - [ ]* 2.3 Write PBT for choose_model valid output
    - Implement `TestChooseModelPBT` using `@given` with `st.fixed_dictionaries` generating random message bodies and `st.booleans()` for `is_private`
    - Use `@settings(max_examples=100)` and monkeypatch `has_internet` to `lambda: False`
    - Assert result is always in `{"spectre", "architect", "atlas", "gemini-flash", "gemini-pro"}`
    - _Requirements: 2.10 — Property 1: choose_model output is always a valid model name_

  - [ ]* 2.4 Write PBT for cybersecurity keyword routing invariant
    - Implement `test_cybersec_keyword_always_routes_to_spectre` using `@given` with content generated from `CYBERSEC_PATTERN`-matching strings
    - Use `@settings(max_examples=100)` and monkeypatch `has_internet`
    - Assert `choose_model` always returns `"spectre"` when any message content matches `CYBERSEC_PATTERN`
    - _Requirements: 2.11 — Property 2: Cybersecurity keyword routing invariant_

- [ ] 3. Checkpoint — infrastructure and router tests runnable
  - Ensure `pytest tests/scripts/test_auto_router.py` passes, ask the user if questions arise.

- [ ] 4. Implement Continuous Security scanner unit tests
  - [ ] 4.1 Write true-positive and true-negative tests for all 8 SEC rules
    - Implement `TestScanFileContentRules` in `tests/scripts/test_continuous_security.py`
    - For each of SEC-001 through SEC-008: write one snippet that triggers the rule and one that does not, using `tmp_py_file` fixture
    - SEC-001 positive: `api_key = "EXAMPLE_sk_live_XXXXXXXXXXXXXXXXXXXX"`; negative: `api_key = "short"`
    - SEC-002 positive: SQL string concatenation; negative: parameterised query
    - SEC-003 positive: `os.system(user_input)`; SEC-004 positive: `element.innerHTML = user_data`
    - SEC-005 positive: `open(f"/data/{request.args['file']}")`; SEC-006 positive: `hashlib.md5(data)`
    - SEC-007 positive: `requests.get(request.args['url'])`; SEC-008 positive: `DEBUG = True`
    - _Requirements: 3.1_

  - [ ] 4.2 Write SEC-001 and SEC-002 severity assertion tests
    - Implement `TestScanFileContentSpecificRules` asserting `rule_id == "SEC-001"` and `severity == "CRITICAL"` for the API key snippet
    - Assert `rule_id == "SEC-002"` and `severity == "HIGH"` for the SQL injection snippet
    - _Requirements: 3.2, 3.3_

  - [ ] 4.3 Write edge case tests (self-reference exclusion and clean file)
    - Implement `TestScanFileContentEdgeCases`
    - Self-reference: write a file whose sole line is the regex pattern itself and assert no findings
    - Clean file: write a file with no matching content and assert empty list returned
    - _Requirements: 3.4, 3.5_

  - [ ] 4.4 Write scan_directory tests (ignored dirs, ai_assist on/off)
    - Implement `TestScanDirectory` using `tmp_dir_with_files` fixture
    - Create a tree with `.git/`, `node_modules/`, and `__pycache__/` subdirs each containing a positive snippet; assert none are scanned
    - With `ai_assist=True` and `mock_ollama`: assert `query_spectre_ai` called once per finding and `finding["ai_analysis"]` is populated
    - With `ai_assist=False`: assert `query_spectre_ai` is never called
    - _Requirements: 3.6, 3.7, 3.8_

  - [ ] 4.5 Write log_findings output format test
    - Implement `TestLogFindings` using `tmp_path`
    - Call `log_findings` with a synthetic findings list; assert file is created and each entry contains `rule_id`, `severity`, `file`, `line`, and `match` text
    - Test with a non-existent log path to verify the file is created
    - _Requirements: 3.9_

  - [ ]* 4.6 Write PBT for SEC-001 regex match consistency
    - Implement `TestScanFilePBT` using `@given` with `st.text(alphabet=string.ascii_letters + string.digits + "_-.", max_size=200)`
    - For each generated string: if it matches the SEC-001 compiled regex assert exactly one finding with `rule_id == "SEC-001"`; otherwise assert empty list
    - _Requirements: 3.10 — Property 3: SEC-001 scanner output matches regex_

- [ ] 5. Implement PQC Auditor unit tests
  - [ ] 5.1 Write true-positive and true-negative tests for all 6 PQC-VULN patterns
    - Implement `TestScanFilePatterns` in `tests/scripts/test_pqc_audit.py`
    - PQC-VULN-001 positive: `RSA.generate(2048)`; negative: `ec.generate_private_key`
    - PQC-VULN-002 positive: `from cryptography.hazmat.primitives.asymmetric import dh`
    - PQC-VULN-003 positive: `from Crypto.Signature import PKCS1_v1_5`
    - PQC-VULN-004 positive: `from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey`
    - PQC-VULN-005 positive: `AES.new(key, AES.MODE_CBC, key_size=128)`
    - PQC-VULN-006 positive: `hashlib.md5(data)`; negative: `hashlib.sha256(data)`
    - Use `tmp_py_file` fixture for all snippets
    - _Requirements: 4.1_

  - [ ] 5.2 Write RSA and MD5 severity assertion tests
    - Implement `TestScanFileSpecific` asserting `vuln_id == "PQC-VULN-001"` and `severity == "CRITICAL"` for RSA snippet
    - Assert `vuln_id == "PQC-VULN-006"` and `severity == "HIGH"` for MD5 snippet
    - _Requirements: 4.2, 4.3_

  - [ ] 5.3 Write run_scan extension filtering and ignored-dir tests
    - Implement `TestRunScan` using `tmp_dir_with_files`
    - Create directory with `.py`, `.java`, `.txt`, and an ignored subdirectory; assert only supported extensions are scanned and `IGNORE_DIRS` are skipped
    - _Requirements: 4.4, 4.5_

  - [ ] 5.4 Write generate_markdown_report output tests
    - Implement `TestGenerateMarkdownReport`
    - With ≥1 CRITICAL finding: assert `"harvest now, decrypt later"` appears under `## Executive Summary`
    - With zero findings: assert `"No critical asymmetric key exchange vulnerabilities detected"` appears in executive summary
    - _Requirements: 4.6, 4.7_

  - [ ] 5.5 Write AI remediation failure and ai_assist=False tests
    - Implement `TestAIRemediation`
    - Unreachable Ollama: monkeypatch `scripts.pqc_audit.urllib.request.urlopen` with `side_effect=urllib.error.URLError("unreachable")`; assert return value starts with `"[AI consultation unavailable"`
    - `ai_assist=False`: assert `query_ai_remediation` is never called
    - _Requirements: 4.8, 4.9_

  - [ ]* 5.6 Write PBT for PQCAuditor.scan_file non-negative count
    - Implement `TestScanFilePBT` using `@given(st.text(max_size=10000))`
    - Write generated string to a `tmp_py_file` and assert finding count `>= 0` and no unhandled exception raised
    - _Requirements: 4.10 — Property 4: PQCAuditor.scan_file never returns a negative count_

- [ ] 6. Implement Quantum Simulator unit tests
  - [ ] 6.1 Write StatevectorSim gate operation tests
    - Implement `TestStatevectorSimGates` in `tests/scripts/test_quantum_sim.py`
    - Hadamard on |0⟩: assert both amplitudes have magnitude `1/sqrt(2)` within `1e-9` using `pytest.approx`
    - Hadamard self-inverse: apply H twice to same qubit; assert statevector returns to |0⟩ within `1e-9`
    - Bell state via H+CNOT: assert `|01⟩` and `|10⟩` amplitudes have magnitude `< 1e-9`
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 6.2 Write Bell state demo and Grover demo tests
    - Implement `TestBellStateDemo`: call `run_bell_state_demo(shots=1024)`; assert counts for `"01"` and `"10"` are each 0
    - Implement `TestGroverDemo`: for all `target_state` in `[0, 2^num_qubits - 1]` with `num_qubits` in `[2, 4]`, assert `success_rate_percent > 80.0`
    - _Requirements: 5.4, 5.5_

  - [ ] 6.3 Write Shor toy demo and LWE demo tests
    - `TestShorToyDemo`: `N=15, a=7` → assert `rsa_broken == True` and `computed_factors` contains 3 and 5 in any order
    - `TestShorToyDemo`: `N=15, a=3` → assert result dict has `"error"` key and no exception raised
    - `TestLWEDemo`: call `run_lwe_demo()`; for each sample assert `noise in {-1, 0, 1}` and `0 <= b <= q-1`
    - _Requirements: 5.6, 5.7, 5.8_

  - [ ]* 6.4 Write PBT for Grover lower-bound invariant
    - Implement `TestGroverPBT` using `@given(st.integers(2,5), ...)` generating valid `(num_qubits, target_state)` pairs
    - Use `@settings(max_examples=100)`; assert `success_rate_percent >= 50.0` for all generated inputs
    - _Requirements: 5.9 — Property 5: Grover quadratic speedup lower-bound invariant_

  - [ ]* 6.5 Write PBT for statevector probability normalisation
    - Implement `TestNormalisationPBT` using `@given` with `st.integers(1,6)` for qubits and `st.lists(st.tuples(...))` for gate sequences
    - Clamp qubit index to valid range; apply gates; assert `abs(sum(get_probabilities()) - 1.0) < 1e-9`
    - Use `@settings(max_examples=100)`
    - _Requirements: 5.10 — Property 6: Quantum statevector probability normalisation_

- [ ] 7. Implement QRNG unit tests
  - [ ] 7.1 Write ANU API success and failure path tests
    - Implement `TestFetchANUQuantumBytes` in `tests/scripts/test_quantum_rng.py`
    - Success path with `mock_anu_success`: assert return is `bytes` of exactly the requested length
    - Failure path with `mock_anu_failure`: assert return is `None` and no exception raised
    - _Requirements: 6.1, 6.2_

  - [ ] 7.2 Write local jitter entropy tests including ValueError edge case
    - Implement `TestLocalJitterEntropy`
    - For `n` in `[1, 512]` example cases: assert result is `bytes` of exactly `n` bytes
    - `n=0`: assert `ValueError` raised; `n=-1`: assert `ValueError` raised
    - _Requirements: 6.3, 6.11_

  - [ ] 7.3 Write get_quantum_entropy offline and fallback tests
    - Implement `TestGetQuantumEntropy`
    - `force_offline=True`: call without any ANU mock; assert ANU urlopen is never called
    - `force_offline=False` with `mock_anu_failure`: assert result falls back to local entropy and returns `bytes` of the requested length
    - _Requirements: 6.4, 6.5_

  - [ ] 7.4 Write bundle generator and session token tests
    - Implement `TestBundleGenerators`: assert `generate_aes256_gcm_bundle()` returns dict with `key_hex` of length 64 and `iv_hex` of length 24, both hex characters only
    - Assert `generate_pqc_seed_bundle()` returns dict where `byte_length == 64` and `seed_hex` is 128 hex characters
    - Implement `TestSessionTokens`: for example `(count, length)` pairs assert list length and each string length; assert every character is URL-safe base64
    - _Requirements: 6.6, 6.7, 6.8_

  - [ ]* 7.5 Write PBT for local jitter entropy length invariant
    - Implement `TestJitterEntropyPBT` using `@given(st.integers(1, 512))`
    - Use `@settings(max_examples=200)`; assert `len(generate_local_quantum_jitter_entropy(n)) == n`
    - _Requirements: 6.9 — Property 7: Local jitter entropy length invariant_

  - [ ]* 7.6 Write PBT for session token count and length invariants
    - Implement `TestSessionTokensPBT` using `@given(st.integers(1,100), st.integers(16,256))`
    - Use `@settings(max_examples=100)`; assert list has exactly `count` strings each of exactly `length` characters
    - _Requirements: 6.10 — Property 8: Session token count and length invariants_

- [ ] 8. Checkpoint — unit tests for scripts/ passing
  - Ensure `pytest tests/scripts/` completes without failures, ask the user if questions arise.

- [ ] 9. Implement Burp Bridge unit tests
  - [ ] 9.1 Write XML parsing tests (item count, base64 decode, missing tags, FileNotFoundError)
    - Implement `TestParseBurpXML` in `tests/agents/test_web_audit_bridge.py`
    - N-item XML: assert returns list of exactly N dicts each with `"url"`, `"method"`, `"request"`, `"response"` keys
    - Base64 decode: XML with `base64="true"` elements; assert decoded UTF-8 strings returned correctly
    - Invalid UTF-8 base64: assert decoded with `errors="replace"` and no exception raised
    - Missing `<request>` or `<response>` tag: assert that field is an empty string
    - Non-existent path: assert `FileNotFoundError` raised
    - Include `make_burp_xml` helper function in the test module for building fixture XML strings
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 9.2 Write main() FileNotFoundError handling test
    - Implement `TestMainFileNotFound` using `capsys` and `monkeypatch.setattr("sys.argv", ["prog", "nonexistent.xml"])`
    - Assert error message printed to stdout and no unhandled exception propagated
    - _Requirements: 7.6_

  - [ ] 9.3 Write analyze_traffic tests (Ollama call count and exception handling)
    - Implement `TestAnalyzeTraffic` using the `mock_openai_client` fixture from root conftest
    - Assert OpenAI client called exactly once when traffic dict has `"url"`, `"method"`, `"request"` keys
    - Simulate exception in mock `.chat.completions.create`; assert return value starts with `"Error analyzing request:"`
    - _Requirements: 7.7, 7.8_

- [ ] 10. Implement Red Team Crew unit tests
  - [ ] 10.1 Write crew factory structure and wiring tests with importorskip guard
    - Add `crewai = pytest.importorskip("crewai", reason="crewai not installed; skipping Red Team Crew tests")` at module level in `tests/agents/test_red_team_crew.py`
    - Add module-level autouse fixture that monkeypatches `agents.red_team_crew.Ollama` with a `MagicMock` before any test runs
    - Implement `TestCreateRedTeamCrew` with a `crew` fixture that calls `create_red_team_crew("target.example.com")`
    - Assert `len(crew.agents) == 4`
    - Assert agent roles match `["Reconnaissance Specialist", "Exploit Developer", "Security Code Reviewer", "Lead Penetration Tester"]` in order
    - Assert all four agents have `allow_delegation=False`
    - Assert `crew.tasks[0].description` contains `"target.example.com"` as substring
    - Assert task-to-agent assignment order: recon→index 0, exploit→index 1, review→index 2, report→index 3
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 11. Implement integration test layer
  - [ ] 11.1 Write test_ollama_live.py
    - Create `tests/integration/test_ollama_live.py`
    - Mark test with `@pytest.mark.integration`
    - Check Ollama health at `http://localhost:11434/api/tags`; if not HTTP 200, call `pytest.skip("Ollama unreachable")`
    - Send a real chat completion request to the `atlas` model and assert `response.content` length `>= 1`
    - _Requirements: 9.4, 9.5_

  - [ ] 11.2 Write test_router_live.py
    - Create `tests/integration/test_router_live.py`
    - Mark test with `@pytest.mark.integration`
    - Submit prompt containing `"exploit"` to the AUTO router endpoint; assert HTTP 200 and response contains `proxied_model == "spectre"`
    - _Requirements: 9.6_

  - [ ] 11.3 Write test_qrng_live.py
    - Create `tests/integration/test_qrng_live.py`
    - Mark test with `@pytest.mark.integration`
    - Call `fetch_anu_quantum_bytes(32)`; assert result is `None` or `bytes` of length exactly 32; propagate any exception as test failure
    - _Requirements: 9.7_

- [ ] 12. Create GitHub Actions CI workflow
  - [ ] 12.1 Write .github/workflows/test.yml
    - Create `.github/workflows/test.yml` with job `unit-tests` running on `ubuntu-latest`
    - Triggers: `push` on all branches, `pull_request` on `main` and `develop`
    - Steps: checkout (`actions/checkout@v4`), Python 3.11 setup (`actions/setup-python@v5`), `pip install -r requirements-test.txt`
    - Run `pytest --cov=scripts --cov=agents --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-fail-under=70 --junitxml=test-results.xml -v --ignore=tests/integration`
    - Add per-module 80% coverage check step: inline Python script that parses `coverage.xml`, iterates over the six core modules, and exits non-zero if any module is below 80%
    - Upload `htmlcov/` as artifact `coverage-report` with `if: always()`
    - Upload `test-results.xml` as artifact `test-results` with `if: always()`
    - No Docker services required
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [ ] 13. Final checkpoint — full suite green
  - Ensure `pytest --ignore=tests/integration` completes with ≥70% suite coverage and all unit tests pass; ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; all core requirements are covered by non-optional tasks.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation after each major module group.
- Property tests validate universal correctness invariants; unit tests validate specific examples and error paths.
- Tasks 2–7 (module test files) are independent of each other and can be executed in parallel once infrastructure tasks 1.1–1.5 are complete.
- The `tests/integration/conftest.py` skip guard in task 1.5 is a prerequisite for all integration test tasks (11.1–11.3).
- The CI workflow (task 12.1) is independent of integration tests and can be written once unit tests are passing.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "1.5"] },
    { "id": 2, "tasks": ["2.1", "2.2", "4.1", "5.1", "6.1", "7.1", "9.1", "10.1"] },
    { "id": 3, "tasks": ["2.3", "2.4", "4.2", "4.3", "4.4", "4.5", "5.2", "5.3", "6.2", "6.3", "7.2", "7.3", "7.4", "9.2", "9.3"] },
    { "id": 4, "tasks": ["4.6", "5.4", "5.5", "6.4", "6.5", "7.5", "7.6"] },
    { "id": 5, "tasks": ["5.6", "11.1", "11.2", "11.3"] },
    { "id": 6, "tasks": ["12.1"] }
  ]
}
```
