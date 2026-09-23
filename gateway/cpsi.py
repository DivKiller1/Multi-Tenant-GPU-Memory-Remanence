"""
cpsi.py -- Phase 3: Cross-Plane Security Index (CPSI)
Role: Compute the unified security score for Tenant B Admission Gating.

CPSI = max(
    CDDI_PEAK,
    RVS_PEAK,
    BUDGET_EXHAUSTION_FRAC,
    LR_HARDWARE
)

Enforcement at Admission Gate:
  If CPSI >= 0.40 -> REQUIRE HARD SANITIZATION (VRAM zeroing)
  If CPSI < 0.40  -> ADMIT IMMEDIATELY (Soft context switch)
"""

from typing import Any
import os
import json

def compute_cpsi(session_state: dict[str, Any], lr_hardware: float = 0.0) -> dict[str, Any]:
    """
    Computes the CPSI score based on session history and hardware baseline.
    """
    cddi_peak = session_state.get("cddi_peak", 0.0)
    rvs_peak = session_state.get("rvs_peak", 0.0)
    
    perai = session_state.get("perai", {})
    budget_used = perai.get("budget_used", 0.0)
    session_budget = 500.0  # From PERAI
    budget_exhaustion = min(budget_used / session_budget, 1.0)
    
    cpsi_score = max(cddi_peak, rvs_peak, budget_exhaustion, lr_hardware)
    
    decision = "REQUIRE_SANITIZATION" if cpsi_score >= 0.40 else "ADMIT_IMMEDIATELY"
    
    return {
        "cpsi_score": cpsi_score,
        "cddi_peak": cddi_peak,
        "rvs_peak": rvs_peak,
        "budget_exhaustion": budget_exhaustion,
        "lr_hardware": lr_hardware,
        "decision": decision
    }

def evaluate_admission(session_file: str = "gateway/session_state.json", lr_hardware: float = 0.0) -> dict[str, Any]:
    if not os.path.exists(session_file):
        return compute_cpsi({}, lr_hardware)
        
    with open(session_file) as f:
        state = json.load(f)
        
    return compute_cpsi(state, lr_hardware)

if __name__ == "__main__":
    import sys
    result = evaluate_admission()
    print("=" * 68)
    print(" CPSI ADMISSION GATE EVALUATION")
    print("=" * 68)
    print(f" CDDI Peak         : {result['cddi_peak']:.4f}")
    print(f" RVS Peak          : {result['rvs_peak']:.4f}")
    print(f" Budget Exhaustion : {result['budget_exhaustion']:.4f}")
    print(f" Hardware LR       : {result['lr_hardware']:.4f}")
    print(f" --------------------------------")
    print(f" CPSI SCORE        : {result['cpsi_score']:.4f}")
    print(f" ADMISSION DECISION: {result['decision']}")
    print("=" * 68)
    sys.exit(1 if result['decision'] == "REQUIRE_SANITIZATION" else 0)
