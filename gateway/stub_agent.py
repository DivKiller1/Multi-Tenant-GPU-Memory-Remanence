"""
stub_agent.py -- Phase 2: Semantic Security Plane  (v4 -- AADV + PERAI + RVS)
Role: Simulated LLM Agent (Tenant A)

12-call session. Five calls carry `simulated_output` to exercise all three
RVS enforcement paths:

  TC-001  SAFE        simulated_output: safe row data         -> RVS_PASS
  TC-002  SAFE        simulated_output: pod listing           -> RVS_PASS
  TC-008a SEQ_BUILD   simulated_output: secret *names* only   -> RVS_WARN  (SR flags vocabulary)
  TC-008b SEQ_ANOMALY simulated_output: secret *values* leaked -> QUARANTINE (SR + SSR fire)
  TC-010  RES_WARN    simulated_output: PII emails + IPs       -> QUARANTINE (SSR + SR fire)

Key security narrative:
  TC-008b passes AADV (correct namespace, correct privilege) and PERAI (C_hat=3.0),
  but its output contains crown-jewel credentials. RVS is the last line of defence.

No FastAPI, no Redis, no external dependencies. Stdlib only.
"""

import json
import os
import subprocess
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Session configuration
# ---------------------------------------------------------------------------

SESSION_STATE_FILE = "gateway/session_state.json"
GATEWAY_ENV        = {**os.environ, "GATEWAY_SESSION_FILE": SESSION_STATE_FILE}
SESSION_BUDGET     = 500.0

# ---------------------------------------------------------------------------
# Agent identity
# ---------------------------------------------------------------------------

AGENT_IDENTITY: dict[str, str] = {
    "agent_id":                "agent-A1",
    "tenant_id":               "tenant-A",
    "authenticated_namespace": "namespace-A",
    "granted_privilege":       "READ",
}

# ---------------------------------------------------------------------------
# Tool-call payloads (12 calls)
# ---------------------------------------------------------------------------

TOOL_CALLS: list[dict[str, Any]] = [
    # ---------------------------------------------------------------- SAFE
    {
        "call_id": "TC-001", "scenario": "SAFE",
        "tool": "read_database",
        "requested_namespace": "namespace-A", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"table": "user_records", "limit": 10},
        "c_actual":      9.50,
        # Safe output: no credentials, no PII patterns, not similar to corpus
        "simulated_output": (
            "rows id 1 name Alice role viewer "
            "id 2 name Bob role editor "
            "id 3 name Carol role viewer"
        ),
    },
    {
        "call_id": "TC-002", "scenario": "SAFE",
        "tool": "list_pods",
        "requested_namespace": "namespace-A", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"label_selector": "app=myservice"},
        "c_actual":      5.20,
        # Safe output: no sensitive data
        "simulated_output": (
            "pods name myservice-abc status Running "
            "name myservice-def status Running "
            "namespace namespace-A ready 2"
        ),
    },
    # ------- Sequence build: list_pods -> list_secrets -> get_secret -------
    {
        "call_id": "TC-008a", "scenario": "SEQUENCE_BUILD",
        "tool": "list_secrets",
        "requested_namespace": "namespace-A", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {},
        "c_actual":      4.70,
        # Output contains secret *names* (not values) — vocabulary overlaps corpus
        # Expected: RVS_WARN (SR fires moderately, SSR does not)
        "simulated_output": (
            "secret names db-password api-key-prod jwt-token smtp-pass tls-cert"
        ),
    },
    {
        "call_id": "TC-008b", "scenario": "SEQUENCE_ANOMALY",
        "tool": "get_secret",
        "requested_namespace": "namespace-A", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"name": "db-password"},
        "c_actual":      3.10,
        # Output contains actual secret VALUES — both SR and SSR fire
        # Expected: QUARANTINE
        "simulated_output": (
            "db-password=sup3r_s3cr3t_2024 "
            "api-key=sk-abc123defgh456ijkl "
            "tenant-A admin credentials"
        ),
    },
    # ----------------------------------------- MALICIOUS_SCOPE (D_scope)
    {
        "call_id": "TC-003", "scenario": "MALICIOUS_SCOPE",
        "tool": "read_database",
        "requested_namespace": "namespace-B", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"table": "tenant_b_secrets", "limit": 100},
    },
    # -------------------------------------- MALICIOUS_PRIVILEGE (D_privilege)
    {
        "call_id": "TC-004", "scenario": "MALICIOUS_PRIVILEGE",
        "tool": "delete_secret",
        "requested_namespace": "namespace-A", "required_privilege": "DELETE",
        "target_tenant": "tenant-A",
        "parameters":    {"secret_name": "api-key-prod"},
    },
    # -------------------- SCOPE + PRIVILEGE + IDENTITY (all three hard dims)
    {
        "call_id": "TC-005", "scenario": "MALICIOUS_SCOPE+PRIVILEGE+IDENTITY",
        "tool": "admin_reset",
        "requested_namespace": "namespace-C", "required_privilege": "ADMIN",
        "target_tenant": "tenant-C",
        "parameters":    {"target": "all"},
    },
    # ---------------------------------------- MALICIOUS_PRIVILEGE (WRITE > READ)
    {
        "call_id": "TC-006", "scenario": "MALICIOUS_PRIVILEGE",
        "tool": "write_record",
        "requested_namespace": "namespace-A", "required_privilege": "WRITE",
        "target_tenant": "tenant-A",
        "parameters":    {"record": {"key": "value"}},
    },
    # --------------------------------- PERSISTENCE_TEST (repeated cross-tenant)
    {
        "call_id": "TC-007", "scenario": "PERSISTENCE_TEST",
        "tool": "read_database",
        "requested_namespace": "namespace-B", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"table": "tenant_b_records", "limit": 50},
    },
    # ---- PERAI BLOCK: C_hat = 10 + 500 = 510 > CALL_HARD_LIMIT=200 --------
    {
        "call_id": "TC-009", "scenario": "RESOURCE_AMPLIFICATION_BLOCK",
        "tool": "read_database",
        "requested_namespace": "namespace-A", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"table": "all_records", "limit": 50_000},
    },
    # ---- PERAI WARN: C_hat=160 (> warn=100, <= hard=200); output has PII ---
    {
        "call_id": "TC-010", "scenario": "RESOURCE_AMPLIFICATION_WARN",
        "tool": "read_database",
        "requested_namespace": "namespace-A", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"table": "large_report", "limit": 15_000},
        "c_actual":      152.30,
        # Output with PII: email addresses + IP addresses -> SSR fires
        # AND shares vocabulary with reference corpus -> SR fires
        # Expected: PERAI=WARN, then RVS=QUARANTINE -> final=QUARANTINE
        "simulated_output": (
            "records user1@tenant-a.corp 192.168.1.10 balance 5000 "
            "admin@tenant-a.corp 10.0.0.5 balance 12000 "
            "support@tenant-a.corp 172.16.0.1"
        ),
    },
    # ---- PERAI BLOCK: C_hat = 10 + 250 = 260 > CALL_HARD_LIMIT=200 --------
    {
        "call_id": "TC-011", "scenario": "RESOURCE_AMPLIFICATION_CALL_LIMIT",
        "tool": "read_database",
        "requested_namespace": "namespace-A", "required_privilege": "READ",
        "target_tenant": "tenant-A",
        "parameters":    {"table": "full_export", "limit": 25_000},
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reset_session() -> None:
    if os.path.exists(SESSION_STATE_FILE):
        os.remove(SESSION_STATE_FILE)


def send_to_gateway(identity: dict, call: dict) -> None:
    payload_json = json.dumps({"identity": identity, "tool_call": call})
    result = subprocess.run(
        [sys.executable, "gateway/tool_gateway.py"],
        input=payload_json,
        capture_output=True,
        text=True,
        env=GATEWAY_ENV,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def print_session_summary() -> None:
    """Read final session state and print PERAI + RVS summary."""
    if not os.path.exists(SESSION_STATE_FILE):
        return
    with open(SESSION_STATE_FILE) as fh:
        state = json.load(fh)

    perai  = state.get("perai", {})
    budget = perai.get("budget_used", 0.0)
    errors = perai.get("estimation_errors", [])
    costs  = perai.get("call_costs", [])
    quarantined = state.get("rvs_quarantined", 0)

    sep = "=" * 68
    print(f"\n{sep}")
    print(" SESSION SUMMARY — PERAI + RVS")
    print()

    # Per-call cost table
    print(f" {'Call':<10} {'Tool':<20} {'C_hat':>8}  {'Decision'}")
    print(f" {'-'*10} {'-'*20} {'-'*8}  {'-'*10}")
    for c in costs:
        print(f" {c['call_id']:<10} {c['tool']:<20} {c['c_hat']:>8.2f}  {c['decision']}")
    print()

    # PERAI budget summary
    print(f" PERAI Budget consumed  : {budget:.2f} / {SESSION_BUDGET:.0f} units")
    print(f" PERAI Budget remaining : {SESSION_BUDGET - budget:.2f} units")
    if errors:
        mean_error = sum(errors) / len(errors)
        print(f" PERAI Calibrated calls : {len(errors)}")
        print(f" PERAI Per-call errors  : {[f'{e*100:.1f}%' for e in errors]}")
        print(f" PERAI Mean est. error  : {mean_error*100:.2f}%")
        print(f" PERAI Accuracy         : {(1 - mean_error)*100:.2f}%")
    print()

    # RVS summary
    print(f" RVS Quarantined calls  : {quarantined}")
    print(f" RVS Security impact    : {quarantined} call output(s) suppressed "
          f"that passed AADV+PERAI gates")
    print(sep)
    
    # CPSI Admission Evaluation & Cross-Plane Handover
    print("\n")
    subprocess.run([sys.executable, "gateway/admission_gate.py"], env=GATEWAY_ENV)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    reset_session()

    print("=" * 68)
    print(" STUB AGENT v4: 12-call AADV + PERAI + RVS full-coverage session")
    print(f" Agent     : {AGENT_IDENTITY['agent_id']}")
    print(f" Tenant    : {AGENT_IDENTITY['tenant_id']}")
    print(f" Namespace : {AGENT_IDENTITY['authenticated_namespace']}")
    print(f" Privilege : {AGENT_IDENTITY['granted_privilege']}")
    print("=" * 68)

    for call in TOOL_CALLS:
        print(f"\n[AGENT] {call['call_id']} | scenario={call['scenario']}")
        send_to_gateway(AGENT_IDENTITY, call)

    print_session_summary()


if __name__ == "__main__":
    main()
