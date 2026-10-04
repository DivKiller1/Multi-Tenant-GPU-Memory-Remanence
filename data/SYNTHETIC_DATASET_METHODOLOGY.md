# Synthetic Dataset Generation Methodology

This document outlines the methodology for the deterministic generation of the 1,500-case synthetic dataset used for independent evaluation (500 calibration cases and 1,000 held-out test cases), as well as the 500-case tenant-transition dataset.

## Generation Methodology & Threat Model

The dataset is programmatically generated to model specific threat vectors at the intersection of agent-tool interactions and physical resource state. 

### Scenario Construction
Each scenario represents an execution trace containing:
1. **Agent State**: Memory, instruction prompt, and tool-call payloads.
2. **Resource Metrics**: Memory consumption, CPU cycles, token counts.
3. **Infrastructure State**: Simulated hardware state representations, including GPU VRAM artifacts and physical identity markers.

### Threat Model
The dataset is built around three primary attack surfaces:
1. **Prompt & Instruction Injection**: Scenarios where a malicious user prompt overrides system instructions.
2. **Cross-Tenant State Bleeding**: Specifically modeled in the tenant-transition dataset. An attacker in Tenant A deliberately leaks state (e.g., lexical artifacts in GPU memory), which Tenant B attempts to recover post-transition.
3. **Resource Exhaustion & Quota Evasion**: Attacks targeting the agent's token limits and local computational constraints.

## Class Imbalance Rationale (84% Malicious Base Rate)
The test set contains 839 malicious and 161 benign scenarios. This deliberate class imbalance (84% malicious) reflects an assumption of a high-risk operational environment or an adversarial evaluation setting where the majority of execution traces are designed to probe the system's defensive boundaries. Because the objective of the evaluation is to measure recall against a dense array of novel attacks, benign scenarios serve primarily as a calibration check for false positives rather than a majority class. No random or majority-class baseline is used; performance figures must be interpreted relative to this density of attacks.

## Limitations and Exclusions
While the synthetic dataset is structurally rigorous, several limitations must be acknowledged:

1. **Not Representative of Production Traffic Distributions**: The dataset artificially inflates the density and diversity of attacks. Real-world deployment traffic would likely exhibit a ~0.1% to 5% attack base rate rather than 84%. False Positive Rate (FPR) estimates derived from this dataset may not scale linearly to production without recalibration.
2. **Bounded by Known Attack Patterns**: The deterministic generation relies on predefined attack templates and behaviors. Novel attack paradigms (e.g., emergent multi-agent collusion or zero-day vulnerabilities in the underlying LLM itself) are not represented.
3. **Simulated Hardware State**: The dataset uses simulated representations of physical state (e.g., emulated lexical remanence) rather than raw hardware memory dumps. While useful for modeling system response to threshold triggers, it does not perfectly replicate the physical noise of actual GPU telemetry.
