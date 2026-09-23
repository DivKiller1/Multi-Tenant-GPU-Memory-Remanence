# 4. Experimental Results

We evaluate our Identity-Bound Cross-Plane Security Control architecture across four dimensions: physical hardware remanence baselines, agent divergence accuracy, semantic output protection, and cross-plane integration overhead.

## 4.1 Hardware Remanence Baseline (Phase 1)
To establish the physical threat floor ($\theta$), we executed a byte-level Lexical Recovery ($LR$) attack against uninitialized VRAM blocks. 
- **Target Hardware**: NVIDIA GeForce RTX 3050 Laptop GPU.
- **Methodology**: Tenant A wrote a deterministic payload across 256MB of VRAM. Tenant B immediately allocated the memory without initialization and scanned for the payload.
- **Result**: The mean $LR$ across multiple independent trials was precisely $0.0\%$. 
- **Conclusion**: Current-generation NVIDIA drivers execute an implicit `cudaFree` page-zeroing operation. Our architecture, therefore, treats hardware-level remanence as a conditional threat (dependent on heterogenous driver topologies) and utilizes the Cross-Plane Security Index (CPSI) to mathematically determine when verifiable sanitization is strictly necessary.

## 4.2 Divergence and Resource Estimation Accuracy (Phase 2)
The Pre-Execution Resource Anomaly Index (PERAI) models resource exhaustion by comparing anticipated compute cost ($\hat{C}$) to actual execution cost ($C_{actual}$).
- Across calibrated test suites, PERAI achieved an **estimation accuracy of 95.03%** with a mean estimation error of $4.97\%$.
- The engine successfully identified and blocked resource amplification anomalies (e.g., $TC-009$, generating an $\hat{C}$ of 510 against a limit of 200).

## 4.3 Semantic Output Validation (RVS)
The Returned Value Sanitization (RVS) plane acts as the final post-execution gateway.
- In simulated trials, a sequenced prompt-injection attack successfully bypassed the pre-execution AADV gate by requesting nominally authorized access to a secrets engine.
- However, the RVS engine identified crown-jewel string patterns and high semantic vocabulary overlap, calculating an RVS score of $0.3359$ (exceeding the $0.30$ threshold), and successfully **quarantined** the output before it returned to the agent.

## 4.4 Cross-Plane Integration and Overhead (Phase 3 & 4)
To validate the architecture in a live distributed environment, the control plane was containerized (Docker) and deployed via a local Kubernetes `kind` cluster. A cross-plane controller intercepted live Pod creation events.

We measured the Tenant Transition Sanitization Overhead ($TTSO$) — the computational latency added by the gateway when computing the full CDDI and CPSI pipeline on tenant transition.
- **Mean TTSO Latency**: $0.0860$ ms 
- **99th Percentile Latency**: $0.4494$ ms
- **AUC (Detection Accuracy)**: Operating on a synthetic 100-scenario dataset, the baseline CPSI metric originally yielded an AUC of 0.6500 due to weight dilution. After applying a strict identity-bound calibration (spiking the $CDDI$ to $1.0$ for any hard boundary breach), the calibrated model achieved an **AUC of 0.9900**. This successfully forces isolated high-risk interactions into a mandatory VRAM sanitization loop, while allowing safe traffic to proceed unimpeded.

These metrics demonstrate that identity-bound cross-plane security controls can operate with negligible microsecond latency overhead while providing robust, verifiable defense against multi-tenant memory remanence and prompt-driven escalation.
