# Threat Model: Multi-Tenant LLM Accelerators

This document formally maps the Identity-Bound Cross-Plane Security Control architecture to the existing threat literature and explicitly outlines the limitations of the evaluation.

## 1. Hardware Remanence & Data Exfiltration
**Reference Literature**: *LeftoverLocals (2024)*

LeftoverLocals demonstrated that VRAM structures on specific consumer GPUs (Apple, AMD, Qualcomm) could be read by a secondary process if the memory was not securely zeroed by the driver upon context switch.

**Our Architecture's Stance:**
Phase 1 empirical testing on an NVIDIA RTX 3050 Laptop GPU demonstrated a Lexical Recovery (LR) rate of 0.0%, confirming that patched NVIDIA drivers perform implicit page-zeroing (`cudaFree`). However, because hardware architectures and driver versions are heterogeneous across cloud providers, our architecture **does not assume** this protection. 

The Admission Gate (Phase 3) enforces a *Verifiable Sanitization* pass whenever the prior tenant's behavioural anomaly (CPSI) breaches the required threshold, effectively treating the driver-level threat as conditional and neutralizing it dynamically.

## 2. Prompt-Driven Privilege Escalation
**Reference Literature**: *InjecAgent (2023)*

InjecAgent highlights how LLMs can be tricked via prompt injection into executing malicious API/tool calls that the underlying user did not authorize.

**Our Architecture's Stance:**
The Phase 2 Agent Divergence (CDDI) engine mitigates this by enforcing strict identity bounds at the API gateway layer:
- $D_{scope}$: Binary tracking of cross-tenant namespace requests.
- $D_{privilege}$: Ordinal normalization of requested action against granted token.
- $D_{identity}$: Cross-tenant target isolation.

By binding the agent's identity to the API payload, we strip the LLM's autonomy to pivot across scopes, limiting attacks to the tenant's own isolated environment.

## 3. Resource Amplification & Denial of Service
**Reference Literature**: *ScopeGate (2024)*

Resource exhaustion attacks via malformed prompts can tie up expensive GPU resources (e.g., generating infinite loops or excessive context window queries).

**Our Architecture's Stance:**
The Pre-Execution Resource Anomaly Index (PERAI) tracks the predicted compute cost ($\hat{C}$) against empirical actuals ($C_{actual}$). It enforces both a strict per-call limit and a rolling session budget. In Phase 2 trials, PERAI maintained a 95.03% estimation accuracy.

---

## 4. Limitations and External Validity

The following strict limitations govern the interpretation of this project's empirical results:

### Hardware Limitation
The physical remanence experiment was performed strictly on an NVIDIA RTX 3050 Laptop GPU and yielded zero observed Lexical Recovery.

### GPU-Family and Driver Limitation
The remanence results obtained on the RTX 3050 do not generalize to all accelerators. Remanence behavior heavily depends on specific driver behavior, firmware versions, and architectural isolation configurations.

### Simulated-Control Limitation
Because physical remanence on the evaluation hardware was identically zero, the effectiveness of the *sanitization* routines (e.g., VRAM flushing) in Phase 3 is evaluated via simulated control-flow verification logic, rather than a secondary physical recovery demonstration.

### Synthetic-Data Limitation
The internal cross-plane evaluation relies on synthetic dataset generation (1,500 continuous evaluation cases, 500 tenant-transition cases). These results provide evidence of continuous discrimination boundaries but do not establish or predict production incident rates.

### Benchmark Limitation
AgentDojo and InjecAgent provide valuable external stress testing, but these public benchmarks do not cover the entire multidimensional deployment space. Furthermore, metrics on these benchmarks do not guarantee identical outcomes on differing populations.

### Model Dependence
Agent behavioral trajectories and tool-call sequences depend inherently on the underlying foundation model and its specific inference configuration.

### Observability Limitation
External benchmark environments (such as remote AgentDojo executions) may not expose all infrastructure telemetry required by Full CPSI (e.g., GPU remanence). In such cases, infrastructure components are explicitly tagged as non-observable.

### Security-Boundary Limitation
The architecture assumes that the core orchestrator, container execution runtime, and the API gateway itself remain fundamentally uncompromised. Root-level breaches of the host hypervisor bypass this tenant-level enforcement.

### Non-Goals
This project explicitly excludes:
- KV-cache leakage replication and defenses.
- Persistent state attacks via PostgreSQL/vector-store mechanisms.
- Hardware-level side channels such as GPUBreach or Rowhammer replication.
