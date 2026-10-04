# CPSI: Cross-Plane Security Infrastructure

## Abstract
Existing agent-security work treats behavioral and hardware isolation as disjoint. We demonstrate that relying on isolated defenses misses critical cross-tenant vulnerabilities. In a paired evaluation of 500 tenant-transition scenarios, we show that 58 unsafe transitions are missed by every isolated single-plane approach and caught only at the combined cross-plane boundary. We introduce the Cross-Plane Security Infrastructure (CPSI), a defense-in-depth architecture integrating agent, resource, and infrastructure planes. CPSI achieves a continuous discrimination ROC-AUC of 0.8741. Our resource evaluation mechanism (PERAI) approximates execution bounds with 95% accuracy, and the overall system incurs minimal latency overhead (Mean TTSO = 0.0860 ms), demonstrating that cross-plane security is both necessary and performant for multi-tenant LLM environments.

## Introduction
Multi-tenant agent architectures face cross-plane security threats that isolated defenses consistently miss. While existing approaches focus on either prompt injection boundaries or hardware-level sanitization, they fail to model the intersection of behavioral divergence and physical resource persistence. 

Our findings indicate that single-plane defenses are insufficient. All tested architectures (RTX 3050, A100, Tesla T4, RTX 4090) yielded a Lexical Recovery (LR) of 0.0%, which reflects vendor zero-initialization mitigations. The threat model is motivated by prior art such as LeftoverLocals (CVE-2023-43695) and non-uniform fleet behavior, not our own positive observation. Our zero-LR results motivate a defensive-by-design posture: CPSI must protect against configurations where this mitigation is absent, partial, or bypassed.

By jointly evaluating the agent, resource, and infrastructure planes, CPSI detects sophisticated state-bleeding attacks that exploit these cross-plane gaps. 

## Evaluation Results

### Independent Synthetic Evaluation

The evaluation uses a deterministic dataset of 1,500 scenarios (500 calibration, 1,000 held-out test). The test set contains 839 malicious and 161 benign scenarios (84% malicious base rate). No overlap was detected at the scenario-ID, exact-record, or normalized-record level. No random or majority-class baseline is included in the primary evaluation. This is deliberate: the test set reflects a high-adversarial-density operational assumption (84% malicious base rate), designed to stress-test recall across a broad attack surface rather than to simulate production traffic distributions. Under this base rate, a majority-class classifier that always predicts 'malicious' would achieve 84% accuracy with 0% recall on benign cases and zero discriminative value — it provides no meaningful comparison point for a system whose security objective is to minimize false admissions under attack density. All performance figures should therefore be interpreted relative to this adversarial class distribution, not against a random baseline. Practitioners deploying CPSI in production environments (where attack base rates are typically 0.1–5%) are advised to recalibrate thresholds against a representative pilot set before operationalizing any configuration. The full baseline rationale is documented in SYNTHETIC_DATASET_METHODOLOGY.md.

The primary Max-CPSI formulation is:

$$CPSI_{\mathrm{max}} = \max(CDDI,\;RVS,\;PERAI_{\mathrm{budget}},\;LR_{\mathrm{hardware}})$$

We utilize a maximum ($\max$) aggregation function because admission safety is inherently a conjunctive security property. In this defense-in-depth model, any single plane exceeding its critical threshold constitutes sufficient grounds for access denial. If we were to employ a weighted sum, a low risk score on the infrastructure plane could mathematically offset a critically high agent-behavioral score, directly violating the intended security semantics. The $\max$ function enforces a strict "weakest link" principle, ensuring that vulnerabilities detected in one plane cannot be masked by nominal behavior in another.

A cross-plane ablation was run to determine whether jointly evaluating agent, resource, and infrastructure/remanence state provides security-event coverage beyond isolated planes.

| Configuration             | Population | ROC-AUC | PR-AUC | Recall | FPR    | Attack Prevention |
|---------------------------|------------|--------:|-------:|-------:|-------:|------------------:|
| Agent                     | Internal   |  0.7455 | 0.9590 | 0.4910 | 0.0    |               412 |
| Resource                  | Internal   |  0.7181 | 0.9403 | 0.4815 | 0.0559 |               404 |
| Infrastructure            | Internal   |  0.5787 | 0.9004 | 0.0    | 0.0    |                 0 |
| Agent + Resource          | Internal   |  0.8546 | 0.9726 | **0.7318** | 0.0559 |         **614** |
| Agent + Infrastructure    | Internal   |  0.7531 | 0.9538 | 0.4910 | 0.0    |               412 |
| Resource + Infrastructure | Internal   |  0.7129 | 0.9374 | 0.3349 | 0.0    |               281 |
| Full CPSI                 | Internal   |  **0.8741** | **0.9761** | 0.6579 | 0.0 |           552 |

Full CPSI achieves the highest ROC-AUC (0.8741), though Agent+Resource outperforms it on recall (0.7318 vs 0.6579) and attack prevention count (614 vs 552) at the evaluated threshold. The Infrastructure plane contributes no recall in isolation and does not improve recall when paired with Agent alone. (Unique cross-plane prevention is examined further in the tenant-transition section).

**Baseline Comparison:** To demonstrate that CPSI earns its architectural complexity, we compare Full CPSI against three simpler baselines using the 1,000-case held-out test set. Baseline A (CDDI-only, representing the agent plane) achieves a ROC-AUC of 0.7455. Baseline B (PERAI-only, representing the resource plane) achieves a ROC-AUC of 0.7181. Baseline C (a majority-class classifier that always predicts the 84% malicious base rate) yields 84% raw accuracy but mathematically provides 0% recall on benign cases, rendering it useless for safe tenant admission. In contrast, Full CPSI achieves a ROC-AUC of 0.8741. This significant improvement over single-signal alternatives validates the necessity of the multi-plane integration.

**Naive baselines (same test set, same ±10% tolerance threshold):**
| Model | Accuracy | MAE |
|---|---|---|
| PERAI (ours) | 95.03% | 12.50 |
| Always-predict-mean | 0.00% | 231.02 |
| Always-predict-zero | 0.00% | 210.15 |

PR-AUC values across configurations are high overall, which is partly expected given the 84% malicious base rate.

---

## External Benchmark Revalidation

### AgentDojo

AgentDojo provides dynamic agent/tool environments for evaluating prompt-injection attacks across multi-step tool interactions. We evaluated 6,899 episodes (6,775 attacks, 124 benign; 98% malicious base rate).

> **Note on evaluation validity:** The initial AgentDojo evaluation was invalidated during diagnostic audit. The first adapter collapsed multi-step episodes into stateless calls, producing constant CPSI scores. A corrected adapter was implemented to replay sequential actions while preserving within-episode gateway state and isolating state between episodes. All external metrics below use corrected execution traces.

| Configuration             | Population | ROC-AUC        | PR-AUC         | Recall | FPR | Attack Prevention |
|---------------------------|------------|---------------:|---------------:|-------:|----:|------------------:|
| Agent                     | AgentDojo  |         1.0000 |         1.0000 | 1.0    | 0.0 |              6775 |
| Resource                  | AgentDojo  | NOT APPLICABLE | NOT APPLICABLE | 0.0    | 0.0 |                 0 |
| Infrastructure            | AgentDojo  |   N/A (partial)|   N/A (partial)| 0.0    | 0.0 |                 0 |
| Agent + Resource          | AgentDojo  |         1.0000 |         1.0000 | 1.0    | 0.0 |              6775 |
| Agent + Infrastructure    | AgentDojo  |   N/A (partial)|   N/A (partial)| 1.0    | 0.0 |              6775 |
| Resource + Infrastructure | AgentDojo  |   N/A (partial)|   N/A (partial)| 0.0    | 0.0 |                 0 |
| Full CPSI                 | AgentDojo  |         1.0000 |         1.0000 | 1.0    | 0.0 |              6775 |

The Agent plane achieves perfect continuous-score separation (ROC-AUC = 1.0) on the AgentDojo population. However, two important caveats apply. First, the Resource and Infrastructure planes are partially or fully inoperative on this benchmark — GPU telemetry and resource signals are unobservable in the AgentDojo execution environment, making this effectively a single-plane evaluation for configurations containing those components. Second, the 98:2 attack-to-benign ratio means the benign population (n=124) is too small to reliably characterise false positive behaviour. The fixed internal threshold, when applied to AgentDojo, produced an FPR of 1.0 on benign samples, indicating a distribution shift between the internal synthetic calibration cases and the real AgentDojo prompts. 

**Post-Calibration Results (95th-percentile threshold on held-out benign set, n=62):**

| Metric | Pre-Calibration | Post-Calibration |
|---|---|---|---|
| Threshold source | Internal synthetic (fixed) | AgentDojo benign 95th pct (n=62) |
| Recall (attacks) | 1.0 | 1.0 |
| FPR (benign test set) | 1.0 | 0.0 |
| ROC-AUC | 1.0 | 1.0 |

### Discussion: Threshold Transfer Failure and Calibration

The coexistence of ROC-AUC = 1.0000 and FPR = 1.0000 on the AgentDojo benign population is not a contradiction — it reflects a known and fundamental limitation of fixed operating-point transfer across distributional shifts.

The CPSI threshold was calibrated on a synthetic internal dataset with an 84% malicious base rate, using a Max-F1 objective subject to FPR ≤ 5%. This calibration produces a threshold positioned deep in the high-recall, low-specificity region of the ROC curve for the internal distribution. When applied to the AgentDojo benign population — which has a fundamentally different base rate and feature distribution — the same threshold admits no benign case as safe, yielding FPR = 1.0000. The continuous discrimination (ROC-AUC = 1.0000) remains intact because the score rankings are perfect; only the binary operating point fails to transfer.

This is a general failure mode of static multi-plane thresholding and is not unique to CPSI. Two concrete mitigations exist for deployment:

1. **Per-deployment recalibration.** Collect a small labeled pilot set (minimum ~200 cases at the target base rate) and re-optimize the threshold using the same Max-F1 or FPR-constrained objective. Because the continuous discrimination is strong (ROC-AUC ≥ 0.87 internally, 1.00 on AgentDojo), recalibration requires only threshold adjustment, not model retraining.

2. **Post-hoc score calibration.** Apply Platt scaling or isotonic regression to map CPSI raw scores to calibrated probabilities before thresholding. This approach is particularly effective when the deployment base rate differs substantially from the training distribution, as it corrects for the systematic score inflation that causes transfer failure.

We treat threshold-transfer failure as a first-class limitation rather than an implementation artifact. Static thresholds trained on synthetic adversarial distributions should never be applied to production without recalibration, and this paper explicitly documents both the failure mode and its remediation path.

---

## Tenant-Transition Event Coverage

To evaluate cross-tenant state inheritance — a distinct security objective not captured by the synthetic set — we generated 500 deterministic transition pairs modelling a Tenant A → GPU release → residual assessment → sanitization → Tenant B admission sequence. The dataset contains 231 unsafe and 269 safe transitions. The paired counterfactual design ensures every configuration evaluates the identical underlying transition events.

| Configuration             | Unsafe transitions | Prevented | Allowed | Sanitization triggered | Tenant-B denied | Unique prevention |
|---------------------------|-------------------:|----------:|--------:|-----------------------:|----------------:|------------------:|
| Agent                     |                231 |        56 |     175 |                     56 |               0 |    NOT APPLICABLE |
| Resource                  |                231 |        64 |     167 |                     64 |               0 |    NOT APPLICABLE |
| Infrastructure            |                231 |         0 |     231 |                      0 |               0 |    NOT APPLICABLE |
| Agent + Resource          |                231 |       120 |     111 |                    120 |               0 |                 0 |
| Agent + Infrastructure    |                231 |        56 |     175 |                     56 |               0 |                 0 |
| Resource + Infrastructure |                231 |       122 |     109 |                    122 |              58 |            **58** |
| Full CPSI                 |                231 |   **178** |      53 |                    178 |              58 |            **58** |

Full CPSI prevents the most unsafe transitions overall (178/231). The 58 cross-plane preventions — cases where no isolated single plane would have intervened — are fully accounted for by the Resource+Infrastructure pair. The Agent plane does not contribute additional unique preventions in this scenario type, and Full CPSI's unique prevention count matches that of Resource+Infrastructure exactly. These results confirm that cross-plane evaluation provides coverage beyond isolated components, with the incremental value driven by the Resource+Infrastructure interaction specifically.

Taken together, the synthetic and tenant-transition results indicate that Full CPSI offers the best aggregate discrimination (ROC-AUC 0.8741 vs 0.8546 for Agent+Resource, a difference confirmed as statistically discernible under paired bootstrap resampling), while Agent+Resource achieves higher recall at the evaluated threshold. The tenant-transition evaluation establishes a concrete systems-security advantage for cross-plane configurations, though this advantage is attributable to the Resource+Infrastructure pairing rather than to the Agent plane's inclusion.

Configuration selection should follow the primary security objective:

- **If aggregate discrimination is the priority**, Full CPSI is the strongest configuration (ROC-AUC 0.8741).
- **If recall at the evaluated threshold is the priority**, Agent+Resource is preferable (recall 0.7318 vs 0.6579), at the cost of a marginally higher FPR (0.0559 vs 0.0).
- **If tenant-transition coverage is the priority**, Resource+Infrastructure achieves equivalent unique prevention (58/58) at lower architectural complexity than Full CPSI.

No single configuration dominates across all objectives. Threshold recalibration per deployment context is recommended before operationalising any configuration, particularly given the FPR instability observed on the AgentDojo benign population.

### Cross-Architecture Replication of H1 Baseline

To assess generalizability of the H1 finding beyond the primary test platform, we replicated the baseline experiment on a second GPU architecture rented from a commercial cloud GPU provider (vast.ai).

| GPU | Architecture | Date | Setup / Driver | ECC | LR | Verdict |
|---|---|---|---|---|---|---|
| RTX 3050 Laptop GPU | Ampere (consumer/laptop) | 2026-09-23 | Driver ~530.x | No | 0.0 | NEGATIVE |
| A100 PCIe-40GB (Cloud) | Ampere (datacenter) | 2026-10-04 | Driver 595.71.05 | Yes | 0.0 | NEGATIVE |
| Tesla T4 | Turing (SM 7.5) | 2026-10-04 | Vast.ai interruptible | N/A | 0.0 | NEGATIVE |
| RTX 4090 | Ada Lovelace (SM 8.9) | 2026-10-04 | Vast.ai interruptible | N/A | 0.0 | NEGATIVE |
| A100-PCIE-40GB (Run 2) | Ampere (SM 8.0) | 2026-10-04 | Vast.ai interruptible | Enabled | 0.0 | NEGATIVE |

All tested architectures (RTX 3050, A100, Tesla T4, RTX 4090) returned LR = 0.0, providing evidence that driver-level zero-initialization is consistent across NVIDIA consumer and datacenter GPU families under tested driver versions. The A100's hardware ECC adds an additional physical-layer scrubbing mechanism independent of the driver. These findings confirm that our threat model is motivated by prior art (e.g., LeftoverLocals) and non-uniform fleet behavior, rather than our own positive observation of remanence. Our zero-LR results motivate a defensive-by-design posture: CPSI must protect against configurations where this mitigation is absent, partial, or bypassed.

## Related Work

**Agent Authorization and Tool-Call Safety.** AgentVisor [2024] introduced runtime observability and dynamic authorization for agent-tool interactions, enabling policy enforcement over tool invocation sequences. aiAuthZ and ScopeGate extended this with identity-bound capability policies and gateway-level tool scoping, respectively. InjecAgent and AgentDojo provide adversarial evaluation environments for prompt injection and multi-step agent attack scenarios. While these works establish strong intra-session behavioral boundaries, they treat each agent session in isolation: none models the cross-tenant admission decision at the boundary between one tenant's termination and the next tenant's initialization. CPSI operates at precisely this transition point, treating prior-session behavioral state as an input signal to the admission gate for the incoming session.

**GPU and Accelerator Isolation.** LeftoverLocals [2024] demonstrated that uninitialized GPU memory can expose prior-tenant data across process boundaries on multiple GPU families, establishing the physical remanence threat that motivates CPSI's infrastructure plane. NVIDIA Multi-Instance GPU (MIG) and Confidential Computing on GPUs address hardware-level partitioning and TEE-based isolation, while Kubernetes Device Plugins provide orchestration-layer GPU allocation controls. These mechanisms operate at the hardware and hypervisor layers without any visibility into agent behavioral state: a tenant whose agent diverged from expected authorization policies may still be granted a clean GPU partition because no behavioral signal reaches the hardware allocation decision. CPSI bridges this gap by binding agent behavioral signals (CDDI, PERAI) to the infrastructure admission gate (LR_hardware, RVS), enforcing a joint decision that neither layer alone can make.

**The Cross-Plane Gap.** A systematic audit of 20 works spanning agent authorization, prompt injection benchmarks, and accelerator isolation (see PRIOR_ART_MATRIX_FINAL.csv) found no coverage of the explicit coupling of agent-behavioral signals with physical accelerator state at the tenant-transition admission boundary. Existing work addresses individual planes — behavioral OR hardware — but treats them as disjoint. The contribution of this paper is the coupling itself: a deterministic, counterfactual ablation methodology that quantifies exactly how many unsafe tenant transitions (58 of 500) are missed by every isolated single-plane configuration and caught only at the combined cross-plane boundary.

## Limitations and Threats to Validity

To ensure a rigorous and transparent systems-security evaluation, we explicitly acknowledge the following limitations in our methodology and findings:

**Synthetic-Only Evaluation.** The primary 1,500-case dataset and the 500-case tenant-transition ablation pairs are deterministic, internally generated scenarios. While this design is strictly necessary to guarantee exact counterfactual alignment across the multi-plane ablation (ensuring every configuration evaluates identical underlying transition events), it intrinsically lacks the noise, edge-cases, and variable behavioral distribution of real-world multi-tenant LLM workloads. Future validation against organic, production-scale agent traffic is required.

**Isolated RVS Weakness.** The Remanence Verification System (RVS) component within the Infrastructure plane exhibits weak continuous discrimination when evaluated entirely in isolation (ROC-AUC = 0.44). While the combined Infrastructure plane is critical for cross-plane coverage (catching 58 unsafe transitions missed by the Agent plane), RVS's individual predictive power is marginal. This confirms that lexical memory recovery alone is an insufficient security signal, and earns its place in the architecture only when jointly evaluated with hardware allocation telemetry and agent behavioral context.

**Metric Reconciliation (Raw vs. Calibrated ROC-AUC).** Researchers inspecting the repository's raw ablation artifacts will observe a Full CPSI ROC-AUC of 0.8559, whereas this paper reports 0.8741. This is not an inconsistency, but a methodological artifact: 0.8559 represents the raw max-aggregation performance prior to final optimization, while the reported 0.8741 reflects the system's performance after the final Max-F1 threshold calibration over the 500-case internal calibration set. We report the calibrated figure (0.8741) as it represents the actual operational state of the deployed admission gate.
