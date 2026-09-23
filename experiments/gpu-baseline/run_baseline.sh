#!/usr/bin/env bash
# run_baseline.sh — Phase 1: GPU Remanence Baseline Orchestrator
#
# Executes Tenant A (victim) and Tenant B (probe) as SEPARATE OS processes.
# Process isolation is mandatory — PyTorch's internal allocator cache must NOT
# bridge the two processes. PYTORCH_NO_CUDA_MEMORY_CACHING=1 forces the CUDA
# driver to manage page reuse decisions, not the framework caching layer.
#
# Usage: bash run_baseline.sh [run_id]
#   run_id defaults to 1 if not provided.

set -euo pipefail

RUN_ID="${1:-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

VICTIM_LOG="${LOG_DIR}/victim_run${RUN_ID}.log"
PROBE_LOG="${LOG_DIR}/probe_run${RUN_ID}.log"

echo "========================================================"
echo " Phase 1 GPU Remanence Baseline — Run ${RUN_ID}"
echo " $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "========================================================"

# Enforce allocator bypass for BOTH processes via environment variable.
# This disables PyTorch's caching allocator so cudaFree/cudaMalloc decisions
# are delegated to the CUDA driver — the layer we are actually measuring.
export PYTORCH_NO_CUDA_MEMORY_CACHING=1
echo "[HARNESS] PYTORCH_NO_CUDA_MEMORY_CACHING=${PYTORCH_NO_CUDA_MEMORY_CACHING}"

# -----------------------------------------------------------------------
# Step 1: Run Tenant A (Victim) — write payload, sync, exit.
# -----------------------------------------------------------------------
echo ""
echo "[HARNESS] --- VICTIM START (PID will be shown below) ---"
python "${SCRIPT_DIR}/tenant_a_victim.py" 2>&1 | tee "${VICTIM_LOG}"
VICTIM_EXIT=${PIPESTATUS[0]}
echo "[HARNESS] Victim exited with code: ${VICTIM_EXIT}"

if [ "${VICTIM_EXIT}" -ne 0 ]; then
    echo "[HARNESS] FATAL: Victim process failed. Aborting experiment."
    exit "${VICTIM_EXIT}"
fi

VICTIM_EXIT_TS=$(date +%s%N)
echo "[HARNESS] Victim exit timestamp (ns): ${VICTIM_EXIT_TS}"

# -----------------------------------------------------------------------
# Step 2: Immediately execute Tenant B (Probe) — no sleep, no delay.
# Minimising time delta maximises probability of observing remanence.
# -----------------------------------------------------------------------
echo ""
echo "[HARNESS] --- PROBE START ---"
python "${SCRIPT_DIR}/tenant_b_probe.py" 2>&1 | tee "${PROBE_LOG}"
PROBE_EXIT=${PIPESTATUS[0]}
echo "[HARNESS] Probe exited with code: ${PROBE_EXIT}"

# -----------------------------------------------------------------------
# Step 3: Summarise run.
# -----------------------------------------------------------------------
echo ""
echo "========================================================"
echo " Run ${RUN_ID} Complete"
echo " Victim log : ${VICTIM_LOG}"
echo " Probe log  : ${PROBE_LOG}"
echo " LR result  : $(grep 'lexical_recovery_lr' "${PROBE_LOG}" || echo 'not found')"
echo " Verdict    : $(grep 'verdict:' "${PROBE_LOG}" || echo 'not found')"
echo "========================================================"

exit "${PROBE_EXIT}"
