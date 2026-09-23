"""
tenant_a_victim.py — Phase 1: GPU Remanence Baseline
Role: Tenant A (Victim)

Writes a deterministic ASCII byte-pattern payload into GPU VRAM using
an uninitialized tensor allocation, synchronises the device, then exits.

Engineering constraints enforced:
  - PYTORCH_NO_CUDA_MEMORY_CACHING=1 must be set in the environment before
    this process starts (enforced by run_baseline.sh / caller).
  - torch.cuda.empty_cache() called before allocation to evict any cached
    blocks back to the CUDA driver.
  - Payload written via torch.empty() (uninitialized) then filled with a
    known repeating byte pattern — this is what the probe will search for.
  - torch.cuda.synchronize() ensures the write reaches physical VRAM before
    the process exits.
  - The tensor reference is explicitly deleted and empty_cache() is called
    again so the CUDA driver — not PyTorch's caching allocator — holds the
    decision about whether to zero the pages before reassignment.
"""

import sys
import time
import torch


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Repeating ASCII payload: "TENANT_A_SECRET_PAYLOAD_" (24 bytes) repeated.
# Chosen to be human-readable, deterministic, and statistically distinguishable
# from random VRAM noise.
PAYLOAD_PATTERN = b"TENANT_A_SECRET_PAYLOAD_"

# Allocation size: 256 MB worth of bytes represented as float32 elements.
# float32 = 4 bytes, so 256 MB = 256 * 1024 * 1024 / 4 = 67_108_864 elements.
ALLOC_BYTES = 256 * 1024 * 1024
ALLOC_ELEMENTS = ALLOC_BYTES // 4  # float32

# How many times to repeat the pattern to fill the tensor byte buffer.
PATTERN_REPEATS = ALLOC_BYTES // len(PAYLOAD_PATTERN)


def main() -> int:
    if not torch.cuda.is_available():
        print("[VICTIM] ERROR: CUDA not available. Cannot run GPU remanence experiment.")
        return 1

    device = torch.device("cuda:0")
    print(f"[VICTIM] CUDA device: {torch.cuda.get_device_name(device)}")

    # Step 1: Evict any PyTorch-cached blocks back to the CUDA driver.
    torch.cuda.empty_cache()
    print(f"[VICTIM] Allocator cache cleared.")

    # Step 2: Allocate uninitialized float32 tensor (avoids zero-fill overhead
    # and mirrors what a real workload allocation looks like to the CUDA driver).
    tensor = torch.empty(ALLOC_ELEMENTS, dtype=torch.float32, device=device)
    print(f"[VICTIM] Allocated {ALLOC_BYTES / 1024 / 1024:.0f} MB on {device}.")

    # Step 3: Build the payload byte sequence and copy it into the tensor's
    # memory as raw bytes via a CPU byte-tensor then view-cast.
    payload_bytes = PAYLOAD_PATTERN * PATTERN_REPEATS
    # Pad or trim to exact byte count (handles edge cases from integer division).
    payload_bytes = (payload_bytes + PAYLOAD_PATTERN)[:ALLOC_BYTES]

    cpu_byte_tensor = torch.frombuffer(bytearray(payload_bytes), dtype=torch.uint8)
    # Reinterpret as float32 so it fits our pre-allocated tensor shape.
    cpu_float_view = cpu_byte_tensor.view(torch.float32)
    tensor.copy_(cpu_float_view)
    print(f"[VICTIM] Payload written to GPU tensor. Pattern: {PAYLOAD_PATTERN!r}")

    # Step 4: Synchronise — ensures all GPU writes are complete before we exit.
    torch.cuda.synchronize(device)
    print("[VICTIM] CUDA synchronise complete. Payload is in physical VRAM.")

    # Step 5: Record the timestamp so the probe can compute time-delta if needed.
    release_ts = time.time()
    print(f"[VICTIM] Release timestamp: {release_ts:.6f}")

    # Step 6: Explicitly release — delete tensor reference and return pages to
    # the CUDA driver. With PYTORCH_NO_CUDA_MEMORY_CACHING=1 the caching
    # allocator is disabled, so cudaFree is called immediately.
    del tensor
    torch.cuda.empty_cache()
    print("[VICTIM] Tensor released. Process exiting now.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
