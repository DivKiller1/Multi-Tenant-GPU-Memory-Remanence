import os
import sys
import requests
from kubernetes import client, config, watch

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")

def evaluate_pod_admission(tenant_id: str, pod_name: str):
    """
    Query the Semantic Gateway for the current CPSI score and determine
    if the Kubernetes Pod should be admitted to the GPU.
    """
    print(f"[{pod_name}] GPU Allocation requested by {tenant_id}")
    
    try:
        # Fetch current session state from the gateway
        resp = requests.get(f"{GATEWAY_URL}/session")
        if resp.status_code != 200:
            print(f"[{pod_name}] Failed to query gateway: {resp.text}")
            return False
            
        state = resp.json()
        
        # Calculate CPSI based on the current session state
        cddi_peak = state.get("cddi_peak", 0.0)
        rvs_peak = state.get("rvs_peak", 0.0)
        
        perai = state.get("perai", {})
        budget_used = perai.get("budget_used", 0.0)
        session_budget = 500.0
        budget_exhaustion = min(budget_used / session_budget, 1.0)
        
        cpsi_score = max(cddi_peak, rvs_peak, budget_exhaustion, 0.0)
        
        print(f"[{pod_name}] CPSI Evaluation:")
        print(f"  - CDDI Peak: {cddi_peak:.4f}")
        print(f"  - RVS Peak: {rvs_peak:.4f}")
        print(f"  - Budget Exhaustion: {budget_exhaustion:.4f}")
        print(f"  => CPSI = {cpsi_score:.4f}")
        
        if cpsi_score >= 0.40:
            print(f"[{pod_name}] => ADMISSION BLOCKED (CPSI >= 0.40). Requires VRAM sanitization first.")
            return False
        else:
            print(f"[{pod_name}] => ADMISSION ALLOWED. Safe to allocate GPU.")
            return True
            
    except Exception as e:
        print(f"[{pod_name}] Error connecting to Semantic Gateway: {e}")
        return False

def watch_pods():
    try:
        # Try to load in-cluster config if running inside a pod
        config.load_incluster_config()
    except config.ConfigException:
        # Fall back to local kubeconfig
        try:
            config.load_kube_config()
        except Exception as e:
            print(f"Failed to load kubeconfig: {e}")
            sys.exit(1)

    v1 = client.CoreV1Api()
    w = watch.Watch()
    
    print("Cross-Plane Orchestrator Initialized. Watching for Pod events...")
    
    for event in w.stream(v1.list_pod_for_all_namespaces):
        pod = event['object']
        event_type = event['type']
        
        if event_type == "ADDED":
            pod_name = pod.metadata.name
            tenant_id = pod.metadata.labels.get("tenant", "unknown-tenant") if pod.metadata.labels else "unknown-tenant"
            
            # Check if this pod requests a GPU
            requests_gpu = False
            for container in pod.spec.containers:
                resources = container.resources
                if resources and resources.limits and "nvidia.com/gpu" in resources.limits:
                    requests_gpu = True
                    break
            
            if requests_gpu:
                evaluate_pod_admission(tenant_id, pod_name)
                print("-" * 50)

if __name__ == "__main__":
    watch_pods()
