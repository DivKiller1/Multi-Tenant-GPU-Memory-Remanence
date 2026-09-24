# PROJECT ARCHITECTURE — Identity-Bound Cross-Plane Security Control
## Multi-Tenant LLM Accelerator Security System
> IMMUTABLE — Do not edit to match failed tests. Architecture != Result.
> Last structural revision: Phase 1 initialization.

---

## 1. System Boundaries

```
+-------------------------------------------------------------+
|                    SEMANTIC LAYER                           |
|  LLM Agent  -->  Authorization Gateway  -->  Tool Executor  |
|  (Identity / Tenant / Scope / Behavior telemetry)          |
+-----------------------------+-------------------------------+
                              |  Identity Binding
+-----------------------------v-------------------------------+
|                   CROSS-PLANE CONTROL                       |
|  Agent State  <--->  Security Evaluator  <--->  GPU State   |
|  (CPSI computation, enforcement decisions)                  |
+-----------------------------+-------------------------------+
                              |  Lifecycle Control
+-----------------------------v-------------------------------+
|                 INFRASTRUCTURE LAYER                        |
|  GPU Allocator  -->  Remanence Monitor  -->  Sanitizer      |
|  (RVS, MTSNR, tenant admission gating)                     |
+-------------------------------------------------------------+
```

### Tenant Transition Lifecycle
```
Tenant A execution
    |  release
    v
Residual-state assessment  (RVS measured)
    |  if RVS < theta
    v
Sanitization
    |
    v
Sanitization verification  (RVS re-measured)
    |  if verified
    v
Tenant B admission
```

---

## 2. Core Security Hypotheses

| # | Hypothesis | Validated By |
|---|-----------|-------------|
| H1 | Measurable GPU VRAM remanence exists across OS-process boundaries on RTX 3050 | Phase 1 experiment |
| H2 | Tenant-attributable information is lexically/semantically recoverable post-release | RVS metric (Phase 1-2) |
| H3 | Agent authorization divergence is continuously measurable via AADV/CDDI | Phase 2 experiment |
| H4 | Pre-execution resource amplification is estimable via PERAI | Phase 2 experiment |
| H5 | Semantic + infrastructure signals can be combined into actionable CPSI | Phase 3 experiment |
| H6 | Verified sanitization measurably reduces RVS below admission threshold theta | Phase 3 experiment |
| H7 | Cross-plane control overhead remains operationally acceptable | Phase 4 evaluation |

---

## 3. Mathematical Formulations

### 3.1 Residual Vulnerability Score (RVS)
```
RVS(t) = alpha * LR(t) + beta * SR(t) + gamma * SSR(t)

  LR(t)  = Lexical Recovery      -- byte-pattern match ratio in raw tensor
  SR(t)  = Semantic Recovery     -- embedding cosine similarity to original payload
  SSR(t) = Sensitive-String Rec. -- regex/NER detection of PII/secrets in residual
  alpha + beta + gamma = 1   (weights TBD by experimental calibration)

Phase 1 measures LR(t) only. SR and SSR are Phase 2+.
```

### 3.2 Mean Time to Safe-Noise Ratio (MTSNR)
```
MTSNR = min{ t : RVS(t) < theta }

  theta = admission threshold (experimental, not assumed)
  Measures persistence of recoverable information over time/sanitization passes.
```

### 3.3 Agent Authorization Divergence Vector (AADV)
```
AADV = (scope_delta, privilege_delta, identity_distance,
        cross_tenant_flag, tool_sequence_anomaly, recurrence_count)

CDDI (Continuous Divergence Detection Index) = weighted norm of AADV
```

### 3.4 Pre-Execution Resource Amplification Index (PERAI)
```
PERAI = C_hat / Q_remaining

  C_hat       = pre-execution cost estimate (tokens, VRAM, latency)
  Q_remaining = remaining quota for tenant
  Validity requires: measure C_hat vs C_actual before trusting estimator
```

### 3.5 Cross-Plane Security Index (CPSI)
```
CPSI = F(AgentState, GPUState, RemanenceState)

  AgentState     = f(CDDI, AADV, session history)
  GPUState       = f(allocation, utilization anomaly)
  RemanenceState = f(RVS, MTSNR)

  F is a research hypothesis -- must be experimentally determined.
  Do NOT assume F is a simple linear combination without validation.
```

---

## 4. Four-Phase Execution Plan

| Phase | Title | Objective | Status |
|-------|-------|-----------|--------|
| 1 | GPU Remanence Baseline | Prove/disprove physical VRAM leakage across OS-process boundaries. Measure LR(t). | VALIDATED (LR=0.0, theta=0, driver zeroing confirmed) |
| 2 | Agent Divergence Measurement | Implement AADV/CDDI pipeline. Measure PERAI estimator accuracy. Extend RVS with SR/SSR. | VALIDATED |
| 3 | Cross-Plane Binding & Control | Implement CPSI. Bind agent identity to GPU lifecycle. Enforce admission gating. | VALIDATED |
| 4 | Evaluation & Paper Metrics | End-to-end overhead, sanitization effectiveness, detection accuracy, threat modeling. | VALIDATED |

---

## 5. Monorepo Structure

```
MAJOR PROJECT-1/
+-- PROJECT_ARCHITECTURE.md       (immutable)
+-- PROGRESS_TRACKER.md
+-- requirements.txt
+-- experiments/
|   +-- gpu-baseline/             (Phase 1 -- VALIDATED)
|       +-- tenant_a_victim.py
|       +-- tenant_b_probe.py
|       +-- run_baseline.sh
+-- gateway/                      (Phase 2 -- IN_PROGRESS)
    +-- stub_agent.py             (simulates LLM tool call generation)
    +-- tool_gateway.py           (AADV enforcement: D_scope, D_privilege)
```

Phase 3+ directories (not yet created -- remain TODO):
```
+-- crossplane/                   (Phase 3)
+-- evaluation/                   (Phase 4)
```

---

## 6. Target Hardware
- GPU: NVIDIA RTX 3050 Laptop GPU (bare metal)
- Framework: PyTorch (CUDA backend)
- Key constraint: Allocator bypass required.
  Use PYTORCH_NO_CUDA_MEMORY_CACHING=1 + torch.cuda.empty_cache() + torch.empty() (uninitialized).

### 6.1 Empirical Baseline (Phase 1 Result — VALIDATED)
```
Hardware : NVIDIA GeForce RTX 3050 Laptop GPU
Driver   : Current NVIDIA driver (driver-level page zeroing active)
Result   : Mean LR = 0.0%  across 3 independent OS-process-boundary trials
           (0 of 268,435,456 bytes recovered per run)
Threshold: theta = 0  on this hardware configuration

Interpretation:
  The RTX 3050 Laptop GPU driver zeros VRAM pages on cudaFree BEFORE returning
  them to the pool. This is a driver-level sanitization guarantee.

Threat-model shift:
  Remanence leakage is HARDWARE- and DRIVER-CONDITIONAL.
  LeftoverLocals (2024) confirmed leakage on Apple/AMD/Qualcomm GPUs.
  Our system's runtime admission gate remains strictly necessary because:
    (a) Heterogeneous multi-tenant fleets cannot guarantee driver compliance.
    (b) Driver versions change -- a future regression or legacy deployment
        may remove this guarantee.
    (c) Absence of leakage on RTX 3050 does NOT imply absence across all
        production accelerator classes.
  The cross-plane verification gate proves the condition rather than
  assuming it -- which is the correct engineering posture regardless of
  the baseline LR value.
```

---

## 7. What Is NOT This Project (Scope Guard)

| Out of Scope (Phase 2+)       | Reason         |
|-------------------------------|----------------|
| FastAPI / REST gateway        | Phase 2+       |
| Kubernetes YAMLs              | Phase 3+       |
| Dockerfiles                   | Phase 2+       |
| Databases / vector stores     | Phase 2+       |
| KV-cache leakage experiments  | Separate expt  |
| GPU Rowhammer replication     | Different class|

---
Source: Research Manifesto -- "Identity-Bound Cross-Plane Security Control for Multi-Tenant LLM Accelerators"
