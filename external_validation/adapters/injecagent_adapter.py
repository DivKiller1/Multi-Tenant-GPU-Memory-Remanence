import json
import os
import hashlib

def map_category(bench_type):
    if bench_type == "dh":
        return "privilege_escalation"  # Direct Harm
    elif bench_type == "ds":
        return "output_leakage"  # Data Stealing
    return "unmapped"

def process_file(filepath, bench_type):
    normalized = []
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found.")
        return normalized
        
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    for case in data:
        # InjecAgent format typically has:
        # id, user_prompt/user_case, attacker_prompt/attacker_case, etc.
        # It's an array of objects.
        case_id = str(case.get("id", case.get("case_id", "unknown")))
        
        # In InjecAgent, every case in test_cases_* is considered a valid attack scenario if an attacker prompt exists.
        # But we need to define ground_truth_attack. Since it's a security benchmark of prompt injections, 
        # usually all of them are attacks. If there's a benign baseline, we handle it. Let's assume all test_cases_* are attacks.
        
        raw_str = json.dumps(case, sort_keys=True)
        raw_hash = hashlib.sha256(raw_str.encode()).hexdigest()
        
        user_task = case.get("user_prompt", case.get("user_case", ""))
        attacker_content = case.get("attacker_prompt", case.get("attacker_case", ""))
        
        norm_rec = {
            "source": "InjecAgent",
            "external_id": case_id,
            "native_category": "direct_harm" if bench_type == "dh" else "data_stealing",
            "cpsi_category": map_category(bench_type),
            "ground_truth_attack": True, # These are injection test cases
            "user_task": user_task,
            "attack_content": attacker_content,
            "tool_context": json.dumps(case.get("tool_desc", case.get("tools", {}))),
            "raw_case_hash": raw_hash
        }
        norm_str = json.dumps(norm_rec, sort_keys=True)
        norm_rec["normalized_case_hash"] = hashlib.sha256(norm_str.encode()).hexdigest()
        normalized.append(norm_rec)
        
    return normalized

def build_injecagent():
    base_dir = "external_validation/sources/InjecAgent/data"
    
    dh_cases = process_file(f"{base_dir}/test_cases_dh_base.json", "dh")
    ds_cases = process_file(f"{base_dir}/test_cases_ds_base.json", "ds")
    
    all_cases = dh_cases + ds_cases
    
    os.makedirs("external_validation/normalized", exist_ok=True)
    with open("external_validation/normalized/injecagent_normalized.jsonl", "w") as f:
        for c in all_cases:
            f.write(json.dumps(c) + "\n")
            
    print(f"InjecAgent Normalized: {len(all_cases)} cases")

if __name__ == "__main__":
    build_injecagent()
