"""
tenant_b_probe.py — Phase 1: GPU Remanence Baseline
Role: Tenant B (Probe)

Independently allocates uninitialized GPU memory and scans it for the
victim's known byte pattern. Computes Lexical Recovery (LR) as defined:

  LR = (number of matching pattern occurrences * len(pattern)) / total_bytes_scanned

Engineering constraints enforced:
  - PYTORCH_NO_CUDA_MEMORY_CACHING=1 must be set by the caller.
  - torch.cuda.empty_cache() called before allocation.
  - torch.empty() used — deliberately uninitialized so we observe whatever
    the CUDA driver returns, not a Python/PyTorch zero-fill.
  - The tensor is pulled to CPU for byte-level scanning (GPU-side pattern
    matching is out of scope for Phase 1).
  - Results are printed in a machine-parseable format for logging.
"""

import sys
import time
import torch


# ---------------------------------------------------------------------------
# Constants — must match tenant_a_victim.py exactly
# ---------------------------------------------------------------------------

PAYLOAD_PATTERN = b"TENANT_A_SECRET_PAYLOAD_"
ALLOC_BYTES = 256 * 1024 * 1024      # 256 MB
ALLOC_ELEMENTS = ALLOC_BYTES // 4    # float32 elements


def compute_lexical_recovery(raw_bytes: bytes, pattern: bytes) -> dict:
    """
    Scan raw_bytes for occurrences of pattern using overlapping search.
    Returns a dict with match_count, LR, and metadata.
    """
    match_count = 0
    start = 0
    pattern_len = len(pattern)

    while True:
        idx = raw_bytes.find(pattern, start)
        if idx == -1:
            break
        match_count += 1
        start = idx + 1  # overlapping search

    total_bytes = len(raw_bytes)
    lr = (match_count * pattern_len) / total_bytes if total_bytes > 0 else 0.0

    return {
        "pattern": pattern.decode("ascii"),
        "pattern_len_bytes": pattern_len,
        "total_bytes_scanned": total_bytes,
        "match_count": match_count,
        "lexical_recovery_lr": lr,
    }


def main() -> int:
    if not torch.cuda.is_available():
        print("[PROBE] ERROR: CUDA not available.")
        return 1

    device = torch.device("cuda:0")
    print(f"[PROBE] CUDA device: {torch.cuda.get_device_name(device)}")

    probe_start_ts = time.time()
    print(f"[PROBE] Probe start timestamp: {probe_start_ts:.6f}")

    # Step 1: Evict any locally cached blocks — we want raw driver pages.
    torch.cuda.empty_cache()
    print("[PROBE] Allocator cache cleared.")

    # Step 2: Allocate uninitialized tensor of the same size as the victim's
    # allocation. With PYTORCH_NO_CUDA_MEMORY_CACHING=1, this triggers a fresh
    # cudaMalloc — the driver decides whether to zero pages or not.
    tensor = torch.empty(ALLOC_ELEMENTS, dtype=torch.float32, device=device)
    alloc_ts = time.time()
    print(f"[PROBE] Allocated {ALLOC_BYTES / 1024 / 1024:.0f} MB on {device} "
          f"at t={alloc_ts:.6f}.")

    # Step 3: Pull to CPU for byte-level inspection.
    cpu_tensor = tensor.cpu()
    # Reinterpret float32 memory as raw bytes.
    raw_bytes = cpu_tensor.view(torch.uint8).numpy().tobytes()
    print(f"[PROBE] Tensor transferred to CPU. Scanning {len(raw_bytes)} bytes...")

    # Step 4: Compute Lexical Recovery.
    result = compute_lexical_recovery(raw_bytes, PAYLOAD_PATTERN)

    # Step 5: Report results in machine-parseable format.
    print("\n[PROBE] ===== PHASE 1 LEXICAL RECOVERY RESULT =====")
    for key, val in result.items():
        print(f"[PROBE] {key}: {val}")

    lr = result["lexical_recovery_lr"]

    # Step 6: Apply acceptance criteria from PROGRESS_TRACKER.md
    if lr > 0.01:
        verdict = "POSITIVE — H1 CONFIRMED (LR > 1%)"
    elif lr >= 0.001:
        verdict = "INCONCLUSIVE — marginal signal (0.1% <= LR <= 1%)"
    else:
        verdict = "NEGATIVE — H1 NOT CONFIRMED ON THIS HARDWARE (LR < 0.1%)"

    print(f"[PROBE] verdict: {verdict}")
    print("[PROBE] ===================================================\n")

    # Step 7: Clean up.
    del tensor, cpu_tensor
    torch.cuda.empty_cache()
    print("[PROBE] Tensor released. Process exiting.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
