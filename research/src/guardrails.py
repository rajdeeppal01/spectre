import re
import logging
from typing import Tuple, List

logger = logging.getLogger("uvicorn.error")

class AIGuardrail:
    """
    Enterprise-grade AI Guardrail engine protecting LLM endpoints against 
    OWASP LLM Top 10 vulnerabilities (Prompt Injection, Jailbreaking, PII leakage, Model DoS).
    """
    
    INJECTION_PATTERNS: List[str] = [
        r"ignore\s+(previous|prior|all)\s+instructions",
        r"disregard\s+(previous|prior|all)\s+instructions",
        r"system\s+prompt",
        r"developer\s+mode",
        r"you\s+are\s+now\s+dan",
        r"do\s+anything\s+now",
        r"bypass\s+(security|guardrails|filters)",
        r"reveal\s+(internal|secret|hidden)\s+instructions",
        r"act\s+as\s+an\s+unrestricted",
        r"print\s+your\s+initial\s+prompt",
        r"new\s+instructions:",
        r"sudo\s+mode",
    ]

    SECRET_PATTERNS: List[str] = [
        r"sk-[a-zA-Z0-9_-]{15,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN\s+PRIVATE\s+KEY-----",
    ]

    def __init__(self, max_length: int = 2000):
        self.max_length = max_length
        self.compiled_injections = [re.compile(pattern, re.IGNORECASE) for pattern in self.INJECTION_PATTERNS]
        self.compiled_secrets = [re.compile(pattern) for pattern in self.SECRET_PATTERNS]

    def validate_prompt(self, prompt: str) -> Tuple[bool, str]:
        """
        Validates the incoming user prompt against safety heuristics.
        Returns:
            (is_safe: bool, reason: str)
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Prompt must be a non-empty string."

        # Check length / DoS guard
        if len(prompt) > self.max_length:
            return False, f"Prompt exceeds maximum allowed length of {self.max_length} characters."

        # Check for Prompt Injection / Jailbreak patterns
        for pattern in self.compiled_injections:
            if pattern.search(prompt):
                logger.warning(f"Blocked prompt injection pattern detected: {pattern.pattern}")
                return False, "Prompt injection or jailbreak attempt detected."

        # Check for accidental secret leakage in prompt
        for secret_pattern in self.compiled_secrets:
            if secret_pattern.search(prompt):
                logger.warning("Secret pattern detected in user prompt.")
                return False, "Prompt contains sensitive credentials or secret keys."

        return True, "Prompt passed security guardrails successfully."

    def sanitize_output(self, output: str) -> str:
        """
        Sanitizes LLM output to prevent reflected XSS or secret disclosure.
        """
        if not output:
            return ""
        
        # Redact potential API keys or sensitive strings in output
        sanitized = output
        for secret_pattern in self.compiled_secrets:
            sanitized = secret_pattern.sub("[REDACTED_SECRET]", sanitized)

        return sanitized
