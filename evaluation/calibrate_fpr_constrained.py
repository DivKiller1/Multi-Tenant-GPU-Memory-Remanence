import json
import os
import sys
import hashlib
from datetime import datetime
import numpy as np
from sklearn.metrics import confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate

def calibrate():
    with open("data/raw/calibration_dataset.json") as f:
        dataset = json.load(f)
        
    identity = {
        "agent_id": "agent-eval",
        "tenant_id": "tenant-a",
        "authenticated_namespace": "namespace-a",
        "granted_privilege": "READ",
    }
    
    y_true = []
    cpsi_scores = []
    
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
        
        cddi = report.get("cddi", 0.0)
        rvs = report.get("rvs", {}).get("rvs_score", 0.0) if report.get("rvs") else 0.0
        perai_budget = min(report["perai"].get("c_hat", 0.0) / 500.0, 1.0)
        lr = 0.0
        
        cpsi = max(cddi, rvs, perai_budget, lr)
        
        y_true.append(1 if is_malicious else 0)
        cpsi_scores.append(cpsi)
        
    y_true = np.array(y_true)
    cpsi_scores = np.array(cpsi_scores)
    
    # Pre-declared constraints
    constraints = [0.01, 0.05, 0.10]
    locked_configs = {}
    
    thresholds = np.linspace(0, 1, 1000)
    for target_fpr in constraints:
        best_thresh = 1.0
        best_recall = -1.0
        best_prec = -1.0
        
        for t in thresholds:
            y_pred = (cpsi_scores >= t).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
            
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            
            if fpr <= target_fpr:
                # Tie-breaking: maximize recall, then precision, then highest threshold
                if recall > best_recall:
                    best_recall = recall
                    best_prec = precision
                    best_thresh = t
                elif recall == best_recall:
                    if precision > best_prec:
                        best_prec = precision
                        best_thresh = t
                    elif precision == best_prec:
                        if t > best_thresh:
                            best_thresh = t
                            
        f1 = 2 * best_prec * best_recall / (best_prec + best_recall) if (best_prec + best_recall) > 0 else 0.0
        
        with open("data/raw/calibration_dataset.json", "rb") as f:
            cal_hash = hashlib.sha256(f.read()).hexdigest()
            
        locked_configs[f"FPR_{int(target_fpr*100)}"] = {
            "target_fpr": target_fpr,
            "selected_threshold": float(best_thresh),
            "calibration_recall": float(best_recall),
            "calibration_precision": float(best_prec),
            "calibration_f1": float(f1),
            "selection_rule": "maximize recall, then precision, then highest threshold",
            "dataset_hash": cal_hash,
            "seed": 42,
            "model_formulation": "max(CDDI, RVS, PERAI, LR)"
        }
        
    os.makedirs("evaluation", exist_ok=True)
    with open("evaluation/locked_fpr_configs.json", "w") as f:
        json.dump(locked_configs, f, indent=2)

if __name__ == "__main__":
    calibrate()
