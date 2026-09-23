import time
import os
import sys
import statistics

# Ensure imports work from gateway
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway.cpsi import evaluate_admission

def benchmark_ttso(iterations=100):
    print("=" * 68)
    print(" TENANT TRANSITION SANITIZATION OVERHEAD (TTSO) BENCHMARK")
    print("=" * 68)
    
    # Measure baseline Python function call overhead
    base_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = 1 + 1
        t1 = time.perf_counter()
        base_times.append(t1 - t0)
    
    # Measure CPSI admission gate overhead
    gate_times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = evaluate_admission()
        t1 = time.perf_counter()
        gate_times.append(t1 - t0)
        
    avg_base_ms = (sum(base_times) / iterations) * 1000
    avg_gate_ms = (sum(gate_times) / iterations) * 1000
    std_dev_ms = statistics.stdev([t * 1000 for t in gate_times])
    
    net_overhead_ms = avg_gate_ms - avg_base_ms
    
    print(f" Iterations         : {iterations}")
    print(f" Mean TTSO Latency  : {net_overhead_ms:.4f} ms")
    print(f" Std Dev Latency    : {std_dev_ms:.4f} ms")
    print(f" 99th Percentile    : {sorted([t * 1000 for t in gate_times])[int(0.99*iterations)]:.4f} ms")
    print("=" * 68)

if __name__ == "__main__":
    benchmark_ttso()
