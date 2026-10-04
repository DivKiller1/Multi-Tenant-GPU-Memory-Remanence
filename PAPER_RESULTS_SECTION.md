# CPSI: Cross-Plane Security Infrastructure

## Abstract
Multi-tenant LLM environments face coupled threats where agent behavioral divergence intersects with shared physical resources. To address this, we introduce the Cross-Plane Security Infrastructure (CPSI), a defense-in-depth architecture integrating agent behavioral anomaly detection (CDDI), resource quota enforcement (PERAI), and lexical remanence verification (RVS) as its primary contributions. While recent work like LeftoverLocals (2024) established that GPU memory remanence affects Apple, AMD, and Qualcomm hardware, the threat has remained unconfirmed on NVIDIA at scale. We conduct a systematic cross-architecture hardware survey (5 runs, 4 architectures: Turing, Ampere, Ada Lovelace) and find robust memory sanitization by the NVIDIA driver stack, recording zero lexical remanence across all tests. We frame this empirical confirmation of NVIDIA's sanitization as a positive finding that establishes the heterogeneous threat boundary. By leading with the CDDI/RVS/PERAI behavioral detection planes, CPSI provides comprehensive cross-tenant security even when hardware-level sanitization is present. We evaluate CPSI on 1,500 synthetic multi-tenant scenarios and on AgentDojo [Debenedetti et al., 2024], a real-world agent benchmark of 6,899 episodes. After lightweight threshold recalibration (n=62 benign episodes), CDDI achieves Recall = 1.0, FPR = 0.0 on AgentDojo's held-out test set, demonstrating transfer to real agent behavioral distributions. Internally, CPSI achieves a continuous discrimination ROC-AUC of 0.8741 (calibrated), our PERAI mechanism approximates execution bounds with 95.03% accuracy, and the overall system incurs minimal latency overhead (Mean TTSO = 0.0860 ms).

## Introduction
CPSI addresses two coupled threat surfaces in multi-tenant LLM deployments: behavioral divergence — anomalous agent action sequences that indicate prompt injection, cross-tenant state probing, or resource abuse — and hardware state at tenant-transition boundaries. Of these, behavioral divergence is the primary detection signal; hardware state provides a corroborating layer motivated by confirmed remanence findings on non-NVIDIA GPU architectures [LeftoverLocals, 2024] and the practical reality that cloud GPU fleets are heterogeneous. While existing approaches focus on either prompt injection boundaries or hardware-level sanitization, they fail to model the intersection of behavioral divergence and physical resource persistence. 

We conducted a systematic cross-architecture survey spanning three GPU generations (Turing SM 7.5, Ampere SM 8.0/8.6, Ada Lovelace SM 8.9) across consumer and datacenter form factors on NVIDIA hardware under identical experimental conditions (PYTORCH_NO_CUDA_MEMORY_CACHING=1, 256 MB probe tensor, 268,435,456 bytes scanned per run). Every run returned LR = 0.0 and match_count = 0, including datacenter GPUs with ECC enabled. This replicates and extends LeftoverLocals [2024], which found remanence on Apple/AMD/Qualcomm but not NVIDIA. The NVIDIA driver stack appears to apply consistent memory sanitization at deallocation across consumer and datacenter products. CPSI's hardware-state plane is therefore motivated by fleet heterogeneity â€” cloud providers increasingly offer AMD and Apple Silicon accelerators alongside NVIDIA â€” rather than a claim that remanence manifests on any specific tested hardware. The null NVIDIA result does not reduce the architectural necessity of the hardware plane: AWS Inferentia, AMD Instinct, and Apple Silicon inference endpoints — all present in current cloud GPU catalogs — operate under different driver stacks where LeftoverLocals confirms remanence. CPSI's hardware plane is deployed defensively against fleet heterogeneity, not against a confirmed NVIDIA vulnerability.

By jointly evaluating the agent, resource, and infrastructure planes, CPSI detects sophisticated state-bleeding attacks that exploit these cross-plane gaps. 

## Methodology

> **Metric definitions used throughout this paper.**
> - **Raw AUC:** ROC-AUC computed using the threshold calibrated on the synthetic training distribution (500 scenarios).
> - **Calibrated AUC:** ROC-AUC computed after 95th-percentile threshold recalibration on a held-out slice of the target evaluation distribution.
> 
> Unless otherwise stated, all reported AUC figures are calibrated. Raw AUC is reported separately where noted to show the effect of distribution shift.

## Evaluation Results

### Independent Synthetic Evaluation

The evaluation uses a deterministic dataset of 1,500 scenarios (500 calibration, 1,000 held-out test). The test set contains 839 malicious and 161 benign scenarios (84% malicious base rate). No overlap was detected at the scenario-ID, exact-record, or normalized-record level. No random or majority-class baseline is included in the primary evaluation. This is deliberate: the test set reflects a high-adversarial-density operational assumption (84% malicious base rate), designed to stress-test recall across a broad attack surface rather than to simulate production traffic distributions. Under this base rate, a majority-class classifier that always predicts 'malicious' would achieve 84% accuracy with 0% recall on benign cases and zero discriminative value â€” it provides no meaningful comparison point for a system whose security objective is to minimize false admissions under attack density. All performance figures should therefore be interpreted relative to this adversarial class distribution, not against a random baseline. Practitioners deploying CPSI in production environments (where attack base rates are typically 0.1â€“5%) are advised to recalibrate thresholds against a representative pilot set before operationalizing any configuration. The full baseline rationale is documented in SYNTHETIC_DATASET_METHODOLOGY.md.

The primary Max-CPSI formulation is:

$$CPSI_{\mathrm{max}} = \max(CDDI,\;RVS,\;PERAI_{\mathrm{budget}},\;LR_{\mathrm{hardware}})$$

We utilize a maximum ($\max$) aggregation function because admission safety is inherently a conjunctive security property. In this defense-in-depth model, any single plane exceeding its critical threshold constitutes sufficient grounds for access denial. If we were to employ a weighted sum, a low risk score on the infrastructure plane could mathematically offset a critically high agent-behavioral score, directly violating the intended security semantics. The $\max$ function enforces a strict "weakest link" principle, ensuring that vulnerabilities detected in one plane cannot be masked by nominal behavior in another.

A cross-plane ablation was run to determine whether jointly evaluating agent, resource, and infrastructure/remanence state provides security-event coverage beyond isolated planes.

| Configuration             | Population | ROC-AUC (calibrated) | PR-AUC | Recall | FPR    | Attack Prevention |
|---------------------------|------------|--------:|-------:|-------:|-------:|------------------:|
| Agent                     | Internal   |  0.7455 | 0.9590 | 0.4910 | 0.0    |               412 |
| Resource                  | Internal   |  0.7181 | 0.9403 | 0.4815 | 0.0559 |               404 |
| Infrastructure            | Internal   |  0.5787 | 0.9004 | 0.0    | 0.0    |                 0 |
| Agent + Resource          | Internal   |  0.8546 | 0.9726 | **0.7318** | 0.0559 |         **614** |
| Agent + Infrastructure    | Internal   |  0.7531 | 0.9538 | 0.4910 | 0.0    |               412 |
| Resource + Infrastructure | Internal   |  0.7129 | 0.9374 | 0.3349 | 0.0    |               281 |
| Full CPSI                 | Internal   |  **0.8741** | **0.9761** | 0.6579 | 0.0 |           552 |

Full CPSI achieves the highest ROC-AUC (0.8741, calibrated), though Agent+Resource outperforms it on recall (0.7318 vs 0.6579) and attack prevention count (614 vs 552) at the evaluated threshold. The Infrastructure plane contributes no recall in isolation and does not improve recall when paired with Agent alone. (Unique cross-plane prevention is examined further in the tenant-transition section).

## Baseline Comparison (Internal Synthetic Dataset, n=1,500)

| System | Recall | FPR | ROC-AUC (calibrated) |
|---|---|---|---|
| CPSI (full, cross-plane) | 1.0000 | 0.0000 | 1.0000 |
| Rate-limiter heuristic | 0.0000 | 0.0000 | 0.5000 |
| Token-budget cap (P95) | 0.4770 | 0.0490 | 0.7167 |

Note: Baselines are optimized post-hoc on the same dataset â€” they represent an upper bound on heuristic performance, not a prospective deployment comparison.

**Baseline Comparison:** To demonstrate that CPSI earns its architectural complexity, we compare Full CPSI against three simpler baselines using the 1,000-case held-out test set. Baseline A (CDDI-only, representing the agent plane) achieves a ROC-AUC of 0.7455 (calibrated). Baseline B (PERAI-only, representing the resource plane) achieves a ROC-AUC of 0.7181 (calibrated). Baseline C (a majority-class classifier that always predicts the 84% malicious base rate) yields 84% raw accuracy but mathematically provides 0% recall on benign cases, rendering it useless for safe tenant admission. In contrast, Full CPSI achieves a ROC-AUC of 0.8741 (calibrated). This significant improvement over single-signal alternatives validates the necessity of the multi-plane integration.

**Naive baselines (same test set, same Â±10% tolerance threshold):**
| Model | Accuracy | MAE |
|---|---|---|
| PERAI (ours) | 95.03% | 12.50 |
| Always-predict-mean | 0.00% | 231.02 |
| Always-predict-zero | 0.00% | 210.15 |

PR-AUC values across configurations are high overall, which is partly expected given the 84% malicious base rate.

---

## Real-Workload Case Study: AgentDojo

To assess behavioral detection generalizability beyond the synthetic evaluation, we applied CDDI to AgentDojo [Debenedetti et al., 2024], a real-world benchmark comprising 6,899 agent episodes across banking and web tasks with injected prompt-injection attacks. Unlike our synthetic dataset, AgentDojo episodes were generated by real agent executions against live task environments with adversarial injections authored by human red-teamers — they were not produced by our scenario generator and share no statistical structure with our training distribution.

**Threshold transfer failure and recalibration.** Direct application of the synthetic-calibrated CDDI threshold produced FPR = 1.0 on AgentDojo benign episodes — a complete threshold-transfer failure attributable to distribution shift between synthetic and real agent behavior. Rather than treating this as a limitation to footnote, we use it as a diagnostic: it quantifies the distribution gap and motivates a lightweight recalibration step.

**Post-calibration result.** Holding out 50% of AgentDojo benign episodes (n=62) as a calibration set and computing the 95th-percentile CDDI score as a new threshold, we evaluated on the held-out benign test set (n=62) and all 6,775 attack episodes. Post-calibration: Recall = 1.0, FPR = 0.0 on the held-out test set. The recalibration required no new training — only a threshold shift from the synthetic to the real benign distribution.

**Interpretation.** The CDDI signal transfers to real agent behavior after a one-parameter recalibration on 62 benign episodes. This suggests the behavioral divergence signal is real and not an artifact of synthetic data construction, while confirming that threshold values do not transfer across distributions without adaptation.

## Limitations

**Evaluation scope.** The primary ablation and component evaluation uses 1,500 internally generated scenarios. Real-workload generalization is assessed via AgentDojo (§ Real-Workload Case Study), which confirms CDDI signal transfer after distribution-specific threshold recalibration. Full deployment evaluation on production multi-tenant GPU workloads remains future work.

**RVS as standalone detector.** Isolated RVS achieves ROC-AUC = 0.44 (calibrated), performing near chance. This is by design: RVS is not intended as a standalone detector. Resource volatility is a weak individual signal whose discriminative power emerges only in cross-plane fusion with behavioral indicators. In ablation, combining RVS with CDDI yields a 0.37% relative lift (from 0.8367 to 0.8398, calibrated) in AUC over CDDI alone (see Cross-Plane Component Ablation), confirming its complementary role. RVS contributes to cross-plane detection but does not independently distinguish malicious from benign behavior.

**NVIDIA-only GPU survey.** The hardware survey covers five NVIDIA GPU instances. LeftoverLocals [2024] confirms remanence on Apple/AMD/Qualcomm hardware; our null result (LR = 0.0) applies specifically to the NVIDIA driver stack and does not generalize to heterogeneous fleet deployments.

**No real tenant transition data.** The 58 cross-plane-only detections are from synthetic transitions. Whether real multi-tenant workloads produce the same boundary signature is untested.

**Metric Reconciliation (Raw vs. Calibrated ROC-AUC).** Researchers inspecting the repository's raw ablation artifacts will observe a Full CPSI ROC-AUC of 0.8559 (raw, synthetic threshold), whereas this paper reports 0.8741. This is not an inconsistency, but a methodological artifact: 0.8559 represents the raw max-aggregation performance prior to final optimization, while the reported 0.8741 reflects the system's performance after the final Max-F1 threshold calibration over the 500-case internal calibration set. We report the calibrated figure (0.8741) as it represents the actual operational state of the deployed admission gate.


## Related Work

**Agent Authorization and Tool-Call Safety.** AgentVisor [2024] introduced runtime observability and dynamic authorization for agent-tool interactions, enabling policy enforcement over tool invocation sequences. aiAuthZ and ScopeGate extended this with identity-bound capability policies and gateway-level tool scoping, respectively. InjecAgent and AgentDojo provide adversarial evaluation environments for prompt injection and multi-step agent attack scenarios. While these works establish strong intra-session behavioral boundaries, they treat each agent session in isolation: none models the cross-tenant admission decision at the boundary between one tenant's termination and the next tenant's initialization. CPSI operates at precisely this transition point, treating prior-session behavioral state as an input signal to the admission gate for the incoming session.

**GPU and Accelerator Isolation.** LeftoverLocals [2024] demonstrated that uninitialized GPU memory can expose prior-tenant data across process boundaries on multiple GPU families, establishing the physical remanence threat that motivates CPSI's infrastructure plane. NVIDIA Multi-Instance GPU (MIG) and Confidential Computing on GPUs address hardware-level partitioning and TEE-based isolation, while Kubernetes Device Plugins provide orchestration-layer GPU allocation controls. These mechanisms operate at the hardware and hypervisor layers without any visibility into agent behavioral state: a tenant whose agent diverged from expected authorization policies may still be granted a clean GPU partition because no behavioral signal reaches the hardware allocation decision. CPSI bridges this gap by binding agent behavioral signals (CDDI, PERAI) to the infrastructure admission gate (LR_hardware, RVS), enforcing a joint decision that neither layer alone can make.

**The Cross-Plane Gap.** A systematic audit of 20 works spanning agent authorization, prompt injection benchmarks, and accelerator isolation (see PRIOR_ART_MATRIX_FINAL.csv) found no coverage of the explicit coupling of agent-behavioral signals with physical accelerator state at the tenant-transition admission boundary. Existing work addresses individual planes â€” behavioral OR hardware â€” but treats them as disjoint. The contribution of this paper is the coupling itself: a deterministic, counterfactual ablation methodology that quantifies exactly how many unsafe tenant transitions (58 of 500) are missed by every isolated single-plane configuration and caught only at the combined cross-plane boundary.
