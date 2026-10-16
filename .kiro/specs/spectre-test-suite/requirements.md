# Requirements Document

## Introduction

SPECTRE currently has zero test coverage across 13 scripts, 2 agent pipelines, a FastAPI routing
layer, and a RAG subsystem. This feature introduces a comprehensive pytest-based test suite that
validates correctness of all core logic modules, prevents regressions as the project evolves, and
integrates into a GitHub Actions CI pipeline. The suite is structured to run fully air-gapped (no
real network calls) in unit mode, and optionally connects to live local services in a separate
integration layer.

---

## Glossary

- **Test_Suite**: The complete collection of automated tests described in this document, residing
  under `tests/` at the repository root.
- **Unit_Test**: A test that executes a single function or class in isolation with all external
  I/O mocked.
- **Integration_Test**: A test that exercises one or more modules against a live local service
  (Ollama, LiteLLM) and is separated into `tests/integration/`.
- **PBT**: Property-Based Test — a test driven by the Hypothesis library that generates randomised
  inputs to verify invariants rather than fixed examples.
- **Auto_Router**: The FastAPI application in `scripts/auto_router.py` that routes chat
  completions to the optimal model.
- **Security_Scanner**: The scanning engine in `scripts/continuous_security.py` that detects
  OWASP and secret patterns using eight regex rules (SEC-001 through SEC-008).
- **PQC_Auditor**: The `PQCAuditor` class in `scripts/pqc_audit.py` that detects quantum-
  vulnerable cryptographic primitives using six regex rules (PQC-VULN-001 through PQC-VULN-006).
- **Quantum_Sim**: The `StatevectorSim` class and demonstration functions in
  `scripts/quantum_sim.py`.
- **QRNG**: The quantum random-number generation layer in `scripts/quantum_rng.py`, comprising the
  ANU API fetcher and the local jitter entropy fallback.
- **Burp_Bridge**: The Burp Suite XML parsing and AI-analysis pipeline in
  `agents/web_audit_bridge.py`.
- **Red_Team_Crew**: The four-agent CrewAI pipeline in `agents/red_team_crew.py`.
- **Ollama_API**: The local model-serving HTTP endpoint at `http://localhost:11434` used by
  SPECTRE, ATLAS, ARCHITECT, and ORACLE.
- **ANU_API**: The external quantum-vacuum entropy endpoint at `https://qrng.anu.edu.au`.
- **LiteLLM_Proxy**: The unified model-routing proxy at `http://localhost:4000`.
- **Mock**: A test double provided by `unittest.mock` or `pytest` monkeypatching that replaces a
  real external dependency.
- **Fixture**: A pytest setup/teardown helper that provides shared test state.
- **Coverage_Target**: The minimum percentage of lines in a module that must be exercised by the
  test suite before a pull request may be merged.

---

## Requirements

### Requirement 1: Test Infrastructure Setup

**User Story:** As a developer, I want a ready-to-run test infrastructure, so that I can execute
all tests with a single `pytest` command without manual configuration.

#### Acceptance Criteria

1. THE Test_Suite SHALL be organised under a `tests/` directory at the repository root, containing
   at minimum the subdirectories `tests/scripts/` and `tests/agents/`.
2. THE Test_Suite SHALL include a `conftest.py` at `tests/` providing shared fixtures for mocking
   the Ollama_API, ANU_API, LiteLLM_Proxy, and filesystem events.
3. THE Test_Suite SHALL include a `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]`
   section that configures test discovery, sets `asyncio_mode` to `"auto"`, and sets a minimum
   coverage threshold of 70%.
4. WHEN `pytest` is invoked from the repository root with no arguments, THE Test_Suite SHALL
   discover and execute all unit tests and produce a coverage report without requiring network
   access.
5. THE Test_Suite SHALL declare test dependencies (pytest, pytest-asyncio, pytest-cov, hypothesis)
   in a dedicated `requirements-test.txt` file separate from the main `requirements.txt`.
6. IF a test requires a missing optional dependency (e.g. `watchdog`, `crewai`), THEN THE
   Test_Suite SHALL skip that test with a skip message that names the missing dependency.

---

### Requirement 2: AUTO Router Unit Tests

**User Story:** As a developer, I want unit tests for the AUTO router's model-selection logic, so
that routing rules cannot regress silently as new keywords or complexity thresholds are added.

#### Acceptance Criteria

1. WHEN a chat message body contains a cybersecurity keyword matching the `CYBERSEC_PATTERN` regex,
   THE Auto_Router SHALL route the request to the `"spectre"` model regardless of any other
   condition.
2. WHEN a chat message body has `"x-spectre-private": "true"` in its headers and does NOT match
   the `CYBERSEC_PATTERN`, THE Auto_Router SHALL route the request to the `"architect"` model.
3. WHEN the `has_internet` function returns `False`, `is_private` is `False`, and the prompt does
   NOT match the `COMPLEXITY_PATTERN`, THE Auto_Router SHALL route the request to the `"atlas"`
   model.
4. WHEN the `has_internet` function returns `False`, `is_private` is `False`, and the prompt
   matches the `COMPLEXITY_PATTERN`, THE Auto_Router SHALL route the request to the `"architect"`
   model.
5. WHEN the `has_internet` function returns `True` and the prompt word-count exceeds 1000 words,
   THE Auto_Router SHALL route the request to `"gemini-pro"`.
6. WHEN the `has_internet` function returns `True` and the prompt contains fewer than 50 words and
   does not match any override rule, THE Auto_Router SHALL route the request to `"gemini-flash"`.
7. WHEN the `has_internet` function returns `True` and the prompt contains between 50 and 1000
   words (inclusive) and does not match any override rule, THE Auto_Router SHALL route the request
   to `"gemini-pro"`.
8. WHEN a POST request is made to `/v1/chat/completions` in an integration test context, THE
   Auto_Router SHALL proxy the modified body to `LiteLLM_Proxy` and stream the response back to
   the caller.
9. WHEN a GET request is made to `/healthz`, THE Auto_Router SHALL return HTTP 200 with a JSON
   body containing `"status": "ok"` and an `"internet"` boolean field.
10. THE Test_Suite SHALL include a PBT that generates random message bodies and verifies that
    `choose_model` always returns one of the five valid model names (`"spectre"`, `"architect"`,
    `"atlas"`, `"gemini-flash"`, `"gemini-pro"`).
11. THE Test_Suite SHALL include a PBT that verifies: for all message bodies containing at least
    one cybersecurity keyword from `CYBERSEC_PATTERN`, `choose_model` SHALL always return
    `"spectre"` (cybersecurity routing invariant).

---

### Requirement 3: Security Scanner Unit Tests

**User Story:** As a developer, I want unit tests for all eight security regex rules, so that
rule coverage is explicit and false-positive/negative regressions are caught immediately.

#### Acceptance Criteria

1. THE Test_Suite SHALL include, for each rule SEC-001 through SEC-008, at least one code snippet
   that triggers the rule (true positive) and at least one code snippet that does not trigger the
   rule (true negative).
2. WHEN `scan_file_content` is called on a file containing a hardcoded API key matching SEC-001,
   THE Security_Scanner SHALL return a finding with `rule_id == "SEC-001"` and
   `severity == "CRITICAL"`.
3. WHEN `scan_file_content` is called on a file containing a raw SQL string-concatenation
   matching SEC-002, THE Security_Scanner SHALL return a finding with `rule_id == "SEC-002"` and
   `severity == "HIGH"`.
4. WHEN `scan_file_content` is called on a line whose entire content consists of the rule's
   compiled regex pattern string (that is, any line matching at least one of the patterns used to
   define SEC-001 through SEC-008 within the scanner's own source), THE Security_Scanner SHALL
   NOT produce a finding for that line (self-reference exclusion).
5. WHEN `scan_file_content` is called on a clean file containing no vulnerable patterns, THE
   Security_Scanner SHALL return an empty list.
6. WHEN `scan_directory` is called on a directory containing ignored subdirectories (`.git`,
   `node_modules`, `__pycache__`), THE Security_Scanner SHALL NOT scan any file inside those
   directories.
7. WHEN `scan_directory` is called with `ai_assist=True`, THE Security_Scanner SHALL call
   `query_spectre_ai` exactly once per finding with the finding dict as its argument, and the
   returned string SHALL be stored in `finding["ai_analysis"]`.
8. WHEN `scan_directory` is called with `ai_assist=False`, THE Security_Scanner SHALL NOT call
   `query_spectre_ai`.
9. WHEN `log_findings` is called with a non-empty findings list, THE Security_Scanner SHALL write
   one Markdown entry per finding to the specified log file, where each entry contains at minimum
   the `rule_id`, `severity`, `file` path, `line` number, and `match` text; IF the specified log
   file does not exist, THEN THE Security_Scanner SHALL create it before writing.
10. THE Test_Suite SHALL include a property-based test that generates strings composed of
    characters drawn from the character classes defined in the SEC-001 compiled regex (letters,
    digits, and the symbols `_`, `-`, `.`), places each generated string as the sole line of a
    synthetic single-line file, and verifies that if the string matches the SEC-001 compiled regex
    then `scan_file_content` returns exactly one finding with `rule_id == "SEC-001"`, and if it
    does not match then `scan_file_content` returns an empty list.

---

### Requirement 4: PQC Auditor Unit Tests

**User Story:** As a developer, I want unit tests for the PQC auditor's six vulnerability
patterns, so that new NIST standard mappings can be added without breaking existing detections.

#### Acceptance Criteria

1. THE Test_Suite SHALL include, for each pattern in PQC-VULN-001 through PQC-VULN-006, at least
   one positive-case code snippet for which `PQCAuditor.scan_file` returns a finding list
   containing a finding whose `vuln_id` equals that pattern identifier, and at least one
   negative-case code snippet for which `PQCAuditor.scan_file` returns a finding list containing
   no finding whose `vuln_id` equals that pattern identifier.
2. WHEN `PQCAuditor.scan_file` is called on a Python file that calls `RSA.generate()`, THE
   PQC_Auditor SHALL produce a finding with `vuln_id == "PQC-VULN-001"` and
   `severity == "CRITICAL"`.
3. WHEN `PQCAuditor.scan_file` is called on a Python file that uses `hashlib.md5()`, THE
   PQC_Auditor SHALL produce a finding with `vuln_id == "PQC-VULN-006"` and `severity == "HIGH"`.
4. WHEN `PQCAuditor.run_scan` is called on a directory, THE PQC_Auditor SHALL process only files
   whose suffix is in `SUPPORTED_EXTENSIONS`.
5. WHEN `PQCAuditor.run_scan` is called on a directory, THE PQC_Auditor SHALL not recurse into
   subdirectories whose name is in `IGNORE_DIRS`.
6. WHEN `PQCAuditor.generate_markdown_report` is called after a scan with at least one CRITICAL
   finding, THE PQC_Auditor SHALL include a substring containing "harvest now, decrypt later" in
   the executive summary section identified by the heading `## Executive Summary`.
7. WHEN `PQCAuditor.generate_markdown_report` is called after a scan with zero findings, THE
   PQC_Auditor SHALL include the "No critical asymmetric key exchange vulnerabilities detected"
   sentence in the executive summary.
8. WHEN `PQCAuditor.query_ai_remediation` is called, IF the Ollama_API is unreachable, THEN THE
   PQC_Auditor SHALL return a string beginning with `"[AI consultation unavailable"` without
   raising an exception.
9. WHEN `PQCAuditor.enrich_with_ai` is called with `ai_assist=False`, THE PQC_Auditor SHALL NOT
   call `query_ai_remediation`.
10. THE Test_Suite SHALL include a PBT that generates random Python source strings of length
    between 0 and 10,000 characters, runs `PQCAuditor.scan_file`, and verifies that the number
    of findings returned is greater than or equal to zero.

---

### Requirement 5: Quantum Simulator Unit Tests

**User Story:** As a developer, I want unit tests for the statevector simulator's gate operations
and quantum demonstration functions, so that mathematical errors in quantum circuit logic are
caught before they silently corrupt cryptographic impact claims.

#### Acceptance Criteria

1. WHEN `StatevectorSim.apply_hadamard` is applied to a single-qubit simulator initialised in
   state |0>, THE Quantum_Sim SHALL produce a statevector where both amplitudes have magnitude
   `1/sqrt(2)` within a tolerance of 1e-9.
2. WHEN `StatevectorSim.apply_hadamard` is applied twice to the same qubit of a single-qubit
   simulator, THE Quantum_Sim SHALL return the simulator to its original state (Hadamard
   self-inverse invariant) within a tolerance of 1e-9.
3. WHEN `StatevectorSim.apply_cnot` is applied with control=0, target=1 after applying Hadamard
   to qubit 0, THE Quantum_Sim SHALL produce a Bell state where the amplitudes of the `|01>` and
   `|10>` basis states have magnitude less than 1e-9.
4. WHEN `run_bell_state_demo` is called and 1024 measurement shots are sampled, THE Quantum_Sim
   SHALL return a counts dictionary where the counts for `"01"` and `"10"` are each 0.
5. WHEN `run_grover_demo` is called with a known `target_state` and `num_qubits` in `[2, 4]`, THE
   Quantum_Sim SHALL return a `success_rate_percent` greater than 80.0 for all valid target values
   in range `[0, 2^num_qubits - 1]`.
6. WHEN `run_shor_toy_demo` is called with `N=15` and `a=7`, THE Quantum_Sim SHALL return a
   result where `rsa_broken == True` and `computed_factors` contains `[3, 5]` in any order.
7. WHEN `run_shor_toy_demo` is called with `N=15` and `a=3` (where `gcd(3, 15) == 3`), THE
   Quantum_Sim SHALL return a dict containing an `"error"` key without raising an exception.
8. WHEN `run_lwe_demo` is called, THE Quantum_Sim SHALL return a dict where each entry in
   `sample_noisy_equations` has a `"noise"` value in `{-1, 0, 1}` and a `"b"` value in the range
   `[0, q - 1]` where `q` is the value at the `"modulus_q"` key of the returned dict.
9. THE Test_Suite SHALL include a PBT with a minimum sample count of 100 examples that generates
   random `(target_state, num_qubits)` pairs with `num_qubits` in `[2, 5]` and verifies that
   `run_grover_demo` always returns `success_rate_percent >= 50.0` (Grover quadratic speedup
   lower-bound invariant).
10. THE Test_Suite SHALL include a PBT with a minimum sample count of 100 examples that generates
    random `num_qubits` values in `[1, 6]` and random gate sequences of at most 10 gates drawn
    from `{apply_hadamard, apply_pauli_x}`, and verifies that `StatevectorSim.get_probabilities`
    always sums to `1.0` within a tolerance of 1e-9 (normalisation invariant).

---

### Requirement 6: QRNG Unit Tests

**User Story:** As a developer, I want unit tests for the QRNG entropy functions, so that key
generation and token generation never produce empty, under-length, or out-of-range output.

#### Acceptance Criteria

1. WHEN `fetch_anu_quantum_bytes` is called and the ANU_API returns a valid `{"success": true,
   "data": [...]}` response where `data` contains exactly the requested number of integer values
   in `[0, 255]`, THE QRNG SHALL return a bytes object of exactly the requested length.
2. WHEN `fetch_anu_quantum_bytes` is called and the ANU_API is unreachable (network error), THE
   QRNG SHALL return `None` without raising an exception.
3. WHEN `generate_local_quantum_jitter_entropy` is called with a positive integer `n` in
   `[1, 512]`, THE QRNG SHALL return a bytes object of exactly `n` bytes where every byte value
   is in `[0, 255]`.
4. WHEN `get_quantum_entropy` is called with `force_offline=True`, THE QRNG SHALL NOT attempt to
   contact the ANU_API.
5. WHEN `get_quantum_entropy` is called with `force_offline=False` and the ANU_API returns `None`
   (mocked failure), THE QRNG SHALL fall back to `generate_local_quantum_jitter_entropy` and
   return a bytes object of exactly the requested length.
6. WHEN `generate_aes256_gcm_bundle` is called, THE QRNG SHALL return a dict where `key_hex` has
   length 64 characters, `iv_hex` has length 24 characters, and both strings contain only
   characters in `[0-9, a-f]`.
7. WHEN `generate_pqc_seed_bundle` is called, THE QRNG SHALL return a dict where the value at
   key `byte_length` equals 64 and `seed_hex` is a string of exactly 128 characters containing
   only characters in `[0-9, a-f]`.
8. WHEN `generate_session_tokens` is called with `count=N` where `N` is in `[1, 100]` and
   `length=L` where `L` is in `[16, 256]`, THE QRNG SHALL return a list of exactly `N` strings
   each of exactly `L` characters where every character is a URL-safe base64 character in
   `[A-Z, a-z, 0-9, -, _]`.
9. THE Test_Suite SHALL include a PBT that generates random integer values for `n` in `[1, 512]`
   and asserts that `generate_local_quantum_jitter_entropy(n)` returns a bytes object whose
   length equals `n`.
10. THE Test_Suite SHALL include a PBT that generates random integer pairs `(count, length)` where
    `count` is in `[1, 100]` and `length` is in `[16, 256]`, and asserts that
    `generate_session_tokens(count=count, length=length)` returns a list of exactly `count`
    strings each of exactly `length` characters.
11. IF `generate_local_quantum_jitter_entropy` is called with `n` equal to 0 or a negative
    integer, THEN THE QRNG SHALL raise a `ValueError` without returning a bytes object.

---

### Requirement 7: Burp Bridge Unit Tests

**User Story:** As a developer, I want unit tests for the Burp XML parser, so that malformed or
empty Burp exports do not cause unhandled exceptions in the agent pipeline.

#### Acceptance Criteria

1. WHEN `parse_burp_xml` is called with a well-formed Burp Suite XML file — defined as a file
   with a root `<items>` element containing one or more `<item>` child elements each having
   `<url>`, `<method>`, `<request>`, and `<response>` sub-elements — containing N items, THE
   Burp_Bridge SHALL return a list of exactly N dicts each containing `"url"`, `"method"`,
   `"request"`, and `"response"` keys.
2. WHEN `parse_burp_xml` is called with a Burp XML file where `<request>` or `<response>`
   elements carry a `base64="true"` attribute and contain valid Base64-encoded content, THE
   Burp_Bridge SHALL return the decoded UTF-8 strings in the `"request"` and `"response"` fields.
3. WHEN `parse_burp_xml` is called with a Burp XML file where `<request>` or `<response>`
   elements carry a `base64="true"` attribute but the decoded bytes are not valid UTF-8, THE
   Burp_Bridge SHALL return the raw decoded bytes decoded with `errors="replace"` in that field
   without raising an exception.
4. WHEN `parse_burp_xml` is called with a file that has a missing `<request>` or `<response>`
   tag, THE Burp_Bridge SHALL return an empty string for that field without raising an exception.
5. WHEN `parse_burp_xml` is called with a path to a non-existent file, THE Burp_Bridge SHALL
   raise a `FileNotFoundError`.
6. IF `parse_burp_xml` raises a `FileNotFoundError`, THEN the calling `main()` function SHALL
   catch the exception, print an error message indicating the file was not found, and exit without
   an unhandled exception propagating to the runtime.
7. WHEN `analyze_traffic` is called with a dict containing at minimum the keys `"url"`,
   `"method"`, and `"request"`, THE Burp_Bridge SHALL call the OpenAI-compatible Ollama_API
   endpoint exactly once and return the response content string.
8. WHEN `analyze_traffic` is called and the Ollama_API raises an exception, THE Burp_Bridge SHALL
   return a string beginning with `"Error analyzing request:"` without propagating the exception.

---

### Requirement 8: Red Team Crew Unit Tests

**User Story:** As a developer, I want unit tests for the Red Team crew factory, so that changes
to agent configuration or task wiring are caught before they break an automated pentest run.

#### Acceptance Criteria

1. WHEN `create_red_team_crew` is called with a target string, THE Red_Team_Crew SHALL return a
   `Crew` object containing exactly four agents with roles matching Reconnaissance Specialist,
   Exploit Developer, Security Code Reviewer, and Lead Penetration Tester.
2. WHEN `create_red_team_crew` is called with a target string, THE Red_Team_Crew SHALL return a
   `Crew` object containing exactly four tasks appearing in the tasks list in this order:
   `recon_task` at index 0 assigned to the Reconnaissance Specialist agent, `exploit_task` at
   index 1 assigned to the Exploit Developer agent, `review_task` at index 2 assigned to the
   Security Code Reviewer agent, and `report_task` at index 3 assigned to the Lead Penetration
   Tester agent.
3. WHEN `create_red_team_crew` is called with a target string, THE Red_Team_Crew SHALL configure
   all four agents with `allow_delegation=False`.
4. WHEN `create_red_team_crew` is called with a target string, THE Red_Team_Crew SHALL embed the
   target string in the `recon_task` description such that the description contains the target
   string as a substring.
5. THE Test_Suite SHALL invoke `pytest.importorskip("crewai")` at module level so that every test
   in the Red_Team_Crew test module is skipped when the `crewai` package is not installed.

---

### Requirement 9: Integration Test Layer

**User Story:** As a developer, I want a separate integration test suite that can be run against
live local services, so that end-to-end connectivity with Ollama and LiteLLM can be verified
without polluting the fast unit test run.

#### Acceptance Criteria

1. THE Test_Suite SHALL place all integration tests under `tests/integration/`.
2. THE Test_Suite SHALL mark every integration test with a custom `@pytest.mark.integration`
   marker registered in `pytest.ini` or `pyproject.toml`.
3. WHEN integration tests are run without the `--run-integration` pytest flag, THE Test_Suite
   SHALL skip all tests marked `integration` by calling `pytest.skip()` with a message indicating
   the flag is required.
4. WHEN `tests/integration/test_ollama_live.py` is run with `--run-integration` and the Ollama
   service returns HTTP 200 on its health endpoint, THE Test_Suite SHALL send one real chat
   completion request to the `atlas` model and assert that the response `content` field is a
   string of length ≥ 1 character.
5. IF the Ollama service does not return HTTP 200 on its health endpoint, THEN THE Test_Suite
   SHALL skip the test with a message indicating Ollama is unreachable.
6. WHEN `tests/integration/test_router_live.py` is run with `--run-integration`, THE Test_Suite
   SHALL submit a prompt containing the word `"exploit"` to the Auto_Router endpoint and assert
   that the response body contains `proxied_model` equal to `"spectre"` and that the HTTP
   response status is 200.
7. WHEN `tests/integration/test_qrng_live.py` is run with `--run-integration`, THE Test_Suite
   SHALL call `fetch_anu_quantum_bytes(32)` and assert that the return value is either a `bytes`
   object of length exactly 32 or `None`; IF `fetch_anu_quantum_bytes(32)` raises an exception,
   THEN THE Test_Suite SHALL fail the test with the raised exception message.

---

### Requirement 10: Coverage and CI

**User Story:** As a developer, I want automated coverage enforcement in CI, so that the codebase
coverage never drops below threshold on a merged pull request.

#### Acceptance Criteria

1. THE Test_Suite SHALL configure `pytest-cov` to measure line coverage for `scripts/` and
   `agents/` directories and write an HTML report to `htmlcov/`.
2. WHEN unit tests are run for the core logic modules (auto_router, continuous_security,
   pqc_audit, quantum_sim, quantum_rng, web_audit_bridge), THE Test_Suite SHALL achieve a minimum
   line coverage of 80% per module.
3. WHEN a push or pull request event is received by the GitHub Actions workflow defined in
   `.github/workflows/test.yml`, THE GitHub Actions workflow SHALL install test dependencies, run
   `pytest --run-unit` with coverage, and upload the HTML coverage report as a workflow artifact.
4. WHEN a pull request reduces coverage on any core logic module below 80%, THE GitHub Actions
   workflow SHALL exit with a non-zero code and block the merge.
5. IF the GitHub Actions runner has no GPU or Ollama installed, THEN THE Test_Suite SHALL pass all
   unit tests (integration tests are skipped by default) without any Docker service dependency.
6. THE Test_Suite SHALL produce JUnit-compatible XML test results (`--junitxml=test-results.xml`)
   so that CI platforms can display per-test pass/fail status.
7. IF `pytest-cov` fails to measure coverage for any configured source directory (e.g., directory
   not found or import error), THEN THE GitHub Actions workflow SHALL exit with a non-zero code
   and report an error message indicating which directory caused the failure.
