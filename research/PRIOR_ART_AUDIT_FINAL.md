# CPSI Final Prior-Art and Novelty Audit

**Audit Date:** 2026-09-24

## 1. Literature Search Freeze
A final systematic search of the relevant agent-security, AI authorization, and hardware isolation literature was performed spanning 2020 through 2026-09-24. 20 distinct highly relevant works were analyzed across three main domains:
1. Agent/tool authorization (e.g., AgentVisor, aiAuthZ, ScopeGate)
2. Prompt injection and agent benchmarks (e.g., InjecAgent, AgentDojo, TS-Bench)
3. GPU/accelerator isolation and remanence (e.g., LeftoverLocals, MIG, Kubernetes Device Plugins)

The explicit mapping of these 20 works across 10 security capabilities is preserved in `PRIOR_ART_MATRIX_FINAL.csv`.

## 2. Empirically Verified Gap
The systematic audit identifies a distinct methodological gap: **NO DIRECT COVERAGE FOUND** in the existing literature for the explicit coupling of agent-behavioral signals (identity, sequence, tool usage) with physical accelerator state (remanence, GPU allocation) specifically enforced at the tenant-transition admission boundary. 

Existing literature heavily addresses individual agent authorization (e.g., AgentVisor) OR hardware-level isolation (e.g., LeftoverLocals/MIG), but treats them as entirely disjoint planes.

## 3. Novelty Claim Boundary
The final paper must adhere strictly to this verifiable boundary.
**Unsupported Claims to Avoid:**
- Do not claim CPSI is the "first agent firewall".
- Do not claim CPSI is the "first identity-bound agent authorization".
- Do not claim CPSI is the "first GPU remanence defense".

**Supported Novelty Statement:**
> "Existing work predominantly addresses individual agent authorization, tool-call safety, prompt injection, or accelerator isolation. The evaluated contribution here is the explicit coupling of these signals at the tenant-transition boundary, together with a counterfactual ablation that measures security events prevented only by the combined cross-plane controller."
