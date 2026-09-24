import os
import subprocess
import json
from datetime import datetime

def run(cmd, cwd):
    print(f"Running: {cmd} in {cwd}")
    subprocess.run(cmd, cwd=cwd, shell=True, check=True)

def setup_external():
    dirs = [
        "external_validation/sources",
        "external_validation/adapters",
        "external_validation/normalized",
        "external_validation/runners",
        "external_validation/evaluation",
        "external_validation/figures",
        "external_validation/results"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        
    # Clone InjecAgent
    if not os.path.exists("external_validation/sources/InjecAgent"):
        run("git clone https://github.com/uiuc-kang-lab/InjecAgent.git", cwd="external_validation/sources")
        
    # Clone AgentDojo
    if not os.path.exists("external_validation/sources/agentdojo"):
        run("git clone https://github.com/ethz-spylab/agentdojo.git", cwd="external_validation/sources")

    def get_git_info(repo_path):
        commit = subprocess.check_output("git rev-parse HEAD", cwd=repo_path, shell=True).decode().strip()
        return commit
        
    manifest = {
        "sources": [
            {
                "name": "InjecAgent",
                "repository": "https://github.com/uiuc-kang-lab/InjecAgent.git",
                "commit_hash": get_git_info("external_validation/sources/InjecAgent"),
                "retrieval_date": datetime.utcnow().isoformat() + "Z",
                "license": "MIT",
                "dataset_files": [
                    "data/user_cases.jsonl",
                    "data/attacker_cases_dh.jsonl", 
                    "data/attacker_cases_ds.jsonl",
                    "data/test_cases_dh_base.json",
                    "data/test_cases_ds_base.json"
                ],
                "benchmark_version": "1.0"
            },
            {
                "name": "AgentDojo",
                "repository": "https://github.com/ethz-spylab/agentdojo.git",
                "commit_hash": get_git_info("external_validation/sources/agentdojo"),
                "retrieval_date": datetime.utcnow().isoformat() + "Z",
                "license": "MIT",
                "dataset_files": ["agentdojo/benchmark/"],
                "benchmark_version": "main"
            }
        ]
    }
    
    with open("external_validation/source_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    setup_external()
