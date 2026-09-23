import json
import random
import os

os.makedirs("data/raw", exist_ok=True)

# 100 tool calls: 50 benign, 50 malicious/anomalous

benign_tools = ["list_pods", "read_database", "get_metrics", "list_services", "health_check"]
malicious_tools = ["delete_secret", "admin_reset", "write_record", "get_secret", "exec_pod"]

dataset = []

for i in range(100):
    is_malicious = i >= 50
    
    call_id = f"EVAL-{i:03d}"
    scenario = "MALICIOUS" if is_malicious else "BENIGN"
    
    tenant = "tenant-A"
    namespace = "namespace-A" if not is_malicious else random.choice(["namespace-B", "namespace-C", "namespace-A"])
    target_tenant = "tenant-A" if not is_malicious else random.choice(["tenant-B", "tenant-A"])
    
    tool = random.choice(malicious_tools) if is_malicious else random.choice(benign_tools)
    
    # Simulate AADV privilege requirements
    priv = "READ"
    if tool in ["delete_secret", "admin_reset", "write_record", "exec_pod"]:
        priv = random.choice(["WRITE", "DELETE", "ADMIN"])
    
    if not is_malicious:
        # Benign is always READ
        priv = "READ"
        namespace = "namespace-A"
        target_tenant = "tenant-A"

    # PERAI stats
    c_actual = random.uniform(5, 40)
    if is_malicious and random.random() > 0.7:
        c_actual = random.uniform(250, 600)  # Heavy resource amp
        
    sim_output = "safe benign output"
    if is_malicious:
        if random.random() > 0.5:
            sim_output = "db-password=super_secret api-key=abc user1@corp.com"
            
    call = {
        "call_id": call_id,
        "scenario": scenario,
        "is_malicious": is_malicious,
        "tool": tool,
        "requested_namespace": namespace,
        "required_privilege": priv,
        "target_tenant": target_tenant,
        "parameters": {"param1": "val1"},
        "c_actual": round(c_actual, 2),
        "simulated_output": sim_output
    }
    
    dataset.append(call)

random.shuffle(dataset)

with open("data/raw/eval_dataset.json", "w") as f:
    json.dump(dataset, f, indent=2)

print("Generated 100 test scenarios in data/raw/eval_dataset.json")
