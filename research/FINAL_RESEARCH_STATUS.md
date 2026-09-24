# Final Research Status

**Audit Date:** 2026-09-24

### Empirically Established
- **Cross-Plane Necessity:** The combined cross-plane evaluation prevented 58 unsafe tenant transitions that were not prevented by any isolated single-plane configuration. These cases were also captured by the Resource+Infrastructure pair, so the ablation does not establish additional Full-CPSI prevention beyond that pairwise configuration.
- **Discrimination:** The integrated CPSI architecture achieved a ROC-AUC of 0.8741 on the internal test set, demonstrating a statistically robust improvement over CDDI + PERAI alone (CI: 0.0031 to 0.0363).
- **External Continuous Validation:** Continuous feature extraction successfully generalized to the multi-step AgentDojo dataset, yielding ROC-AUC = 1.0000, indicating perfect continuous-score ranking separation on the evaluated AgentDojo population. The fixed internal threshold nevertheless produced an external FPR of 1.0000 on the benign AgentDojo population. These continuous metrics observed strong continuous discrimination on the evaluated datasets.
- **Latency Overheads:** Mean Tenant Transition Setup Overhead (TTSO) was exactly measured at 0.0860 ms, conforming to operational multi-tenant SLA constraints.
- **Final Novelty Statement:** Existing work predominantly addresses individual agent authorization, tool-call safety, prompt injection, or accelerator isolation. The evaluated contribution here is the explicit coupling of these signals at the tenant-transition boundary, together with a deterministic paired-counterfactual methodology for measuring isolated-plane versus combined-plane enforcement. The combined cross-plane evaluation captured 58 unsafe transitions missed by every isolated single-plane configuration, while explicitly exposing continuous discrimination versus threshold-transfer limitations.

### Partially Established / Context-Bound
- **Sanitization Requirements:** While the architecture accurately triggers and verifies required sanitization boundaries based on prior agent divergence, the *physical* effectiveness of VRAM flushing is treated as partially established, as the baseline RTX 3050 hardware implicitly zero-initialized pages before simulated tests could extract them.
- **Hardware-Specific Neutrality:** No remanence was observed under the RTX 3050 patched configuration. System applicability relies heavily on specific hardware-driver configurations deployed in the cloud.
- **AgentDojo Out-of-Distribution Rigidity:** While continuous ranking generalized flawlessly to external benchmarks, rigidly fixed internal thresholds yielded a complete threshold-transfer failure (1.0000 FPR on AgentDojo benign cases). This highlights the brittleness of static multi-plane thresholding.

### Remaining Non-Research Tasks
- Submission formatting for target venue (e.g., IEEE S&P / USENIX).
- Final typo/grammar checks on the LaTeX source code.
- Final compression of the dataset generation assets for supplementary materials.
