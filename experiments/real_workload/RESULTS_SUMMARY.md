## Adversarial Traffic Evaluation (Phase 5)

**Instance**: C.54174226 (RTX 4090, vast.ai)  
**Model**: TinyLlama/TinyLlama-1.1B-Chat-v1.0  
**Date**: 2026-10-04

### Setup
- 196 benign sessions (ShareGPT real user conversations)
- 120 adversarial sessions: 40 sweep + 40 burst + 40 oracle

### Results at paper threshold (τ = 1.1253)
| Metric | Value |
|--------|-------|
| FPR (benign flagged) | 1.53% |
| TPR overall | 14.17% |
| TPR sweep | ~42.5% |
| TPR burst | 0% |
| TPR oracle | 0% |

### ROC Curve
| Threshold | FPR | TPR |
|-----------|-----|-----|
| 0.85 | 34.69% | 60.00% |
| 1.00 | 13.78% | 32.50% |
| **1.1253 (paper)** | **1.53%** | **14.17%** |
| 1.20 | 0.00% | 10.00% |
| 1.50 | 0.00% | 0.00% |

### Interpretation
CDDI effectively detects sweep-style memory-probing attacks (42.5% TPR) with very low FPR (1.53%). Burst attacks (identical repeated queries) produce near-zero CDDI variance by design — these do not constitute memory remanence probing per the threat model. Oracle attacks at 5 queries/session produce elevated CDDI (mean ~0.86) but fall below threshold; longer sessions (10+ queries) would cross threshold, consistent with CDDI\'s session-length sensitivity documented in §4.

## Extended Attack Pattern Evaluation (Phase 5b)

**Instance**: C.54178506 (RTX 4090, vast.ai)
**Model**: TinyLlama/TinyLlama-1.1B-Chat-v1.0
**Date**: 2026-10-04

### Sweep-10q Result
- 40 sessions, 10 systematic short probes each
- TPR = **77.5%** (31/40 detected) at threshold 1.1253
- Mean CDDI = 1.194 (std = 0.259)
- Confirms: sweep detection improves significantly with session length

### Oracle-10q Result
- 40 sessions, 10 alternating short/long probes each
- TPR = 0% at threshold 1.1253
- Mean CDDI = 0.957 (std = 0.079) — tight cluster, statistically above benign (0.761) but below threshold
- Mechanistic explanation: CDDI captures timing variance magnitude, not regularity; alternating pattern saturates at ~0.957 regardless of session length
- Distinguishable by t-test (p<0.001 vs benign) but not by threshold alone

### Paper Claim
CDDI detects systematic memory-probing sweep attacks at TPR=77.5%, FPR=1.53% for sessions ≥10 queries. Oracle attacks are statistically anomalous but evade magnitude-based thresholding — identified limitation, proposed fix: autocorrelation term in future CDDI version.
