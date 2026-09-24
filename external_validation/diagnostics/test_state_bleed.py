import sys
import os
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

def update_session(session, report, call):
    session["total_calls"] += 1
    if report["decision"] == "BLOCK":
        session["block_count"] += 1
    elif report["decision"] == "QUARANTINE":
        session["rvs_quarantined"] += 1

    session["cddi_peak"] = max(session.get("cddi_peak", 0.0), report["cddi"])
    if report.get("rvs"):
        session["rvs_peak"] = max(session.get("rvs_peak", 0.0), report["rvs"]["rvs_score"])

    session["call_history"].append({
        "call_id": call["call_id"],
        "tool": call["tool"],
        "decision": report["decision"]
    })

    pr = report["perai"]
    if report["decision"] in ("ALLOW", "WARN", "QUARANTINE"):
        session["perai"]["budget_used"] += pr["c_hat"]
        if pr.get("estimation_error") is not None:
            session["perai"]["estimation_errors"].append(pr["estimation_error"])

    session["perai"]["call_costs"].append({
        "call_id": call["call_id"],
        "tool": call["tool"],
        "c_hat": pr["c_hat"],
        "decision": report["decision"]
    })

def run_episode(actions, session, identity):
    cpsi_scores = []
    for call in actions:
        report = evaluate(identity, call, session)
        update_session(session, report, call)
        cddi = report.get("cddi", 0.0)
        rvs = report.get("rvs", {}).get("rvs_score", 0.0) if report.get("rvs") else 0.0
        perai = min(report["perai"].get("c_hat", 0.0) / 500.0, 1.0)
        cpsi_scores.append(max(cddi, rvs, perai, 0.0))
    return cpsi_scores

def test_bleed():
    # Episode A: Heavy resource usage, multiple suspicious calls
    actions_a = [
        {"call_id": "a1", "tool": "list_pods", "requested_namespace": "ns", "required_privilege": "READ", "target_tenant": "t1", "parameters": {"size": 500}},
        {"call_id": "a2", "tool": "list_secrets", "requested_namespace": "ns", "required_privilege": "READ", "target_tenant": "t1", "parameters": {"size": 500}},
        {"call_id": "a3", "tool": "get_secret", "requested_namespace": "ns", "required_privilege": "READ", "target_tenant": "t1", "parameters": {"size": 500}}
    ]
    identity_a = {"agent_id": "a_a", "tenant_id": "t1", "authenticated_namespace": "ns", "granted_privilege": "READ"}

    # Episode B: Minimal benign request
    actions_b = [
        {"call_id": "b1", "tool": "ping", "requested_namespace": "ns", "required_privilege": "READ", "target_tenant": "t2", "parameters": {"size": 1}}
    ]
    identity_b = {"agent_id": "a_b", "tenant_id": "t2", "authenticated_namespace": "ns", "granted_privilege": "READ"}

    # Run 1: Episode A alone
    sess_a1 = create_fresh_session()
    scores_a_alone = run_episode(actions_a, sess_a1, identity_a)

    # Run 2: Episode B alone
    sess_b1 = create_fresh_session()
    scores_b_alone = run_episode(actions_b, sess_b1, identity_b)

    # Run 3: A -> reset -> B
    sess_a2 = create_fresh_session()
    scores_a_seq = run_episode(actions_a, sess_a2, identity_a)
    sess_b2 = create_fresh_session()
    scores_b_seq = run_episode(actions_b, sess_b2, identity_b)

    # Run 4: B -> reset -> A
    sess_b3 = create_fresh_session()
    scores_b_rev = run_episode(actions_b, sess_b3, identity_b)
    sess_a3 = create_fresh_session()
    scores_a_rev = run_episode(actions_a, sess_a3, identity_a)

    assert scores_a_alone == scores_a_seq == scores_a_rev, "State bleed detected in Episode A!"
    assert scores_b_alone == scores_b_seq == scores_b_rev, "State bleed detected in Episode B!"
    
    os.makedirs("external_validation/diagnostics/results", exist_ok=True)
    with open("external_validation/diagnostics/results/state_isolation_test.json", "w") as f:
        json.dump({
            "status": "PASS",
            "scores_a": scores_a_alone,
            "scores_b": scores_b_alone
        }, f)
        
    print("State Bleed Regression Test: PASS")

if __name__ == "__main__":
    test_bleed()
