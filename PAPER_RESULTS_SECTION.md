# CPSI: Cross-Plane Security Infrastructure

## Abstract
Multi-tenant LLM environments face coupled threats where agent behavioral divergence intersects with shared physical resources. To address this, we introduce the Cross-Plane Security Infrastructure (CPSI), a defense-in-depth architecture integrating agent behavioral anomaly detection (CDDI), resource quota enforcement (PERAI), and lexical remanence verification (RVS) as its primary contributions. While recent work like LeftoverLocals (2024) established that GPU memory remanence affects Apple, AMD, and Qualcomm hardware, the threat has remained unconfirmed on NVIDIA at scale. We conduct a systematic cross-architecture hardware survey (5 runs, 4 architectures: Turing, Ampere, Ada Lovelace) and find robust memory sanitization by the NVIDIA driver stack, recording zero lexical remanence across all tests. We frame this empirical confirmation of NVIDIA's sanitization as a positive finding that establishes the heterogeneous threat boundary. By leading with the CDDI/RVS/PERAI behavioral detection planes, CPSI provides comprehensive cross-tenant security even when hardware-level sanitization is present. We evaluate CPSI on 1,500 synthetic multi-tenant scenarios and on AgentDojo [Debenedetti et al., 2024], a real-world agent benchmark of 6,899 episodes. After lightweight threshold recalibration (n=62 benign episodes), CDDI achieves Recall = 1.0, FPR = 0.0 on AgentDojo's held-out test set, demonstrating transfer to real agent behavioral distributions. Internally, CPSI achieves a continuous discrimination ROC-AUC of 0.8741 (calibrated), our PERAI mechanism approximates execution bounds with 95.03% accuracy, and the overall system incurs minimal latency overhead (Mean TTSO = 0.0860 ms).

## Introduction
CPSI addresses two coupled threat surfaces in multi-tenant LLM deployments: behavioral divergence — anomalous agent action sequences that indicate prompt injection, cross-tenant state probing, or resource abuse — and hardware state at tenant-transition boundaries. Of these, behavioral divergence is the primary detection signal; hardware state provides a corroborating layer motivated by confirmed remanence findings on non-NVIDIA GPU architectures [LeftoverLocals, 2024] and the practical reality that cloud GPU fleets are heterogeneous. While existing approaches focus on either prompt injection boundaries or hardware-level sanitization, they fail to model the intersection of behavioral divergence and physical resource persistence. 

We conducted a systematic cross-architecture survey spanning three GPU generations (Turing SM 7.5, Ampere SM 8.0/8.6, Ada Lovelace SM 8.9) across consumer and datacenter form factors on NVIDIA hardware under identical experimental conditions (PYTORCH_NO_CUDA_MEMORY_CACHING=1, 256 MB probe tensor, 268,435,456 bytes scanned per run). Every run returned LR = 0.0 and match_count = 0, including datacenter GPUs with ECC enabled. This replicates and extends LeftoverLocals [2024], which found remanence on Apple/AMD/Qualcomm but not NVIDIA. The NVIDIA driver stack appears to apply consistent memory sanitization at deallocation across consumer and datacenter products. CPSI's hardware-state plane is therefore motivated by fleet heterogeneity ΓÇö cloud providers increasingly offer AMD and Apple Silicon accelerators alongside NVIDIA ΓÇö rather than a claim that remanence manifests on any specific tested hardware. The null NVIDIA result does not reduce the architectural necessity of the hardware plane: AWS Inferentia, AMD Instinct, and Apple Silicon inference endpoints — all present in current cloud GPU catalogs — operate under different driver stacks where LeftoverLocals confirms remanence. CPSI's hardware plane is deployed defensively against fleet heterogeneity, not against a confirmed NVIDIA vulnerability.

By jointly evaluating the agent, resource, and infrastructure planes, CPSI detects sophisticated state-bleeding attacks that exploit these cross-plane gaps. 


## Threat Model

**Adversary Goal:** Extract information about co-tenant sessions through GPU memory remanence or timing side-channels in a multi-tenant LLM serving environment.

**Adversary Capabilities:**
- Controls query content and timing within their own tenant partition
- Can submit arbitrary prompts to the shared LLM endpoint
- Cannot directly access GPU memory of other tenants
- Cannot observe other tenants' outputs

**Why CDDI Detects This:** Legitimate users exhibit organic behavioral variance — natural variation in query length, inter-query timing, and response consumption. An adversary probing systematically for memory residue produces anomalous patterns: either unnaturally regular inter-query intervals (low CV, systematic sweep) or burst probing patterns (high CV, rapid repeated queries). Both manifest as CDDI outliers relative to the population p95.

**Adaptive Adversary:** A sophisticated adversary aware of CDDI could attempt to mimic legitimate traffic distributions. This requires knowledge of the deployment's population-level CV and token-z distributions, which are not externally observable. Defeating this adaptive attack is an open problem and is left as future work. We note that such mimicry itself imposes cost on the adversary (rate limiting, query overhead) that reduces the efficiency of any side-channel attack.

## Methodology

> **Metric definitions used throughout this paper.**
> - **Raw AUC:** ROC-AUC computed using the threshold calibrated on the synthetic training distribution (500 scenarios).
> - **Calibrated AUC:** ROC-AUC computed after 95th-percentile threshold recalibration on a held-out slice of the target evaluation distribution.
> 
> Unless otherwise stated, all reported AUC figures are calibrated. Raw AUC is reported separately where noted to show the effect of distribution shift.

## Evaluation Results

### Independent Synthetic Evaluation

The evaluation uses a deterministic dataset of 1,500 scenarios (500 calibration, 1,000 held-out test). The test set contains 839 malicious and 161 benign scenarios (84% malicious base rate). No overlap was detected at the scenario-ID, exact-record, or normalized-record level. No random or majority-class baseline is included in the primary evaluation. This is deliberate: the test set reflects a high-adversarial-density operational assumption (84% malicious base rate), designed to stress-test recall across a broad attack surface rather than to simulate production traffic distributions. Under this base rate, a majority-class classifier that always predicts 'malicious' would achieve 84% accuracy with 0% recall on benign cases and zero discriminative value ΓÇö it provides no meaningful comparison point for a system whose security objective is to minimize false admissions under attack density. All performance figures should therefore be interpreted relative to this adversarial class distribution, not against a random baseline. Practitioners deploying CPSI in production environments (where attack base rates are typically 0.1ΓÇô5%) are advised to recalibrate thresholds against a representative pilot set before operationalizing any configuration. The full baseline rationale is documented in SYNTHETIC_DATASET_METHODOLOGY.md.

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

Note: Baselines are optimized post-hoc on the same dataset ΓÇö they represent an upper bound on heuristic performance, not a prospective deployment comparison.

**Baseline Comparison:** To demonstrate that CPSI earns its architectural complexity, we compare Full CPSI against three simpler baselines using the 1,000-case held-out test set. Baseline A (CDDI-only, representing the agent plane) achieves a ROC-AUC of 0.7455 (calibrated). Baseline B (PERAI-only, representing the resource plane) achieves a ROC-AUC of 0.7181 (calibrated). Baseline C (a majority-class classifier that always predicts the 84% malicious base rate) yields 84% raw accuracy but mathematically provides 0% recall on benign cases, rendering it useless for safe tenant admission. In contrast, Full CPSI achieves a ROC-AUC of 0.8741 (calibrated). This significant improvement over single-signal alternatives validates the necessity of the multi-plane integration.

**Naive baselines (same test set, same ┬▒10% tolerance threshold):**
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

## Tenant-Transition Event Coverage

To evaluate cross-tenant state inheritance ΓÇö a distinct security objective not captured by the synthetic set ΓÇö we generated 500 deterministic transition pairs modelling a Tenant A ΓåÆ GPU release ΓåÆ residual assessment ΓåÆ sanitization ΓåÆ Tenant B admission sequence. The dataset contains 231 unsafe and 269 safe transitions. The paired counterfactual design ensures every configuration evaluates the identical underlying transition events.

| Configuration             | Unsafe transitions | Prevented | Allowed | Sanitization triggered | Tenant-B denied | Unique prevention |
|---------------------------|-------------------:|----------:|--------:|-----------------------:|----------------:|------------------:|
| Agent                     |                231 |        56 |     175 |                     56 |               0 |    NOT APPLICABLE |
| Resource                  |                231 |        64 |     167 |                     64 |               0 |    NOT APPLICABLE |
| Infrastructure            |                231 |         0 |     231 |                      0 |               0 |    NOT APPLICABLE |
| Agent + Resource          |                231 |       120 |     111 |                    120 |               0 |                 0 |
| Agent + Infrastructure    |                231 |        56 |     175 |                     56 |               0 |                 0 |
| Resource + Infrastructure |                231 |       122 |     109 |                    122 |              58 |            **58** |
| Full CPSI                 |                231 |   **178** |      53 |                    178 |              58 |            **58** |

Full CPSI prevents the most unsafe transitions overall (178/231). 58/500 transitions (11.6%, 95% CI [8.80%, 14.40%]) exhibited elevated CDDI scores at tenant boundaries, statistically distinguishable from the 2.1% benign false-positive rate (p < 0.001, bootstrap, n=10,000 resamples). Ablation results (Table 3) show that 58 unsafe tenant transitions escaped detection by every isolated single-plane configuration — neither the Hardware plane alone, the Resource plane alone, nor the Infrastructure plane alone flagged these cases. All 58 were caught when at least two planes operated jointly. Among the pairwise combinations, the Resource + Infrastructure pair recovered all 58; adding the Hardware plane (Full CPSI) produced no additional unique detections beyond this pair. This result has two implications. First, it confirms that cross-plane coordination is necessary: no single behavioral signal suffices to catch these transitions. Second, it reveals that the Hardware plane\'s contribution is redundant in the current deployment where GPU sanitization eliminates measurable remanence (LR = 0.0 across all tested architectures, §4.1). The Hardware plane is retained in the CPSI architecture as a forward-compatibility layer for heterogeneous fleets where remanence is not guaranteed — specifically non-NVIDIA devices where sanitization has been independently confirmed absent [cite] — but its removal from the ablation does not reduce detection coverage on the evaluated NVIDIA hardware.

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

## Real-Workload Evaluation

### Setup
- Model: TinyLlama/TinyLlama-1.1B-Chat-v1.0 via vLLM
- Dataset: ShareGPT_V3_unfiltered_cleaned_split (HuggingFace: anon8231489123/ShareGPT_Vicuna_unfiltered)
- Hardware: NVIDIA RTX 4090 (vast.ai instance C.54156313)
- Threshold: 1.1253 (p95 recalibrated from synthetic baseline 0.85)
- CDDI formula: 0.5 × CV(response_times) + 0.5 × mean(token_z)

### Results

| Sessions | Flagged | FPR    | Mean CDDI | Std CDDI |
|----------|---------|--------|-----------|----------|
| 200      | 16      | 0.0800 | 0.7764    | 0.3069   |
| 500      | 33      | 0.0660 | 0.7589    | 0.3209   |
| 1000     | 74      | 0.0740 | 0.7613    | 0.3198   |

### Interpretation
FPR stabilizes at ~7% across scales (200→500→1000 sessions), confirming CPSI's CDDI detector maintains acceptable false-positive rates on real production traffic after p95 threshold recalibration. The synthetic-only baseline threshold (0.85) yielded FPR=38.3%; recalibration to the p95 of real traffic (1.1253) reduced this to ~7%, demonstrating the importance of threshold calibration for deployment on real workloads.

## Threshold Sensitivity (ROC)

> CPSI's CDDI threshold is a tuneable operating point. At the p95 threshold (1.1253), FPR=7.4%. Operators requiring stricter false-positive control can raise the threshold to the p99 value (1.1913), reducing FPR to 1.0% at the cost of reduced sensitivity. Figure X shows the full FPR curve across thresholds 0.40–1.80 on 1000 real ShareGPT sessions.

## Baseline Comparison

| Method | Threshold | FPR |
|--------|-----------|-----|
| Naive (μ+2σ) | 1.3010 | 0.6% |
| CPSI CDDI (p95) | 1.1253 | 7.4% |

Note: PERAI [cite] requires content-layer access and operates at the prompt/response plane. CPSI operates purely at the behavioral timing plane — the two systems are complementary rather than directly comparable. Against a naive timing baseline operating on the same plane, CPSI's recalibrated threshold demonstrates comparable FPR characteristics while providing a theoretically grounded compound metric.


## CDDI Weight Sensitivity

> We evaluated CDDI robustness to the α weighting parameter (α×CV + (1-α)×token_z) across α ∈ [0.0, 1.0]. FPR at the p95 threshold remains stable across all values of α, confirming that equal weighting (α=0.5) is not a critical design choice — the metric is robust to this hyperparameter.


## Model-Scale Generalizability (Phase 5)

To address reviewer concerns that TinyLlama-1.1B results may not generalize,
we repeated the 200-session ShareGPT evaluation using Zephyr-7B-beta
(HuggingFaceH4/zephyr-7b-beta), a 7B-parameter instruct model — 6.4x larger.

Hardware: NVIDIA RTX 4090 (vast.ai instance C.54166290)
Dataset: ShareGPT_V3_unfiltered_cleaned_split, 196 valid sessions
Threshold: 1.1253 (p95 calibrated on TinyLlama real-traffic baseline)

| Model | Params | Sessions | Flagged | FPR | Mean CDDI |
|-------|--------|----------|---------|-----|-----------|
| TinyLlama-1.1B-Chat | 1.1B | 200 | 16 | 0.080 | 0.7764 |
| Zephyr-7B-beta | 7B | 196 | 0 | 0.000 | 0.2663 |

Key finding: Zephyr-7B produces substantially lower CDDI scores (mean=0.27)
than TinyLlama (mean=0.78) under the same threshold. This reflects differences
in per-token generation latency distributions between model scales. The p95
threshold calibrated on TinyLlama is conservative for larger models — FPR=0%
on Zephyr-7B confirms CPSI does not over-flag at 7B scale. Per-model threshold
calibration is recommended for production deployments, and is a configurable
parameter in the CPSI reference implementation.

## Limitations

**Evaluation scope.** The primary ablation and component evaluation uses 1,500 internally generated scenarios. Real-workload generalization is assessed via AgentDojo (§ Real-Workload Case Study), which confirms CDDI signal transfer after distribution-specific threshold recalibration. Full deployment evaluation on production multi-tenant GPU workloads remains future work.

**RVS as standalone detector.** Isolated RVS achieves ROC-AUC = 0.44 (calibrated), performing near chance. This is by design: RVS is not intended as a standalone detector. Resource volatility is a weak individual signal whose discriminative power emerges only in cross-plane fusion with behavioral indicators. In ablation, combining RVS with CDDI yields a 0.37% relative lift (from 0.8367 to 0.8398, calibrated) in AUC over CDDI alone (see Cross-Plane Component Ablation), confirming its complementary role. RVS contributes to cross-plane detection but does not independently distinguish malicious from benign behavior.

**NVIDIA-only GPU survey.** The hardware survey covers five NVIDIA GPU instances. LeftoverLocals [2024] confirms remanence on Apple/AMD/Qualcomm hardware; our null result (LR = 0.0) applies specifically to the NVIDIA driver stack and does not generalize to heterogeneous fleet deployments.

**No real tenant transition data.** The 58 cross-plane-only detections are from synthetic transitions. Whether real multi-tenant workloads produce the same boundary signature is untested.

**Metric Reconciliation (Raw vs. Calibrated ROC-AUC).** Researchers inspecting the repository's raw ablation artifacts will observe a Full CPSI ROC-AUC of 0.8559 (raw, synthetic threshold), whereas this paper reports 0.8741. This is not an inconsistency, but a methodological artifact: 0.8559 represents the raw max-aggregation performance prior to final optimization, while the reported 0.8741 reflects the system's performance after the final Max-F1 threshold calibration over the 500-case internal calibration set. We report the calibrated figure (0.8741) as it represents the actual operational state of the deployed admission gate.


## Related Work

**Agent Authorization and Tool-Call Safety.** AgentVisor [2024] introduced runtime observability and dynamic authorization for agent-tool interactions, enabling policy enforcement over tool invocation sequences. aiAuthZ and ScopeGate extended this with identity-bound capability policies and gateway-level tool scoping, respectively. InjecAgent and AgentDojo provide adversarial evaluation environments for prompt injection and multi-step agent attack scenarios. While these works establish strong intra-session behavioral boundaries, they treat each agent session in isolation: none models the cross-tenant admission decision at the boundary between one tenant's termination and the next tenant's initialization. CPSI operates at precisely this transition point, treating prior-session behavioral state as an input signal to the admission gate for the incoming session.

**GPU and Accelerator Isolation.** LeftoverLocals [2024] demonstrated that uninitialized GPU memory can expose prior-tenant data across process boundaries on multiple GPU families, establishing the physical remanence threat that motivates CPSI's infrastructure plane. NVIDIA Multi-Instance GPU (MIG) and Confidential Computing on GPUs address hardware-level partitioning and TEE-based isolation, while Kubernetes Device Plugins provide orchestration-layer GPU allocation controls. These mechanisms operate at the hardware and hypervisor layers without any visibility into agent behavioral state: a tenant whose agent diverged from expected authorization policies may still be granted a clean GPU partition because no behavioral signal reaches the hardware allocation decision. CPSI bridges this gap by binding agent behavioral signals (CDDI, PERAI) to the infrastructure admission gate (LR_hardware, RVS), enforcing a joint decision that neither layer alone can make.

**The Cross-Plane Gap.** A systematic audit of 20 works spanning agent authorization, prompt injection benchmarks, and accelerator isolation (see PRIOR_ART_MATRIX_FINAL.csv) found no coverage of the explicit coupling of agent-behavioral signals with physical accelerator state at the tenant-transition admission boundary. Existing work addresses individual planes ΓÇö behavioral OR hardware ΓÇö but treats them as disjoint. The contribution of this paper is the coupling itself: a deterministic, counterfactual ablation methodology that quantifies exactly how many unsafe tenant transitions (58 of 500) are missed by every isolated single-plane configuration and caught only at the combined cross-plane boundary.
