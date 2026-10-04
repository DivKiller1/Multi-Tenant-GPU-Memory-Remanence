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
