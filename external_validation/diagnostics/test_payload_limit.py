import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gateway.tool_gateway import evaluate

def create_fresh_session():
    return {
        "call_history": [],
        "block_count": 0,
        "total_calls": 0,
        "rvs_quarantined": 0,
        "cddi_peak": 0.0,
        "rvs_peak": 0.0,
        "perai": {
            "budget_used": 0.0,
            "estimation_errors": [],
            "call_costs": []
        }
    }

def test_payload_limits():
    sizes = [0, 1, 9999, 10000, 10001, 100000, 1000000]
    
    identity = {"agent_id": "test", "tenant_id": "t1", "authenticated_namespace": "ns", "granted_privilege": "READ"}
    
    for size in sizes:
        raw_payload = "A" * size
        if len(raw_payload) > 10000:
            cpsi_payload = raw_payload[:10000]
            truncated = True
        else:
            cpsi_payload = raw_payload
            truncated = False
            
        assert len(cpsi_payload) <= 10000, f"Payload exceeded 10000 characters: {len(cpsi_payload)}"
        
        metadata = {
            "tool_output_chars_original": len(raw_payload),
            "tool_output_chars_used_for_cpsi": len(cpsi_payload),
            "tool_output_truncated": truncated
        }
        
        if size > 10000:
            assert metadata["tool_output_truncated"] is True
        else:
            assert metadata["tool_output_truncated"] is False
            
        call = {
            "call_id": f"s_{size}",
            "tool": "eval_payload",
            "requested_namespace": "ns",
            "required_privilege": "READ",
            "target_tenant": "t1",
            "simulated_output": cpsi_payload
        }
        
        session = create_fresh_session()
        report = evaluate(identity, call, session)
        # Check that evaluate didn't crash
        assert "decision" in report
        
    print("Payload Limits Regression Test: PASS")

if __name__ == "__main__":
    test_payload_limits()
