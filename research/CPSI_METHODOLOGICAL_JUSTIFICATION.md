# CPSI Methodological Justification

## Final Formulation
`CPSI = max(CDDI, RVS, PERAI_budget, LR_hardware)`

## Mathematical and Operational Justification

### Monotonicity
The `max()` operator ensures that increasing any constituent component risk cannot decrease the final CPSI score. If the agent acts maliciously (increasing CDDI), or the resource usage balloons (increasing PERAI), the overall system security risk strictly increases or remains equally elevated. 

### No-Risk-Cancellation Property
Unlike weighted averages or additive aggregations, `max()` prevents risk cancellation. A critically high-risk signal (e.g., highly anomalous tool sequence) cannot be mathematically averaged away by low-risk signals (e.g., normal token usage and zero remanence). A critical threat on any single plane forces the overall system risk score to a critical level.

### Boundary-Event Semantics
Identity violations, unsafe remanence states, or resource anomalies are independent escalation criteria. Each can independently force a security escalation. The formulation maps exactly to the principle that a chain is only as strong as its weakest link; an independent failure in any security plane is sufficient to declare the tenant transition unsafe.

### Threshold Interpretation
The CPSI score establishes a continuous threshold representing the required degree of scrutiny. 
- If `CPSI >= Threshold`: `REQUIRE_SANITIZATION`
- If `CPSI < Threshold`: `ADMIT_IMMEDIATELY`

The threshold determines the acceptable limit of uncertainty. 

### Calibration Separation
Threshold calibration ensures strict operational separation from out-of-distribution evaluation. Fitting occurs strictly on the 500-case calibration set using a predefined objective (maximize Recall subject to FPR <= 5%), or a deterministic F1-maximization fallback if the constraint is mathematically infeasible.

### Test Independence
The final test set (1,000 cases), external validation workloads (AgentDojo), and the tenant-transition set (500 cases) remain completely untouched by threshold optimization, preserving valid independent generalization results.

### Partial Observability
When a component is unavailable externally (e.g., `LR_hardware` in cloud AgentDojo endpoints), the system preserves `feature_available = false` metadata rather than silently interpreting missing telemetry as observed zero risk. The `0.0` value is used specifically because it is the identity element of the nonnegative `max()` operator, ensuring the missing feature does not mathematically alter the remaining available features while retaining an explicit `NOT OBSERVABLE` caveat in reporting.

### Why Max is a Security Policy
The `max()` operator is not claimed to be a mathematically optimal decision boundary for all classification settings. Rather, it is a deliberate, conservative aggregation policy. Its empirical behavior—and potential vulnerability to high noise (e.g., rigid thresholding producing 1.0 FPR externally)—was rigorously evaluated and published as an architectural ablation finding.
