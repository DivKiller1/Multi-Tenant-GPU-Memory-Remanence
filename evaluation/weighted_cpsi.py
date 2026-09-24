import json
import os
import sys
import hashlib
from datetime import datetime
import numpy as np
from scipy.optimize import minimize
from sklearn.metrics import confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate

def weighted_calibrate():
    with open("data/raw/calibration_dataset.json") as f:
        dataset = json.load(f)
        
    identity = {
        "agent_id": "agent-eval",
        "tenant_id": "tenant-a",
        "authenticated_namespace": "namespace-a",
        "granted_privilege": "READ",
    }
    
    y_true = []
    X = []
    
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
        
        y_true.append(1 if is_malicious else 0)
        X.append([cddi, rvs, perai_budget, lr])
        
    y_true = np.array(y_true)
    X = np.array(X)
    
    # We fit a logistic loss function with non-negative constraints on weights
    def loss_func(w):
        # w[0..3] = weights, w[4] = intercept
        logits = np.dot(X, w[:4]) + w[4]
        # sigmoid
        probs = 1 / (1 + np.exp(-np.clip(logits, -50, 50)))
        # log loss
        epsilon = 1e-15
        probs = np.clip(probs, epsilon, 1 - epsilon)
        return -np.mean(y_true * np.log(probs) + (1 - y_true) * np.log(1 - probs))

    # Initial guess
    w0 = np.array([1.0, 1.0, 1.0, 1.0, -1.0])
    
    # Non-negative bounds for weights, unconstrained for intercept
    bounds = [(0, None), (0, None), (0, None), (0, None), (None, None)]
    
    res = minimize(loss_func, w0, bounds=bounds, method='L-BFGS-B')
    
    opt_w = res.x
    print(f" Optimized Weights (CDDI, RVS, PERAI, LR): {opt_w[:4]}")
    print(f" Optimized Intercept: {opt_w[4]}")
    
    # Compute scores to find threshold
    logits = np.dot(X, opt_w[:4]) + opt_w[4]
    y_scores = 1 / (1 + np.exp(-logits))
    
    # Pick F1-maximizing threshold on calibration set
    best_thresh = 0.5
    best_f1 = -1.0
    for t in np.linspace(0, 1, 100):
        y_pred = (y_scores >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t
            
    with open("data/raw/calibration_dataset.json", "rb") as f:
        cal_hash = hashlib.sha256(f.read()).hexdigest()
            
    config = {
        "model_version": "1.0.0-weighted",
        "cpsi_formulation": "sigmoid(w1*CDDI + w2*RVS + w3*PERAI + w4*LR + intercept)",
        "weights": {
            "CDDI": float(opt_w[0]),
            "RVS": float(opt_w[1]),
            "PERAI": float(opt_w[2]),
            "LR": float(opt_w[3])
        },
        "intercept": float(opt_w[4]),
        "threshold": float(best_thresh),
        "calibration_seed": 42,
        "calibration_objective": "Non-negative logistic regression, threshold F1-maximized",
        "calibration_dataset_hash": cal_hash,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    os.makedirs("evaluation", exist_ok=True)
    with open("evaluation/locked_weighted_config.json", "w") as f:
        json.dump(config, f, indent=2)

if __name__ == "__main__":
    weighted_calibrate()
