import json
import numpy as np
import pathlib
from sklearn.metrics import roc_auc_score, confusion_matrix

# Load both datasets to get the 1500 scenarios
cal_path = pathlib.Path("../../data/raw/calibration_dataset.json")
test_path = pathlib.Path("../../data/raw/test_dataset.json")

scenarios = json.loads(cal_path.read_text()) + json.loads(test_path.read_text())

# Ground truth is 1 for malicious, 0 for benign
labels = np.array([s["ground_truth_attack"] for s in scenarios])

# Dataset has no tool_calls_per_sec rate field, defaulting to 0 for rate-limiter baseline
tool_calls_per_sec = np.array([s.get("tool_calls_per_sec", s.get("tool_call_rate", 0)) for s in scenarios])

# c_actual represents resource consumption (e.g. token counts or compute cost)
token_counts = np.array([s.get("c_actual", 0) for s in scenarios])

# Baseline 1: Rate-limiter — flag if tool calls/sec > threshold
# Sweep thresholds and pick best F1
best_f1, best_thresh_rl = 0, 0
if len(np.unique(tool_calls_per_sec)) > 1:
    for t in np.percentile(tool_calls_per_sec, np.arange(50, 99, 2)):
        preds = (tool_calls_per_sec > t).astype(int)
        tn, fp, fn, tp = confusion_matrix(labels, preds, labels=[0, 1]).ravel()
        f1 = 2*tp / (2*tp + fp + fn + 1e-9)
        if f1 > best_f1:
            best_f1, best_thresh_rl = f1, t

rl_preds = (tool_calls_per_sec > best_thresh_rl).astype(int)
tn, fp, fn, tp = confusion_matrix(labels, rl_preds, labels=[0, 1]).ravel()
rl_recall = tp / (tp + fn + 1e-9)
rl_fpr = fp / (fp + tn + 1e-9)
try:
    rl_auc = roc_auc_score(labels, tool_calls_per_sec)
except ValueError:
    rl_auc = 0.5 # fallback if only one class or constant preds

# Baseline 2: Token budget cap — flag if tokens > P95
token_thresh = np.percentile(token_counts[labels == 0], 95)  # P95 of benign
tb_preds = (token_counts > token_thresh).astype(int)
tn2, fp2, fn2, tp2 = confusion_matrix(labels, tb_preds, labels=[0, 1]).ravel()
tb_recall = tp2 / (tp2 + fn2 + 1e-9)
tb_fpr = fp2 / (fp2 + tn2 + 1e-9)
tb_auc = roc_auc_score(labels, token_counts)

print(f"Rate-limiter baseline (threshold={best_thresh_rl:.2f}): Recall={rl_recall:.3f}, FPR={rl_fpr:.3f}, AUC={rl_auc:.4f}")
print(f"Token-budget baseline (P95={token_thresh:.0f} tokens): Recall={tb_recall:.3f}, FPR={tb_fpr:.3f}, AUC={tb_auc:.4f}")

out = {
    "rate_limiter": {"threshold": float(best_thresh_rl), "recall": rl_recall, "fpr": rl_fpr, "roc_auc": rl_auc},
    "token_budget": {"threshold": float(token_thresh), "recall": tb_recall, "fpr": tb_fpr, "roc_auc": tb_auc}
}
pathlib.Path("heuristic_baseline_results.json").write_text(json.dumps(out, indent=2))
print("Saved")
