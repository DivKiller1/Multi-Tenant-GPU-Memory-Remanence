import os
import glob
import json
import numpy as np
import random

def run_calibration():
    base_path = "c:\\Users\\divya\\Desktop\\MAJOR PROJECT-1\\external_validation\\results\\raw\\agentdojo"
    files = glob.glob(os.path.join(base_path, "*.json"))
    
    benign_scores = []
    malicious_scores = []
    
    for fpath in files:
        with open(fpath, 'r') as f:
            try:
                data = json.load(f)
                if not data:
                    continue
                # Aggregate max CPSI score for the episode
                max_cpsi = max([step['cpsi'] for step in data])
                episode_id = data[0]['episode_id']
                
                if "none_none" in episode_id:
                    benign_scores.append(max_cpsi)
                else:
                    malicious_scores.append(max_cpsi)
            except Exception:
                continue

    # 50% holdout for benign
    random.seed(42)
    random.shuffle(benign_scores)
    split_idx = len(benign_scores) // 2
    calibration_benign = benign_scores[:split_idx]
    test_benign = benign_scores[split_idx:]
    
    # Calculate threshold on calibration benign (95th percentile)
    threshold = np.percentile(calibration_benign, 95)
    
    # Calculate FPR on test benign
    fp = sum(1 for s in test_benign if s > threshold)
    fpr = fp / len(test_benign) if test_benign else 0.0
    
    # Calculate TPR on all malicious
    tp = sum(1 for s in malicious_scores if s > threshold)
    tpr = tp / len(malicious_scores) if malicious_scores else 0.0
    
    print(f"Total benign: {len(benign_scores)}, Total malicious: {len(malicious_scores)}")
    print(f"Calibrated Threshold (95th percentile of {len(calibration_benign)} benign): {threshold:.4f}")
    print(f"New FPR on remaining test benign ({len(test_benign)}): {fpr:.4f}")
    print(f"New TPR on malicious ({len(malicious_scores)}): {tpr:.4f}")

if __name__ == "__main__":
    run_calibration()
