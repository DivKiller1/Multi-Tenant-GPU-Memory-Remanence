import json
import os
import glob
import hashlib

def build_agentdojo():
    base_dir = "external_validation/sources/agentdojo/runs"
    # Let's pick a specific model run to form our external episode set
    model_runs = glob.glob(f"{base_dir}/gpt-4o-2024-05-13/**/*.json", recursive=True)
    
    normalized = []
    
    for filepath in model_runs:
        with open(filepath, 'r') as f:
            try:
                data = json.load(f)
            except:
                continue
                
        # AgentDojo runs have a structure like:
        # { "task_id": "...", "injection_id": "...", "messages": [...], "tool_calls": [...] }
        # Or similar. We will just extract the trace.
        
        # If "injection_task_0" etc is not "none", it's an attack.
        is_attack = False
        parts = filepath.replace("\\", "/").split("/")
        
        # Structure: runs/model/suite/user_task/injection_strategy/injection_task.json
        # e.g. runs/gpt-4o/banking/user_task_0/important_instructions/injection_task_0.json
        if "none.json" not in filepath and "none" not in parts[-2:]:
            is_attack = True
            
        case_id = f"agentdojo_" + "_".join(parts[-4:]).replace(".json", "")
        
        raw_str = json.dumps(data, sort_keys=True)
        raw_hash = hashlib.sha256(raw_str.encode()).hexdigest()
        
        # We try to extract user and attacker strings
        user_task = str(data.get("task", ""))
        attacker_content = str(data.get("injection", ""))
        
        norm_rec = {
            "source": "AgentDojo",
            "external_id": case_id,
            "native_category": "prompt_injection" if is_attack else "benign",
            "cpsi_category": "privilege_escalation" if is_attack else "benign",
            "ground_truth_attack": is_attack,
            "user_task": user_task,
            "attack_content": attacker_content,
            "tool_context": json.dumps(data.get("tools", {})),
            "episode_id": case_id,
            "raw_case_hash": raw_hash
        }
        
        norm_str = json.dumps(norm_rec, sort_keys=True)
        norm_rec["normalized_case_hash"] = hashlib.sha256(norm_str.encode()).hexdigest()
        normalized.append(norm_rec)
        
    os.makedirs("external_validation/normalized", exist_ok=True)
    with open("external_validation/normalized/agentdojo_normalized.jsonl", "w") as f:
        for c in normalized:
            f.write(json.dumps(c) + "\n")
            
    print(f"AgentDojo Normalized: {len(normalized)} cases")

if __name__ == "__main__":
    build_agentdojo()
