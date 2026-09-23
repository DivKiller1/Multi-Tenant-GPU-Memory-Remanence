import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.tool_gateway import evaluate
from gateway.cpsi import compute_cpsi

def generate_roc_curve():
    print("=" * 68)
    print(" CPSI ROC/AUC GENERATOR")
    print("=" * 68)
    
    with open("data/raw/eval_dataset.json") as f:
        dataset = json.load(f)
        
    thresholds = [i/100.0 for i in range(0, 105, 5)]
    
    identity = {
        "agent_id": "agent-eval",
        "tenant_id": "tenant-A",
        "authenticated_namespace": "namespace-A",
        "granted_privilege": "READ",
    }
    
    print(f" Loaded {len(dataset)} scenarios.")
    print(" Calculating TPR / FPR across thresholds...\n")
    print(f" {'Threshold':<10} | {'TPR':<8} | {'FPR':<8}")
    print("-" * 35)
    
    tpr_fpr_points = []
    
    for thresh in thresholds:
        true_pos = 0   # Malicious correctly blocked
        false_pos = 0  # Benign incorrectly blocked
        true_neg = 0   # Benign correctly allowed
        false_neg = 0  # Malicious incorrectly allowed
        
        for call in dataset:
            is_malicious = call.pop("is_malicious")
            
            # Simulate a fresh session for each call to isolate the evaluation
            session = {
                "call_history": [], "block_count": 0, "total_calls": 0, "rvs_quarantined": 0,
                "perai": {"budget_used": 0.0, "estimation_errors": [], "call_costs": []},
                "cddi_peak": 0.0, "rvs_peak": 0.0
            }
            
            report = evaluate(identity, call, session)
            
            # Extract final simulated CPSI
            cpsi = compute_cpsi({
                "cddi_peak": report.get("cddi", 0.0),
                "rvs_peak": report.get("rvs", {}).get("rvs_score", 0.0) if report.get("rvs") else 0.0,
                "perai": {"budget_used": report["perai"].get("c_hat", 0.0)}
            })["cpsi_score"]
            
            call["is_malicious"] = is_malicious # restore
            
            blocked = cpsi >= thresh
            
            if is_malicious and blocked:
                true_pos += 1
            elif not is_malicious and blocked:
                false_pos += 1
            elif not is_malicious and not blocked:
                true_neg += 1
            elif is_malicious and not blocked:
                false_neg += 1
                
        tpr = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
        fpr = false_pos / (false_pos + true_neg) if (false_pos + true_neg) > 0 else 0
        
        tpr_fpr_points.append((fpr, tpr))
        print(f" {thresh:<10.2f} | {tpr:<8.2f} | {fpr:<8.2f}")

    # Compute rough AUC (Trapezoidal rule)
    auc = 0.0
    # sort by FPR to integrate
    tpr_fpr_points.sort(key=lambda x: x[0])
    for i in range(1, len(tpr_fpr_points)):
        fpr1, tpr1 = tpr_fpr_points[i-1]
        fpr2, tpr2 = tpr_fpr_points[i]
        auc += (fpr2 - fpr1) * (tpr1 + tpr2) / 2
        
    print("-" * 35)
    print(f" => Estimated AUC = {auc:.4f}")
    print("=" * 68)

if __name__ == "__main__":
    generate_roc_curve()
