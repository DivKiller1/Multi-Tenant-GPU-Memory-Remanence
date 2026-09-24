# Final Reproducibility Audit

**Audit Date:** 2026-09-24

## 1. Traceability
- **Code Version / Infrastructure:** Evaluated using the repository's deterministic `gateway` pipeline modules (`cddi.py`, `perai.py`, `rvs.py`).
- **Seed Values:** Base seed `42` was used for primary synthetic datasets. Base seed `42001` was programmatically derived and used for the `tenant_transition_test.json` generation.
- **Data Hashes:** 
  - Calibration: `d142d76587d6928e1d743a6f9edc9cbba1f80ecdf95e4064d8dbda2f9c8d10b7`
  - Internal Test: `67a3f01c80be0bd4447d96200fb16f46a2a07c4b679622d64f165e317c91e7c5`
  - Tenant Transition Test: `f8a427c1a5da9886ec51815aff7f0bfd9f994bf373b088eff97ad9b9a0bbc3b3`

## 2. Integrity Checks Verified
- **Zero Overlap:** The `generate_tenant_transitions` function mechanically enforces and verifies zero scenario-ID, exact, and normalized duplicate overlap between all three main datasets.
- **Frozen Configurations:** Continuous-score continuous metrics (ROC-AUC) were generated strictly independently of threshold calculations. 
- **Calibration/Test Split:** Threshold operating points were calibrated *strictly* on the 500-case calibration set using a deterministic fallback objective (FPR <= 5% -> Max F1) and then frozen into `threshold_manifest.json` before being evaluated against out-of-distribution external and internal test cases.

## 3. External Execution Reproducibility
- **AgentDojo Replay:** The external trace adaptation uses deterministic state-isolation execution via Python subprocess. The original traces (`AgentDojo`) represent stochastic LLM generation, but the CPSI evaluation over those traces is mechanically deterministic.
- **State Isolation:** The `test_state_bleed.py` mechanical regression test passes, ensuring that session sequences, budgets, and recurrent context dictionaries are deep-reset between episode bounds.
- **Payload Limits:** The `test_payload_limit.py` regression verifies that payloads are safely capped at `MAX_TOOL_OUTPUT_CHARS = 10000`, persisting `tool_output_truncated=true` metadata rather than failing unexpectedly.

## 4. Execution Scope
The audit must distinguish between deterministic scoring and stochastic generation:
**Deterministic:** The gateway preprocessing, CDDI pattern extraction, dataset construction script, threshold fallbacks, ablation scoring loops, and evaluation metrics are 100% deterministic over frozen inputs.
**Stochastic:** The exact agent execution (responses, payloads) mapped in the external AgentDojo environments were naturally stochastic. The metrics provided reflect exact scoring on the specific artifacts downloaded and evaluated on the audit date.
