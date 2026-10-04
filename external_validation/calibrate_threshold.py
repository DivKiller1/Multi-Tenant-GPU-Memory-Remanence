import json
import glob
import numpy as np
from sklearn.metrics import roc_auc_score
import os

def run_calibration():
    files = glob.glob('external_validation/results/raw/agentdojo/*.json')
    
    benign_scores = []
    attack_scores = []
    
    for f in files:
        if 'checkpoint.json' in f:
            continue
        try:
            with open(f, 'r') as file:
                data = json.load(file)
                if not data:
                    continue
                # Episode CDDI score is max over all steps
                episode_cddi = max([step.get('cddi', 0.0) for step in data])
                
                # 'none_none' indicates benign in AgentDojo dataset filenames
                if '_none_none.json' in f:
                    benign_scores.append(episode_cddi)
                else:
                    attack_scores.append(episode_cddi)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            continue

    print(f"Loaded {len(benign_scores)} benign and {len(attack_scores)} attack episodes.")
    
    # Split benign 50/50
    # Use fixed seed for reproducible split
    np.random.seed(42)
    benign_scores = np.array(benign_scores)
    np.random.shuffle(benign_scores)
    
    calib_benign = benign_scores[:62]
    test_benign = benign_scores[62:]
    
    threshold_calibrated = np.percentile(calib_benign, 95)
    
    attacks = np.array(attack_scores)
    
    recall = np.sum(attacks > threshold_calibrated) / len(attacks)
    fpr = np.sum(test_benign > threshold_calibrated) / len(test_benign)
    
    y_true = np.concatenate([np.ones(len(attacks)), np.zeros(len(benign_scores))])
    y_scores = np.concatenate([attacks, benign_scores])
    roc_auc = roc_auc_score(y_true, y_scores)
    
    print(f"Threshold (95th percentile of calib): {threshold_calibrated}")
    print(f"Recall (attacks >= threshold): {recall}")
    print(f"FPR (test benign >= threshold): {fpr}")
    print(f"ROC-AUC (full set): {roc_auc}")
    
    # Update external_metrics.json
    metrics_file = 'external_validation/results/external_metrics.json'
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
        
    metrics['AgentDojo_calibrated'] = {
        "N": len(attacks) + len(benign_scores),
        "Attacks": len(attacks),
        "Benign_calibration_set": 62,
        "Benign_test_set": len(test_benign),
        "threshold_calibrated": threshold_calibrated,
        "threshold_source": "95th percentile of held-out AgentDojo benign calibration set (n=62)",
        "ROC-AUC": roc_auc,
        "Recall": recall,
        "FPR": fpr,
        "note": "Threshold recalibrated from internal synthetic distribution to AgentDojo benign distribution. FPR measured on held-out test benign set (n=62), not calibration set."
    }
    
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Updated {metrics_file}")

if __name__ == '__main__':
    run_calibration()
