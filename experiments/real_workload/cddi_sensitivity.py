import json, numpy as np
from pathlib import Path
from vllm import LLM, SamplingParams

S = json.loads(Path('/tmp/sharegpt_1000.json').read_text())
llm = LLM(model="TinyLlama/TinyLlama-1.1B-Chat-v1.0", max_model_len=2048)
p = SamplingParams(temperature=0.7, max_tokens=256)

def cddi_components(ct, ot):
    if len(ct) < 2: return 0.0, 0.0
    g = np.array(ct, float)
    cv = np.std(g) / (np.mean(g) + 1e-9)
    a = np.array(ot, float)
    z = abs(a - np.mean(a)) / (np.std(a) + 1e-9) if len(a) > 1 else np.array([0.])
    return float(cv), float(np.mean(z))

components = []
for i, s in enumerate(S[:200]):
    ps = [t['value'] for t in s.get('conversations', []) if t.get('from') == 'human']
    if not ps: continue
    ct, ot = [], []
    for q in ps[:5]:
        import time; t0 = time.time()
        o = llm.generate([q[:512]], p)
        ct.append(time.time() - t0); ot.append(len(o[0].outputs[0].token_ids))
    cv, tz = cddi_components(ct, ot)
    components.append({'cv': cv, 'token_z': tz})
    if i % 20 == 0: print(f'[{i+1}/200]')

# Sweep alpha
results = {}
for alpha in np.arange(0.0, 1.1, 0.1):
    alpha = round(float(alpha), 1)
    scores = [alpha * c['cv'] + (1 - alpha) * c['token_z'] for c in components]
    p95 = float(np.percentile(scores, 95))
    fpr = sum(1 for s in scores if s > p95) / len(scores)
    results[str(alpha)] = {'p95_threshold': round(p95, 4), 'fpr_at_p95': round(fpr, 4)}
    print(f'alpha={alpha:.1f}  p95={p95:.4f}  fpr={fpr:.4f}')

Path('results/cddi_sensitivity.json').write_text(json.dumps({'alpha_sweep': results, 'n_sessions': len(components)}, indent=2))
