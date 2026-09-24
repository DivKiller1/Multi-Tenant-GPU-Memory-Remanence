import json
import os
import sys
import numpy as np
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate

def calculate_metrics(y_true, y_scores, threshold):
    auc_val = roc_auc_score(y_true, y_scores) if len(np.unique(y_true)) > 1 else 0.0
    precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_scores)
    pr_auc = auc(recall_curve, precision_curve) if len(np.unique(y_true)) > 1 else 0.0
    
    y_pred = [1 if score >= threshold else 0 for score in y_scores]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    return {
        "ROC-AUC": float(auc_val),
        "PR-AUC": float(pr_auc),
        "Precision": float(precision),
        "Recall": float(recall),
        "F1": float(f1),
        "FPR": float(fpr),
        "FNR": float(fnr),
        "TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn)
    }

def main():
    with open("evaluation/locked_cpsi_config.json") as f:
        config = json.load(f)
        
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
    scores = {
        "CDDI only": [],
        "RVS only": [],
        "PERAI only": [],
        "CDDI + RVS": [],
        "CDDI + PERAI": [],
        "Full CPSI": []
    }
    
    attack_types = []
    
    for call in dataset:
        is_malicious = call["ground_truth_attack"]
        attack_types.append(call["attack_type"])
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
        perai_budget = min(report["perai"].get("c_hat", 0.0) / 500.0, 1.0) # From CPSI compute logic
        lr = 0.0
        
        scores["CDDI only"].append(cddi)
        scores["RVS only"].append(rvs)
        scores["PERAI only"].append(perai_budget)
        scores["CDDI + RVS"].append(max(cddi, rvs))
        scores["CDDI + PERAI"].append(max(cddi, perai_budget))
        scores["Full CPSI"].append(max(cddi, rvs, perai_budget, lr))
        
    y_true = np.array(y_true)
    
    # Stratified analysis setup
    attack_types = np.array(attack_types)
    full_cpsi_scores = np.array(scores["Full CPSI"])
    
    results = {}
    for config_name, s in scores.items():
        results[config_name] = calculate_metrics(y_true, s, threshold)
        
    # Save results
    os.makedirs("evaluation/results", exist_ok=True)
    with open("evaluation/results/ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    # Terminal Output: Ablation Table
    print("## Ablation table")
    print("| Configuration | ROC-AUC | PR-AUC | Precision | Recall | F1 | FPR | FNR |")
    print("| ------------- | ------: | -----: | --------: | -----: | -: | --: | --: |")
    for c in ["CDDI only", "RVS only", "PERAI only", "CDDI + RVS", "CDDI + PERAI", "Full CPSI"]:
        res = results[c]
        print(f"| {c:<13} | {res['ROC-AUC']:7.4f} | {res['PR-AUC']:6.4f} | {res['Precision']:9.4f} | {res['Recall']:6.4f} | {res['F1']:4.4f} | {res['FPR']:4.4f} | {res['FNR']:4.4f} |")
        
    print("\n## Full CPSI confusion matrix")
    print(f"TP: {results['Full CPSI']['TP']}")
    print(f"TN: {results['Full CPSI']['TN']}")
    print(f"FP: {results['Full CPSI']['FP']}")
    print(f"FN: {results['Full CPSI']['FN']}")
    
    # Category level analysis
    print("\n## Category-Level Stratified Results (Full CPSI)")
    print(f"| Category | N | Recall | FPR |")
    print(f"| -------- | - | ------ | --- |")
    
    cats = np.unique(attack_types)
    for cat in cats:
        idx = np.where(attack_types == cat)[0]
        y_cat = y_true[idx]
        s_cat = full_cpsi_scores[idx]
        
        y_pred = [1 if s >= threshold else 0 for s in s_cat]
        
        tp, fp, tn, fn = 0, 0, 0, 0
        for i in range(len(idx)):
            if y_cat[i] == 1 and y_pred[i] == 1: tp += 1
            if y_cat[i] == 1 and y_pred[i] == 0: fn += 1
            if y_cat[i] == 0 and y_pred[i] == 1: fp += 1
            if y_cat[i] == 0 and y_pred[i] == 0: tn += 1
            
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        print(f"| {cat:<10} | {len(idx):<3} | {recall:6.4f} | {fpr:4.4f} |")

if __name__ == "__main__":
    main()
