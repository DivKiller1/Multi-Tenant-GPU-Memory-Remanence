# Final Paper Claim Audit

**Audit Date:** 2026-09-24

## 1. Scope
This audit systematically reviewed `PAPER_RESULTS_SECTION.md`, `THREAT_MODEL.md`, `PROGRESS_TRACKER.md`, and the root documentation to identify and rectify unsupported or overstated language.

## 2. Invalidated/Modified Language Changes
The following strict substitutions were enforced throughout the research corpus to ensure precise alignment with the empirical boundaries:

| Original/Draft Language | Final Replaced Language | Rationale |
|-------------------------|-------------------------|-----------|
| "Proves that CPSI..." | "Provides evidence that..." or "Demonstrates..." | The empirical results provide evidence under tested conditions, not formal mathematical proof for all workloads. |
| "Guarantees isolation..." | "Enforces verifiably safe isolation barriers..." | No system can guarantee absolute isolation against undisclosed hardware flaws; it enforces software-level admission barriers. |
| "Eliminates GPU leakage" | "Did not exhibit measurable remanence under the tested configuration" | The experiment yielded 0.0 LR specifically on an RTX 3050; this does not universally prove all GPU architectures are immune. |
| "State of the art" | *Removed entirely* | A subjective claim lacking standard benchmark baselines in the specific tenant-transition niche. |
| "Universally generalizes" | "Generalizes out-of-distribution without retraining" | Applied specifically to the ROC-AUC on the AgentDojo dataset, preserving the continuous metric finding while dropping the "universal" hyperbole. |
| "First agent firewall" | "Explicit coupling of these signals at the tenant-transition boundary" | Avoids easily falsifiable "first" claims in a rapidly crowding agent-security space. |
| "Negligible overhead" | "Mean TTSO was measured at 0.0860 ms" | Contextualized the latency with the exact measured millisecond metric instead of an ambiguous adjective. |

## 3. Retained Supported Strong Claims
- **"Exceptional continuous discrimination metric (ROC-AUC = 1.0000)"**: Kept, as it accurately reflects the exact mathematical outcome on the AgentDojo dataset using the correct sequential adapter.
- **"Uniquely prevented 58 unsafe Tenant-B admissions"**: Kept, as it explicitly derives from the `CROSS_PLANE_NOVELTY_AUDIT.md` programmatic set-difference output on a 500-case paired population.
- **"Complete threshold-transfer failure"**: Kept, as the empirical FPR on external test cases reached 1.0000, which objectively constitutes a transfer failure. 

## 4. Final Status
The paper draft has been scrubbed. All findings are explicitly constrained by phraseology such as "on the evaluated population", "under the tested configuration", and "observed cross-plane protections". No unsupported novelty claims remain.
