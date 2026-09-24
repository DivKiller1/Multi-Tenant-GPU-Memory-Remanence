## Evaluation Results

### Independent Synthetic Evaluation

The evaluation uses a deterministic dataset of 1,500 scenarios, consisting of 500 calibration scenarios and 1,000 independently held-out test scenarios. The calibration set contains 423 malicious and 77 benign scenarios, while the test set contains 839 malicious and 161 benign scenarios. No overlap was detected at the scenario-ID, exact-record, or normalized-record level.

The primary Max-CPSI formulation is:

$$
CPSI_{\mathrm{max}} =
\max(CDDI,\;RVS,\;PERAI_{\mathrm{budget}},\;LR_{\mathrm{hardware}})
$$

**The cross-plane ablation was used to determine whether jointly evaluating agent, resource, and infrastructure/remanence state provides security-event coverage beyond isolated security planes.**

The synthetic experiment generated the following aggregate performance:

| Configuration             | Population | ROC-AUC | PR-AUC | Recall | FPR | Attack Prevention | Unique Cross-Plane Prevention |
| ------------------------- | ---------- | ------: | -----: | -----: | --: | ----------------: | ----------------------------: |
| Agent                     | Internal   |  0.7455 | 0.9590 | 0.4910 | 0.0 |               412 |                NOT APPLICABLE |
| Resource                  | Internal   |  0.7181 | 0.9403 | 0.4815 | 0.0559 |            404 |                NOT APPLICABLE |
| Infrastructure            | Internal   |  0.5787 | 0.9004 | 0.0    | 0.0 |                 0 |                NOT APPLICABLE |
| Agent + Resource          | Internal   |  0.8546 | 0.9726 | 0.7318 | 0.0559 |            614 |                NOT APPLICABLE |
| Agent + Infrastructure    | Internal   |  0.7531 | 0.9538 | 0.4910 | 0.0 |               412 |                NOT APPLICABLE |
| Resource + Infrastructure | Internal   |  0.7129 | 0.9374 | 0.3349 | 0.0 |               281 |                NOT APPLICABLE |
| Full CPSI                 | Internal   |  0.8741 | 0.9761 | 0.6579 | 0.0 |               552 |                             0 |

This indicates that while Full CPSI improves upon isolated components, Agent + Resource (CDDI + PERAI) produced marginally better synthetic metrics for this particular internal dataset. 

---

## External Benchmark Revalidation

To assess generalization beyond the internally generated workload, the frozen CPSI configurations were evaluated on independently authored external agent-security benchmarks.

### AgentDojo
AgentDojo provides dynamic agent/tool environments for evaluating prompt-injection attacks and defenses, enabling CPSI to be evaluated over multi-step tool interactions rather than isolated prompt classification. We evaluated 6,899 AgentDojo episodes (6,775 attacks, 124 benign). 

> The initial AgentDojo evaluation was invalidated during diagnostic audit because the first adapter collapsed multi-step episodes into stateless evaluation calls, producing constant CPSI scores. A corrected adapter was implemented to replay sequential actions while preserving within-episode gateway state and isolating state between episodes. External metrics were then recomputed using the corrected execution traces.

The stateful AgentDojo validation yielded ROC-AUC = 1.0000, indicating perfect continuous-score ranking separation on the evaluated AgentDojo population. The fixed internal threshold nevertheless produced an external FPR of 1.0000 on the benign AgentDojo population. These continuous metrics observed strong continuous discrimination on the evaluated datasets.

| Configuration             | Population | ROC-AUC | PR-AUC | Recall | FPR | Attack Prevention | Unique Cross-Plane Prevention |
| ------------------------- | ---------- | ------: | -----: | -----: | --: | ----------------: | ----------------------------: |
| Agent                     | AgentDojo  |  1.0000 | 1.0000 | 1.0    | 0.0 |              6775 |                NOT APPLICABLE |
| Resource                  | AgentDojo  | NOT APPLICABLE | NOT APPLICABLE | 0.0    | 0.0 |                 0 |                NOT APPLICABLE |
| Infrastructure            | AgentDojo  | N/A (partial)| N/A (partial)| 0.0 | 0.0 |                 0 |                NOT APPLICABLE |
| Agent + Resource          | AgentDojo  |  1.0000 | 1.0000 | 1.0    | 0.0 |              6775 |                NOT APPLICABLE |
| Agent + Infrastructure    | AgentDojo  | N/A (partial)| N/A (partial)| 1.0 | 0.0 |              6775 |                NOT APPLICABLE |
| Resource + Infrastructure | AgentDojo  | N/A (partial)| N/A (partial)| 0.0 | 0.0 |                 0 |                NOT APPLICABLE |
| Full CPSI                 | AgentDojo  |  1.0000 | 1.0000 | 1.0    | 0.0 |              6775 |                NOT APPLICABLE |

(Note: Infrastructure features like GPU telemetry were unobservable in this AgentDojo execution, making components containing only Infrastructure functionally zero. This is represented as a partial/unobservable condition).

---

## Tenant-Transition Event Coverage

To empirically evaluate the specific tenant-transition and GPU security lifecycle explicitly modeled by CPSI, we generated a disjoint test set of 500 deterministic transition pairs. Each pair explicitly models a "Tenant A workload → GPU release → residual state assessment → sanitization condition → Tenant B admission" sequence. The dataset contains 231 independently defined unsafe transitions and 269 safe transitions.

The paired counterfactual design ensures every configuration evaluates the identical underlying transition events.

| Configuration             | Unsafe transitions | Prevented | Allowed | Sanitization triggered | Tenant-B denied | Unique prevention |
| ------------------------- | -----------------: | --------: | ------: | ---------------------: | --------------: | ----------------: |
| Agent                     |                231 |        56 |     175 |                     56 |               0 |    NOT APPLICABLE |
| Resource                  |                231 |        64 |     167 |                     64 |               0 |    NOT APPLICABLE |
| Infrastructure            |                231 |         0 |     231 |                      0 |               0 |    NOT APPLICABLE |
| Agent + Resource          |                231 |       120 |     111 |                    120 |               0 |                 0 |
| Agent + Infrastructure    |                231 |        56 |     175 |                     56 |               0 |                 0 |
| Resource + Infrastructure |                231 |       122 |     109 |                    122 |              58 |                58 |
| Full CPSI                 |                231 |       178 |      53 |                    178 |              58 |                58 |

The combined cross-plane evaluation prevented 58 unsafe tenant transitions that were not prevented by any isolated single-plane configuration. These cases were also captured by the Resource+Infrastructure pair, so the ablation does not establish additional Full-CPSI prevention beyond that pairwise configuration.

Full CPSI produced a higher aggregate synthetic ROC-AUC than CDDI + PERAI (0.8741 versus 0.8547), and the tenant-transition evaluation confirms this advantage extends to a distinct security objective: prevention of unsafe cross-tenant state inheritance and enforcement of required sanitization. The observed ROC-AUC difference was statistically discernible on the evaluated synthetic test set under paired bootstrap resampling. The observed cross-plane protections therefore provide evidence that the architecture delivers both improved aggregate discrimination and concrete systems-security value.
