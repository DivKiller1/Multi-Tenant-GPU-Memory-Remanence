import numpy as np
import json
import pathlib

np.random.seed(42)
n_total = 500
n_positive = 58
n_bootstrap = 10000

# Known benign FPR from internal eval (0.021 = 2.1%)
# I will check paper if different, but using 0.021 as provided.
benign_fpr = 0.021

# Bootstrap CI on the 58/500 proportion
data = np.array([1]*n_positive + [0]*(n_total - n_positive))
boot_props = [np.mean(np.random.choice(data, size=n_total, replace=True))
              for _ in range(n_bootstrap)]
ci_low, ci_high = np.percentile(boot_props, [2.5, 97.5])
observed = n_positive / n_total

# One-sided p-value vs benign FPR
null_dist = np.random.binomial(n_total, benign_fpr, n_bootstrap) / n_total
p_value = np.mean(null_dist >= observed)

print(f"H5 result: {n_positive}/{n_total} = {observed:.3f}")
print(f"95% CI: [{ci_low*100:.2f}%, {ci_high*100:.2f}%]")
print(f"vs benign FPR {benign_fpr:.3f}: p={p_value:.4f}")

out = {
    "n": n_total, 
    "positives": n_positive, 
    "proportion": observed,
    "ci_95_low": ci_low, 
    "ci_95_high": ci_high,
    "benign_fpr_comparison": benign_fpr, 
    "p_value": float(p_value),
    "n_bootstrap": n_bootstrap
}

pathlib.Path("bootstrap_ci_results.json").write_text(json.dumps(out, indent=2))
print("Saved")
