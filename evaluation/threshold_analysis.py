import json
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, precision_recall_curve, auc, confusion_matrix, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate

def generate_diagnostics():
    os.makedirs("evaluation/results", exist_ok=True)
    os.makedirs("evaluation/results/figures", exist_ok=True)

    with open("data/raw/test_dataset.json") as f:
        dataset = json.load(f)
        
    identity = {
        "agent_id": "agent-eval",
        "tenant_id": "tenant-a",
        "authenticated_namespace": "namespace-a",
        "granted_privilege": "READ",
    }
    
    y_true = []
    cddi_scores = []
    rvs_scores = []
    perai_scores = []
    lr_scores = []
    cpsi_scores = []
    
    for call in dataset:
        is_malicious = call["ground_truth_attack"]
        y_true.append(1 if is_malicious else 0)
        
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
        
        cddi_scores.append(cddi)
        rvs_scores.append(rvs)
        perai_scores.append(perai_budget)
        lr_scores.append(lr)
        cpsi_scores.append(cpsi)
        
    y_true = np.array(y_true)
    cpsi_scores = np.array(cpsi_scores)
    cddi_scores = np.array(cddi_scores)
    rvs_scores = np.array(rvs_scores)
    perai_scores = np.array(perai_scores)
    lr_scores = np.array(lr_scores)
    
    benign_mask = (y_true == 0)
    malicious_mask = (y_true == 1)
    
    # ---------------------------------------------------------
    # 1. Threshold Sweep
    # ---------------------------------------------------------
    fpr_curve, tpr_curve, roc_thresholds = roc_curve(y_true, cpsi_scores)
    roc_auc = roc_auc_score(y_true, cpsi_scores)
    
    precision_curve, recall_curve, pr_thresholds = precision_recall_curve(y_true, cpsi_scores)
    pr_auc = auc(recall_curve, precision_curve)
    
    # We want a dense sweep for F1, FPR, etc.
    dense_thresholds = np.linspace(0, 1, 100)
    sweep_results = []
    for t in dense_thresholds:
        y_pred = (cpsi_scores >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        sweep_results.append({
            "threshold": float(t), "precision": precision, "recall": recall, 
            "f1": f1, "fpr": fpr, "fnr": fnr
        })
        
    with open("evaluation/results/threshold_analysis.json", "w") as f:
        json.dump(sweep_results, f, indent=2)
        
    # Plot ROC and PR
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(fpr_curve, tpr_curve, label=f'Max-CPSI (AUC = {roc_auc:.4f})')
    plt.xlabel('FPR')
    plt.ylabel('TPR (Recall)')
    plt.title('ROC Curve')
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.plot(recall_curve, precision_curve, label=f'Max-CPSI (PR-AUC = {pr_auc:.4f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend()
    plt.tight_layout()
    plt.savefig("evaluation/results/figures/roc_pr_curves.png")
    plt.close()
    
    # Plot Threshold sweeps
    t_vals = [r["threshold"] for r in sweep_results]
    plt.figure(figsize=(10, 6))
    plt.plot(t_vals, [r["precision"] for r in sweep_results], label='Precision')
    plt.plot(t_vals, [r["recall"] for r in sweep_results], label='Recall')
    plt.plot(t_vals, [r["f1"] for r in sweep_results], label='F1')
    plt.plot(t_vals, [r["fpr"] for r in sweep_results], label='FPR')
    plt.xlabel('Threshold')
    plt.ylabel('Score')
    plt.title('Threshold vs Metrics')
    plt.legend()
    plt.savefig("evaluation/results/figures/threshold_metrics.png")
    plt.close()

    # ---------------------------------------------------------
    # 2. Component Distribution Analysis
    # ---------------------------------------------------------
    def calc_stats(arr):
        if len(arr) == 0: return {}
        return {
            "mean": float(np.mean(arr)), "median": float(np.median(arr)), "std": float(np.std(arr)),
            "min": float(np.min(arr)), "max": float(np.max(arr)),
            "q25": float(np.percentile(arr, 25)), "q75": float(np.percentile(arr, 75)),
            "q90": float(np.percentile(arr, 90)), "q95": float(np.percentile(arr, 95)),
            "q99": float(np.percentile(arr, 99))
        }
        
    stats = {
        "benign": {
            "CDDI": calc_stats(cddi_scores[benign_mask]),
            "RVS": calc_stats(rvs_scores[benign_mask]),
            "PERAI": calc_stats(perai_scores[benign_mask]),
            "LR": calc_stats(lr_scores[benign_mask]),
            "CPSI": calc_stats(cpsi_scores[benign_mask])
        },
        "malicious": {
            "CDDI": calc_stats(cddi_scores[malicious_mask]),
            "RVS": calc_stats(rvs_scores[malicious_mask]),
            "PERAI": calc_stats(perai_scores[malicious_mask]),
            "LR": calc_stats(lr_scores[malicious_mask]),
            "CPSI": calc_stats(cpsi_scores[malicious_mask])
        }
    }
    
    with open("evaluation/results/component_statistics.json", "w") as f:
        json.dump(stats, f, indent=2)
        
    # Plot PERAI distribution
    plt.figure()
    plt.hist(perai_scores[benign_mask], bins=30, alpha=0.5, label='Benign PERAI')
    plt.hist(perai_scores[malicious_mask], bins=30, alpha=0.5, label='Malicious PERAI')
    plt.yscale('log')
    plt.xlabel('PERAI Score')
    plt.ylabel('Count (Log Scale)')
    plt.title('PERAI Distribution')
    plt.legend()
    plt.savefig("evaluation/results/figures/perai_distribution.png")
    plt.close()

    # ---------------------------------------------------------
    # 3. Max-Component Dominance
    # ---------------------------------------------------------
    def get_dominance(mask):
        cddi = cddi_scores[mask]
        rvs = rvs_scores[mask]
        perai = perai_scores[mask]
        lr = lr_scores[mask]
        cpsi = cpsi_scores[mask]
        
        dom = {"CDDI": 0, "RVS": 0, "PERAI": 0, "LR": 0, "Tie": 0}
        for i in range(len(cpsi)):
            val = cpsi[i]
            comps = []
            if val == cddi[i]: comps.append("CDDI")
            if val == rvs[i]: comps.append("RVS")
            if val == perai[i]: comps.append("PERAI")
            if val == lr[i]: comps.append("LR")
            
            if len(comps) > 1: dom["Tie"] += 1
            elif len(comps) == 1: dom[comps[0]] += 1
        return dom
        
    dominance = {
        "overall": get_dominance(np.ones(len(y_true), dtype=bool)),
        "benign": get_dominance(benign_mask),
        "malicious": get_dominance(malicious_mask)
    }
    
    with open("evaluation/results/component_dominance.json", "w") as f:
        json.dump(dominance, f, indent=2)

    # Output PERAI Specific Diagnostics
    print("=" * 60)
    print(" PERAI DIAGNOSTIC ANALYSIS")
    print("=" * 60)
    b_perai = perai_scores[benign_mask]
    m_perai = perai_scores[malicious_mask]
    print(f" Max Benign PERAI: {np.max(b_perai):.4f}")
    print(f" Min Malicious PERAI: {np.min(m_perai):.4f}")
    overlap = len(b_perai[b_perai >= np.min(m_perai)]) / len(b_perai) if len(b_perai) > 0 else 0
    print(f" Benign overlapping into Malicious Range: {overlap*100:.1f}%")
    print(f" Fraction of Benign driven by PERAI: {dominance['benign']['PERAI'] / len(b_perai)*100:.1f}%")
    
if __name__ == "__main__":
    generate_diagnostics()
