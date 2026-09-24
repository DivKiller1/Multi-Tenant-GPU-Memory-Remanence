import json
import os
import sys
import numpy as np
from sklearn.metrics import confusion_matrix, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate

def evaluate_fpr():
    with open("evaluation/locked_fpr_configs.json") as f:
        configs = json.load(f)
        
    with open("data/raw/test_dataset.json") as f:
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
    
    roc_auc = roc_auc_score(y_true, cpsi_scores)
    
    results = {}
    for key, conf in configs.items():
        t = conf["selected_threshold"]
        y_pred = (cpsi_scores >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
        
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        results[key] = {
            "target_fpr": conf["target_fpr"],
            "frozen_threshold": t,
            "test_roc_auc": float(roc_auc),
            "test_recall": float(recall),
            "test_fpr": float(fpr),
            "test_f1": float(f1)
        }
        
    with open("evaluation/results/fpr_constrained_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("=" * 60)
    print(" FPR-CONSTRAINED CALIBRATION TEST RESULTS")
    print("=" * 60)
    for k, v in results.items():
        print(f" Constraint: FPR <= {v['target_fpr']*100:.0f}%")
        print(f" Frozen Threshold: {v['frozen_threshold']:.4f}")
        print(f" Test ROC-AUC: {v['test_roc_auc']:.4f}")
        print(f" Test Recall: {v['test_recall']:.4f}")
        print(f" Test FPR: {v['test_fpr']:.4f}")
        print(f" Test F1: {v['test_f1']:.4f}")
        print("-" * 30)

if __name__ == "__main__":
    evaluate_fpr()
