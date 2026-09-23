import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.rvs import evaluate_rvs
from gateway.cpsi import compute_cpsi

def simulate_sanitization():
    print("=" * 68)
    print(" VRAM SANITIZATION EFFECTIVENESS ON RVS METRIC")
    print("=" * 68)
    
    # Pre-sanitization: simulated VRAM leak
    leaked_vram = "db-password=super_secret_2026 api-key=sk-abc12345 tenant-B admin"
    rvs_pre = evaluate_rvs(leaked_vram)
    
    print(f" [PRE-SANITIZATION] Extracted Lexical Buffer (N=64 bytes)")
    print(f"   SR Score   : {rvs_pre['sr_score']:.4f}")
    print(f"   SSR Score  : {rvs_pre['ssr_score']:.4f}")
    print(f"   RVS Total  : {rvs_pre['rvs_score']:.4f}  (Quarantine threshold = 0.30)")
    
    # Hardware Driver Zeroing pass (as proven in Phase 1)
    print("\n -> Initiating Verifiable VRAM Sanitization (cudaFree sim)")
    sanitized_vram = "\x00" * len(leaked_vram)
    
    # Post-sanitization
    rvs_post = evaluate_rvs(sanitized_vram)
    print(f"\n [POST-SANITIZATION] Extracted Lexical Buffer (N=64 bytes)")
    print(f"   SR Score   : {rvs_post['sr_score']:.4f}")
    print(f"   SSR Score  : {rvs_post['ssr_score']:.4f}")
    print(f"   RVS Total  : {rvs_post['rvs_score']:.4f}")
    
    print("=" * 68)
    if rvs_post['rvs_score'] == 0.0:
        print(" CONCLUSION: Mathematical drop to 0.0 confirmed.")
    print("=" * 68)

if __name__ == "__main__":
    simulate_sanitization()
