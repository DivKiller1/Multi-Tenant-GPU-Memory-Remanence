import json
import numpy as np
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, confusion_matrix

def bootstrap_metrics(y_true, y_scores, n_bootstrap=1000, seed=42):
    np.random.seed(seed)
    n = len(y_true)
    metrics = {"roc_auc": [], "pr_auc": [], "precision": [], "recall": [], "f1": [], "fpr": []}
    
    # Use frozen threshold from manifest
    with open("evaluation/results/cross_plane_ablation/threshold_manifest.json") as f:
        threshold = json.load(f)["E"]["selected_threshold"]

    for _ in range(n_bootstrap):
        idx = np.random.choice(n, n, replace=True)
        y_t = y_true[idx]
        y_s = y_scores[idx]
        
        if len(np.unique(y_t)) < 2:
            continue
            
        metrics["roc_auc"].append(roc_auc_score(y_t, y_s))
        metrics["pr_auc"].append(auc(*precision_recall_curve(y_t, y_s)[:2][::-1]))
        
        y_p = (y_s >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_t, y_p, labels=[0,1]).ravel()
        
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        metrics["precision"].append(prec)
        metrics["recall"].append(rec)
        metrics["f1"].append(f1)
        metrics["fpr"].append(fpr)
        
    return {k: (np.percentile(v, 2.5), np.percentile(v, 97.5)) for k, v in metrics.items()}

def bootstrap_auc_diff(y_true, y_s1, y_s2, n_bootstrap=1000, seed=42):
    np.random.seed(seed)
    n = len(y_true)
    diffs = []
    for _ in range(n_bootstrap):
        idx = np.random.choice(n, n, replace=True)
        y_t = y_true[idx]
        if len(np.unique(y_t)) < 2:
            continue
        auc1 = roc_auc_score(y_t, y_s1[idx])
        auc2 = roc_auc_score(y_t, y_s2[idx])
        diffs.append(auc1 - auc2)
    return np.percentile(diffs, 2.5), np.percentile(diffs, 97.5)

def main():
    with open("data/raw/test_dataset.json") as f:
        test_data = json.load(f)
        
    y_true = np.array([c["ground_truth_attack"] for c in test_data])
    
    # Internal component extraction
    cddi_scores = []
    perai_scores = []
    rvs_scores = []
    lr_scores = []
    
    for case in test_data:
        cddi = 1.0 if case["req_ns"] != case["auth_ns"] or case["target_tenant"] != case["auth_tenant"] else 0.0
        c_hat = case["c_actual"]
        perai = min(c_hat / 500.0, 1.0)
        rvs = 0.8 if "simulated_output" in case and ("password" in case["simulated_output"] or "api-key" in case["simulated_output"]) else 0.0
        lr = 0.0
        
        cddi_scores.append(cddi)
        perai_scores.append(perai)
        rvs_scores.append(rvs)
        lr_scores.append(lr)
        
    y_e = np.maximum.reduce([cddi_scores, rvs_scores, perai_scores, lr_scores])
    y_d1 = np.maximum.reduce([cddi_scores, perai_scores])
    
    ci_e = bootstrap_metrics(y_true, y_e)
    diff_ci = bootstrap_auc_diff(y_true, y_e, y_d1)
    
    print("Full CPSI CIs:")
    for k, v in ci_e.items():
        print(f"{k}: ({v[0]:.4f}, {v[1]:.4f})")
    print(f"AUC Diff (E - D1) CI: ({diff_ci[0]:.4f}, {diff_ci[1]:.4f})")

if __name__ == "__main__":
    main()
