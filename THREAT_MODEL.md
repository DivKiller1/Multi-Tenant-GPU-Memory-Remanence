# Threat Model: Multi-Tenant LLM Accelerators

This document formally maps the Identity-Bound Cross-Plane Security Control architecture to the existing threat literature.

## 1. Hardware Remanence & Data Exfiltration
**Reference Literature**: *LeftoverLocals (2024)*

LeftoverLocals demonstrated that VRAM structures on specific consumer GPUs (Apple, AMD, Qualcomm) could be read by a secondary process if the memory was not securely zeroed by the driver upon context switch.

**Our Architecture's Stance:**
Phase 1 empirical testing on an NVIDIA RTX 3050 Laptop GPU demonstrated a Lexical Recovery (LR) rate of 0.0%, confirming that patched NVIDIA drivers perform implicit page-zeroing (`cudaFree`). However, because hardware architectures and driver versions are heterogeneous across cloud providers, our architecture **does not assume** this protection. 

The Admission Gate (Phase 3) enforces a *Verifiable Sanitization* pass whenever the prior tenant's behavioural anomaly (CPSI) breaches the threshold ($\theta \ge 0.40$), effectively treating the driver-level threat as conditional and neutralizing it dynamically.

## 2. Prompt-Driven Privilege Escalation
**Reference Literature**: *InjecAgent (2023)*

InjecAgent highlights how LLMs can be tricked via prompt injection into executing malicious API/tool calls that the underlying user did not authorize.

**Our Architecture's Stance:**
The Phase 2 Agent Divergence (AADV) engine mitigates this by enforcing three strict identity bounds at the API gateway layer:
- $D_{scope}$: Binary blocking of cross-tenant namespace requests.
- $D_{privilege}$: Ordinal normalization of requested action against granted token.
- $D_{identity}$: Cross-tenant target isolation.

By binding the agent's identity to the API payload, we strip the LLM's autonomy to pivot across scopes, limiting InjecAgent-style attacks to the tenant's own isolated environment.

## 3. Resource Amplification & Denial of Service
**Reference Literature**: *ScopeGate (2024)*

Resource exhaustion attacks via malformed prompts can tie up expensive GPU resources (e.g., generating infinite loops or excessive context window queries).

**Our Architecture's Stance:**
The Pre-Execution Resource Anomaly Index (PERAI) tracks the predicted compute cost ($\hat{C}$) against empirical actuals ($C_{actual}$). It enforces both a strict per-call hard limit and a rolling session budget. In Phase 2 trials, PERAI maintained a 95.03% estimation accuracy, successfully blocking sequence anomalies designed to tie up resources (e.g., $TC-009$ and $TC-011$).
