import json
import random
import os
import hashlib

def generate_dataset(seed: int = 42):
    random.seed(seed)
    
    # Tool sets
    legit_tools = ["get_pods", "read_database", "inference_run", "list_services", "health_check"]
    sensitive_tools = ["get_secret", "delete_secret", "exec_pod", "admin_reset"]
    
    unique_scenarios = {}
    
    i = 0
    while len(unique_scenarios) < 1500:
        is_malicious = random.random() < 0.5
        
        # Base benign parameters
        auth_tenant = "tenant-a"
        target_tenant = "tenant-a"
        req_ns = "namespace-a"
        auth_ns = "namespace-a"
        req_priv = "READ"
        auth_priv = "READ"
        tool = random.choice(legit_tools)
        # Use integers for c_actual to make deduplication exact
        c_actual = random.randint(5, 45)
        simulated_output = "legitimate data response"
        
        attack_type = "None"
        
        if is_malicious:
            attack_choices = [
                "cross_tenant", "namespace_violation", "privilege_escalation", 
                "resource_amplification", "output_leakage", "composite"
            ]
            attack = random.choice(attack_choices)
            attack_type = attack
            
            if attack == "cross_tenant":
                target_tenant = "tenant-b"
            elif attack == "namespace_violation":
                req_ns = "namespace-b"
            elif attack == "privilege_escalation":
                req_priv = random.choice(["WRITE", "ADMIN", "DELETE"])
                tool = random.choice(sensitive_tools)
            elif attack == "resource_amplification":
                c_actual = random.randint(250, 800)
            elif attack == "output_leakage":
                simulated_output = "db-password=super_secret_123"
                tool = random.choice(sensitive_tools)
            elif attack == "composite":
                target_tenant = "tenant-b"
                req_priv = "ADMIN"
                c_actual = random.randint(300, 700)
                simulated_output = "api-key=sk-12345"
                tool = random.choice(sensitive_tools)
        else:
            if random.random() < 0.1:
                tool = "get_secret"
                simulated_output = "api-key=sk-legit"
                req_priv = "READ"
                
        scenario = {
            "auth_tenant": auth_tenant,
            "target_tenant": target_tenant,
            "auth_ns": auth_ns,
            "req_ns": req_ns,
            "auth_priv": auth_priv,
            "req_priv": req_priv,
            "tool": tool,
            "c_actual": float(c_actual),
            "simulated_output": simulated_output,
            "attack_type": attack_type,
            "ground_truth_attack": 1 if is_malicious else 0
        }
        
        # Deduplicate
        norm_str = json.dumps(scenario, sort_keys=True)
        if norm_str not in unique_scenarios:
            unique_scenarios[norm_str] = scenario
            i += 1
            
    scenarios = list(unique_scenarios.values())
    random.shuffle(scenarios)
    
    # Assign scenario IDs after shuffling
    for idx, s in enumerate(scenarios):
        s["scenario_id"] = f"TC-{idx:04d}"
    
    calibration_set = scenarios[:500]
    test_set = scenarios[500:]
    
    os.makedirs("data/raw", exist_ok=True)
    
    with open("data/raw/calibration_dataset.json", "w") as f:
        json.dump(calibration_set, f, indent=2)
        
    with open("data/raw/test_dataset.json", "w") as f:
        json.dump(test_set, f, indent=2)
        
    def get_hash(filepath):
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
            
    cal_hash = get_hash("data/raw/calibration_dataset.json")
    test_hash = get_hash("data/raw/test_dataset.json")
        
    print("=" * 60)
    print(" DATASET GENERATION SUMMARY")
    print("=" * 60)
    print(f" Total generated : 1500")
    print(f" Calibration     : 500   (Hash: {cal_hash})")
    print(f" Test            : 1000  (Hash: {test_hash})")
    print(f" Random Seed     : {seed}")
    
    # Overlap check
    cal_ids = set([s["scenario_id"] for s in calibration_set])
    test_ids = set([s["scenario_id"] for s in test_set])
    overlap = cal_ids.intersection(test_ids)
    print(f" ID overlap      : {len(overlap)}")
    
    def norm(s):
        c = dict(s)
        del c["scenario_id"]
        return json.dumps(c, sort_keys=True)
        
    cal_norms = set([norm(s) for s in calibration_set])
    test_norms = set([norm(s) for s in test_set])
    norm_overlap = cal_norms.intersection(test_norms)
    print(f" Exact duplicate overlap: {len(norm_overlap)}")
    print("=" * 60)

if __name__ == "__main__":
    generate_dataset()
