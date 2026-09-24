import json
import os
import sys
import numpy as np
from sklearn.metrics import confusion_matrix, roc_auc_score, auc, precision_recall_curve

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate

def evaluate_weighted():
    with open("evaluation/locked_weighted_config.json") as f:
        config = json.load(f)
        
    w = config["weights"]
    weights = np.array([w["CDDI"], w["RVS"], w["PERAI"], w["LR"]])
    intercept = config["intercept"]
    threshold = config["threshold"]
    
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
    attack_types = []
    
    for call in dataset:
        is_malicious = call["ground_truth_attack"]
        attack_types.append(call["attack_type"])
        
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
        
        x = np.array([cddi, rvs, perai_budget, lr])
        logit = np.dot(x, weights) + intercept
        cpsi = 1 / (1 + np.exp(-logit))
        
        y_true.append(1 if is_malicious else 0)
        cpsi_scores.append(cpsi)
        
    y_true = np.array(y_true)
    cpsi_scores = np.array(cpsi_scores)
    attack_types = np.array(attack_types)
    
    roc_auc = roc_auc_score(y_true, cpsi_scores)
    precision_curve, recall_curve, _ = precision_recall_curve(y_true, cpsi_scores)
    pr_auc = auc(recall_curve, precision_curve)
    
    y_pred = (cpsi_scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    results = {
        "ROC-AUC": float(roc_auc),
        "PR-AUC": float(pr_auc),
        "Precision": float(precision),
        "Recall": float(recall),
        "F1": float(f1),
        "FPR": float(fpr),
        "FNR": float(fnr),
        "TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn)
    }
    
    os.makedirs("evaluation/results", exist_ok=True)
    with open("evaluation/results/weighted_cpsi_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("=" * 60)
    print(" WEIGHTED CPSI INDEPENDENT TEST RESULTS")
    print("=" * 60)
    print(f" ROC-AUC: {roc_auc:.4f}")
    print(f" PR-AUC: {pr_auc:.4f}")
    print(f" Precision: {precision:.4f}")
    print(f" Recall: {recall:.4f}")
    print(f" F1: {f1:.4f}")
    print(f" FPR: {fpr:.4f}")
    print(f" FNR: {fnr:.4f}")
    
    # Category level
    print("\n## Category-Level Stratified Results (Weighted CPSI)")
    cats = np.unique(attack_types)
    cat_res = {}
    for cat in cats:
        idx = np.where(attack_types == cat)[0]
        y_cat = y_true[idx]
        p_cat = y_pred[idx]
        
        tp_cat, fp_cat, tn_cat, fn_cat = 0, 0, 0, 0
        for i in range(len(idx)):
            if y_cat[i] == 1 and p_cat[i] == 1: tp_cat += 1
            if y_cat[i] == 1 and p_cat[i] == 0: fn_cat += 1
            if y_cat[i] == 0 and p_cat[i] == 1: fp_cat += 1
            if y_cat[i] == 0 and p_cat[i] == 0: tn_cat += 1
            
        r = tp_cat / (tp_cat + fn_cat) if (tp_cat + fn_cat) > 0 else 0.0
        f = fp_cat / (fp_cat + tn_cat) if (fp_cat + tn_cat) > 0 else 0.0
        print(f"| {cat:<10} | {len(idx):<3} | {r:6.4f} | {f:4.4f} |")
        cat_res[cat] = {"Recall": float(r), "FPR": float(f), "N": int(len(idx))}
        
    with open("evaluation/results/weighted_category_results.json", "w") as f:
        json.dump(cat_res, f, indent=2)

if __name__ == "__main__":
    evaluate_weighted()
