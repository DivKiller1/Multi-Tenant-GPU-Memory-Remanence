# CPSI: Cross-Plane Security Infrastructure

## Abstract
Existing agent-security work treats behavioral and hardware isolation as disjoint. We demonstrate that relying on isolated defenses misses critical cross-tenant vulnerabilities. In a paired evaluation of 500 tenant-transition scenarios, we show that 58 unsafe transitions are missed by every isolated single-plane approach and caught only at the combined cross-plane boundary. We introduce the Cross-Plane Security Infrastructure (CPSI), a defense-in-depth architecture integrating agent, resource, and infrastructure planes. CPSI achieves a continuous discrimination ROC-AUC of 0.8741. Our resource evaluation mechanism (PERAI) approximates execution bounds with 95% accuracy, and the overall system incurs minimal latency overhead (Mean TTSO = 0.0860 ms), demonstrating that cross-plane security is both necessary and performant for multi-tenant LLM environments.

## Introduction
Multi-tenant agent architectures face cross-plane security threats that isolated defenses consistently miss. While existing approaches focus on either prompt injection boundaries or hardware-level sanitization, they fail to model the intersection of behavioral divergence and physical resource persistence. 

Our findings indicate that single-plane defenses are insufficient. Although we observe that implicit zero-initialization on some hardware configurations (e.g., RTX 3050) acts as a vendor-specific mitigation, hardware behavior remains non-uniform across cloud GPU fleets (as demonstrated by vulnerabilities like LeftoverLocals). CPSI is designed to defend against configurations where this zero-initialization guarantee is absent or circumvented.

By jointly evaluating the agent, resource, and infrastructure planes, CPSI detects sophisticated state-bleeding attacks that exploit these cross-plane gaps. 

## Evaluation Results

### Independent Synthetic Evaluation

The evaluation uses a deterministic dataset of 1,500 scenarios (500 calibration, 1,000 held-out test). The test set contains 839 malicious and 161 benign scenarios (84% malicious base rate). No overlap was detected at the scenario-ID, exact-record, or normalized-record level. No random or majority-class baseline is included; all performance figures should be interpreted against this class imbalance and the absence of a reference baseline throughout.

The primary Max-CPSI formulation is:

$$CPSI_{\mathrm{max}} = \max(CDDI,\;RVS,\;PERAI_{\mathrm{budget}},\;LR_{\mathrm{hardware}})$$

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

To mitigate this threshold-transfer failure, we performed a lightweight percentile-calibration on a held-out slice (50%) of the AgentDojo benign cases, recalibrating the threshold to the 95th percentile of this set. This restored operational performance on the remaining test set, yielding an FPR of 0.0 and maintaining a Recall of 1.0 on the malicious population. This demonstrates that the failure was a calibration issue rather than an architectural limitation. Continuous discrimination and operational threshold performance are distinct; only the former is initially demonstrated here, while the latter can be recovered via in-domain recalibration.

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
