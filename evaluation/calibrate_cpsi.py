import json
import os
import sys
import hashlib
from datetime import datetime
import numpy as np
from sklearn.metrics import roc_auc_score, precision_recall_curve, f1_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate
from gateway.cpsi import compute_cpsi

def calibrate():
    with open("data/raw/calibration_dataset.json") as f:
        dataset = json.load(f)
        
    identity = {
        "agent_id": "agent-eval",
        "tenant_id": "tenant-a",
        "authenticated_namespace": "namespace-a",
        "granted_privilege": "READ",
    }
    
    print("=" * 60)
    print(" CPSI CALIBRATION")
    print("=" * 60)
    print(f" Loaded {len(dataset)} calibration scenarios.")
    
    y_true = []
    y_scores = []
    
    for call in dataset:
        is_malicious = call["ground_truth_attack"]
        
        req = {
            "call_id": call["scenario_id"],
            "tool": call["tool"],
            "requested_namespace": call["req_ns"],
            "required_privilege": call["req_priv"],
            "target_tenant": call.get("target_tenant", "tenant-a"),
            "c_actual": call["c_actual"],
            "simulated_output": call["simulated_output"]
        }
        
        session = {
            "call_history": [], "block_count": 0, "total_calls": 0, "rvs_quarantined": 0,
            "perai": {"budget_used": 0.0, "estimation_errors": [], "call_costs": []},
            "cddi_peak": 0.0, "rvs_peak": 0.0
        }
        
        report = evaluate(identity, req, session)
        
        cpsi = compute_cpsi({
            "cddi_peak": report.get("cddi", 0.0),
            "rvs_peak": report.get("rvs", {}).get("rvs_score", 0.0) if report.get("rvs") else 0.0,
            # Pass budget fraction properly as it would be accumulated
            "perai": {"budget_used": report["perai"].get("c_hat", 0.0)}
        })["cpsi_score"]
        
        y_true.append(1 if is_malicious else 0)
        y_scores.append(cpsi)
        
    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    
    auc = roc_auc_score(y_true, y_scores)
    print(f" Calibration ROC-AUC: {auc:.4f}")
    
    # Calibrate threshold to maximize F1
    precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
    
    # Calculate F1 score for each threshold
    f1_scores = 2 * recall * precision / (recall + precision + 1e-10)
    
    best_idx = np.argmax(f1_scores)
    best_thresh = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
    best_f1 = f1_scores[best_idx]
    
    print(f" Objective: Maximize F1-score")
    print(f" Best Threshold: {best_thresh:.4f}")
    print(f" Calibration F1: {best_f1:.4f}")
    
    with open("data/raw/calibration_dataset.json", "rb") as f:
        cal_hash = hashlib.sha256(f.read()).hexdigest()
        
    config = {
        "model_version": "1.0.0-calibrated",
        "cpsi_formulation": "max(CDDI, RVS, PERAI, LR)",
        "weights": "fixed_architecture",
        "threshold": float(best_thresh),
        "calibration_seed": 42,
        "calibration_dataset_hash": cal_hash,
        "generation_version": "v2",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    os.makedirs("evaluation", exist_ok=True)
    with open("evaluation/locked_cpsi_config.json", "w") as f:
        json.dump(config, f, indent=2)
        
    print(" -> Saved locked configuration to evaluation/locked_cpsi_config.json")
    print("=" * 60)

if __name__ == "__main__":
    calibrate()
