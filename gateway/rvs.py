"""
rvs.py -- Phase 2: Recovery Validation Score (RVS)
Role: Output-side sensitive-data detector and quarantine gate.

Implements two sub-scores:

  SR  (Semantic Recovery)
      Bag-of-Words cosine similarity between the tool output and a
      reference corpus of known sensitive/crown-jewel strings.
      High SR means the output vocabulary closely matches secret material.
      Phase 3 extension: replace BoW with sentence-transformer embeddings.

  SSR (Sensitive-String Recovery)
      Regex-based detection of nine canonical sensitive-data patterns:
      API keys, JWTs, passwords, PII, credentials, etc.
      SSR_score = matched_pattern_types / total_pattern_types

Composite score:
  RVS = RVS_WEIGHT_SR * SR + RVS_WEIGHT_SSR * SSR_score

Enforcement:
  RVS >= RVS_QUARANTINE_THRESHOLD  ->  QUARANTINE  (output suppressed)
  RVS >= RVS_WARN_THRESHOLD        ->  RVS_WARN    (output allowed, flagged)
  RVS <  RVS_WARN_THRESHOLD        ->  RVS_PASS

No FastAPI, no Redis, no external dependencies. Stdlib only.
"""

import re
from collections import Counter
from math import sqrt
from typing import Any

# ---------------------------------------------------------------------------
# Reference corpus: Tenant A crown-jewel strings
# (In production these are loaded from a vault; here they are synthetic.)
# ---------------------------------------------------------------------------

REFERENCE_CORPUS: list[str] = [
    "db-password sup3r_s3cr3t_2024 postgres admin credentials tenant-A",
    "api-key sk-abc123defgh456ijkl production tenant-A authorization",
    "jwt signing key authorization bearer token secret tenant-A",
    "private key RSA PRIVATE KEY certificate pkcs8 pem begin",
    "credit card 4532 1234 5678 9012 visa mastercard billing payment",
    "ssn 123-45-6789 employee personal record social security",
    "email admin@tenant-a-internal.corp user credentials login password",
    "aws access key AKIAIOSFODNN7EXAMPLE secret key region bucket",
]

# ---------------------------------------------------------------------------
# SSR pattern registry (9 pattern types)
# ---------------------------------------------------------------------------

SSR_PATTERNS: dict[str, str] = {
    "api_key_openai":   r"sk-[a-zA-Z0-9]{8,}",
    "api_key_aws":      r"AKIA[A-Z0-9]{16}",
    "jwt_token":        r"eyJ[a-zA-Z0-9_\-]{10,}",
    "password_literal": r"(?i)(?:password|passwd|pwd)\s*[=:]\s*\S+",
    "email_address":    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "ipv4_address":     r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "credit_card":      r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
    "ssn":              r"\b\d{3}-\d{2}-\d{4}\b",
    "pem_private_key":  r"-----BEGIN\s+(?:RSA\s+)?PRIVATE KEY-----",
}

TOTAL_PATTERNS = len(SSR_PATTERNS)   # 9

# ---------------------------------------------------------------------------
# Thresholds and weights
# ---------------------------------------------------------------------------

RVS_WEIGHT_SR:  float = 0.6
RVS_WEIGHT_SSR: float = 0.4

RVS_WARN_THRESHOLD:       float = 0.15   # flag output as potentially sensitive
RVS_QUARANTINE_THRESHOLD: float = 0.30   # suppress output from reaching caller

# ---------------------------------------------------------------------------
# Tokenizer (alphanum only — robust against =, :, -, @, . delimiters)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


# ---------------------------------------------------------------------------
# SR — Semantic Recovery (BoW cosine similarity)
# ---------------------------------------------------------------------------

def _cosine(text_a: str, text_b: str) -> float:
    """BoW cosine similarity between two texts. Returns 0.0 if either is empty."""
    vec_a = Counter(_tokenize(text_a))
    vec_b = Counter(_tokenize(text_b))
    if not vec_a or not vec_b:
        return 0.0
    vocab = set(vec_a) | set(vec_b)
    dot   = sum(vec_a.get(w, 0) * vec_b.get(w, 0) for w in vocab)
    mag_a = sqrt(sum(v * v for v in vec_a.values()))
    mag_b = sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def compute_sr(output_text: str) -> float:
    """
    SR = max cosine similarity between output_text and any reference corpus entry.
    A high score means the output vocabulary closely reconstructs crown-jewel data.
    """
    if not output_text.strip():
        return 0.0
    return max(_cosine(ref, output_text) for ref in REFERENCE_CORPUS)


# ---------------------------------------------------------------------------
# SSR — Sensitive-String Recovery (regex pattern scan)
# ---------------------------------------------------------------------------

def compute_ssr(output_text: str) -> dict[str, Any]:
    """
    Scan output_text for all canonical sensitive-data patterns.

    Returns:
        ssr_score   : float [0, 1]  — matched_types / TOTAL_PATTERNS
        matches     : dict[pattern_name -> list[str]]
    """
    matches: dict[str, list[str]] = {}
    for name, pattern in SSR_PATTERNS.items():
        found = re.findall(pattern, output_text)
        if found:
            matches[name] = found
    return {
        "ssr_score": len(matches) / TOTAL_PATTERNS,
        "matches":   matches,
    }


# ---------------------------------------------------------------------------
# RVS — composite score and enforcement decision
# ---------------------------------------------------------------------------

def evaluate_rvs(output_text: str) -> dict[str, Any]:
    """
    Run the full RVS gate on a tool output string.

    Returns:
        sr_score    : float
        ssr_score   : float
        ssr_matches : dict
        rvs_score   : float
        decision    : 'RVS_PASS' | 'RVS_WARN' | 'QUARANTINE'
        reason      : str | None
    """
    sr_score  = compute_sr(output_text)
    ssr_result = compute_ssr(output_text)
    ssr_score  = ssr_result["ssr_score"]
    rvs_score  = RVS_WEIGHT_SR * sr_score + RVS_WEIGHT_SSR * ssr_score

    if rvs_score >= RVS_QUARANTINE_THRESHOLD:
        decision = "QUARANTINE"
        reason   = (
            f"RVS={rvs_score:.4f} >= quarantine_threshold={RVS_QUARANTINE_THRESHOLD} "
            f"(SR={sr_score:.4f}, SSR={ssr_score:.4f})"
        )
    elif rvs_score >= RVS_WARN_THRESHOLD:
        decision = "RVS_WARN"
        reason   = (
            f"RVS={rvs_score:.4f} >= warn_threshold={RVS_WARN_THRESHOLD} "
            f"(SR={sr_score:.4f}, SSR={ssr_score:.4f})"
        )
    else:
        decision = "RVS_PASS"
        reason   = None

    return {
        "sr_score":    sr_score,
        "ssr_score":   ssr_score,
        "ssr_matches": ssr_result["matches"],
        "rvs_score":   rvs_score,
        "decision":    decision,
        "reason":      reason,
    }
