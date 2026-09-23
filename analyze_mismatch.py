import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gateway.tool_gateway import evaluate
from gateway.cpsi import compute_cpsi

def mismatch_matrix():
    with open("data/raw/eval_dataset.json") as f:
        dataset = json.load(f)
        
    identity = {
        "agent_id": "agent-eval",
        "tenant_id": "tenant-A",
        "authenticated_namespace": "namespace-A",
        "granted_privilege": "READ",
    }
    
    thresh = 0.40
    
    fps = []
    fns = []
    
    for call in dataset:
        is_malicious = call.pop("is_malicious")
        
        session = {
            "call_history": [], "block_count": 0, "total_calls": 0, "rvs_quarantined": 0,
            "perai": {"budget_used": 0.0, "estimation_errors": [], "call_costs": []},
            "cddi_peak": 0.0, "rvs_peak": 0.0
        }
        
        report = evaluate(identity, call, session)
        
        cpsi = compute_cpsi({
            "cddi_peak": report.get("cddi", 0.0),
            "rvs_peak": report.get("rvs", {}).get("rvs_score", 0.0) if report.get("rvs") else 0.0,
            "perai": {"budget_used": report["perai"].get("c_hat", 0.0)}
        })["cpsi_score"]
        
        call["is_malicious"] = is_malicious
        call["cpsi_computed"] = cpsi
        call["report_cddi"] = report.get("cddi", 0.0)
        call["report_rvs"] = report.get("rvs", {}).get("rvs_score", 0.0) if report.get("rvs") else 0.0
        call["report_chat"] = report["perai"].get("c_hat", 0.0)
        
        blocked = cpsi >= thresh
        
        if not is_malicious and blocked:
            fps.append(call)
        elif is_malicious and not blocked:
            fns.append(call)
            
    print(f"Total FPs (Benign blocked): {len(fps)}")
    print(f"Total FNs (Malicious allowed): {len(fns)}")
    
    print("\n--- Sample False Positives (Benign but Blocked) ---")
    for fp in fps[:5]:
        print(f"ID: {fp['call_id']}, Tool: {fp['tool']}, CPSI: {fp['cpsi_computed']:.4f}, CDDI: {fp['report_cddi']:.4f}, RVS: {fp['report_rvs']:.4f}, C_hat: {fp['report_chat']}")
        
    print("\n--- Sample False Negatives (Malicious but Allowed) ---")
    for fn in fns[:5]:
        print(f"ID: {fn['call_id']}, Tool: {fn['tool']}, CPSI: {fn['cpsi_computed']:.4f}, CDDI: {fn['report_cddi']:.4f}, RVS: {fn['report_rvs']:.4f}, C_hat: {fn['report_chat']}")
        print(f"   Details: ns={fn['requested_namespace']}, priv={fn['required_privilege']}, tgt={fn['target_tenant']}")

if __name__ == "__main__":
    mismatch_matrix()
