# Final Statistical Audit

**Audit Date:** 2026-09-24

## 1. Methodology
This audit uses the actual per-sample predictions and continuous scores computed during the independent synthetic evaluation test set (N=1000). To establish statistical confidence boundaries around point estimates, we generated 1,000 bootstrap resamples (seed=42). 

For comparing the continuous discrimination of Full CPSI against CDDI + PERAI (Agent + Resource), we utilized paired resampling on the same test cases.

## 2. Full CPSI Performance Estimate CIs
The 95% bootstrap confidence intervals for the primary performance metrics are as follows:

| Dataset Identity | Sample Count | Pos/Neg Classes | Configuration | Threshold Source | Calibration Objective | Metric | Point Estimate | 95% Confidence Interval |
|------------------|-------------|-----------------|---------------|-----------------|----------------------|--------|---------------|-------------------------|
| Internal Test | 1000 | 839 Pos / 161 Neg | Full CPSI | `threshold_manifest.json` | Max F1 (FPR <= 0.05) | ROC-AUC | 0.8741 | (0.8522, 0.8953) |
| Internal Test | 1000 | 839 Pos / 161 Neg | Full CPSI | `threshold_manifest.json` | Max F1 (FPR <= 0.05) | PR-AUC | 0.9761 | (0.9708, 0.9812) |
| Internal Test | 1000 | 839 Pos / 161 Neg | Full CPSI | `threshold_manifest.json` | Max F1 (FPR <= 0.05) | Precision | 1.0000 | (1.0000, 1.0000) |
| Internal Test | 1000 | 839 Pos / 161 Neg | Full CPSI | `threshold_manifest.json` | Max F1 (FPR <= 0.05) | Recall | 0.6579 | (0.6256, 0.6863) |
| Internal Test | 1000 | 839 Pos / 161 Neg | Full CPSI | `threshold_manifest.json` | Max F1 (FPR <= 0.05) | F1 | 0.7936 | (0.7697, 0.8140) |
| Internal Test | 1000 | 839 Pos / 161 Neg | Full CPSI | `threshold_manifest.json` | Max F1 (FPR <= 0.05) | FPR | 0.0000 | (0.0000, 0.0000) |

*Note: Variance for Precision and FPR is extremely low because the calibrated operating point (frozen threshold) effectively blocked all false positives on the synthetic test set, resulting in deterministic classification behavior at that boundary.*

## 3. Paired Difference Audit
We audited the difference in discrimination power (ROC-AUC) between the Full CPSI aggregation and the best constituent pairwise component (CDDI + PERAI).

- **Full CPSI ROC-AUC:** 0.8741
- **CDDI + PERAI ROC-AUC:** 0.8547
- **Difference:** +0.0194
- **95% CI for the Difference:** (0.0031, 0.0363)

### Interpretation
Because the 95% paired-bootstrap confidence interval for the difference strictly excludes zero (0.0031 to 0.0363), the observed ROC-AUC difference was statistically discernible on the evaluated synthetic test set under paired bootstrap resampling.
