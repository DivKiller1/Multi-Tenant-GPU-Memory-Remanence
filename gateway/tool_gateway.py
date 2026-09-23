"""
tool_gateway.py -- Phase 2: Semantic Security Plane  (v4 -- AADV + PERAI + RVS + CDDI)
Role: Agent Tool Gateway

Three parallel enforcement planes per tool call:

  AADV plane  (semantic / identity -- pre-execution):
    D_scope, D_privilege, D_identity  -- hard block (any > 0)
    D_sequence, D_persistence         -- behavioural context
    D_resource                        -- resource signal (feeds CDDI)
    CDDI = weighted_sum(AADV)         -- soft block if >= 0.40

  PERAI plane  (resource / cost -- pre-execution):
    C_hat vs CALL_HARD_LIMIT          -- per-call hard block
    budget_used + C_hat vs SESSION_BUDGET -- session budget block
    C_hat vs CALL_WARN_THRESHOLD      -- warn

  RVS plane  (output data -- post-execution):
    SR  (Semantic Recovery)  -- cosine similarity vs. crown-jewel corpus
    SSR (Sensitive-String)   -- regex scan for 9 sensitive-data patterns
    RVS = 0.6*SR + 0.4*SSR  -- quarantine if >= 0.30, warn if >= 0.15

Decision merging:
  Phase 1 (pre-execution):
    intermediate = BLOCK  if AADV-BLOCK OR PERAI-BLOCK
    intermediate = WARN   if AADV-ALLOW AND PERAI-WARN
    intermediate = ALLOW  otherwise

  Phase 2 (post-execution, only if intermediate != BLOCK):
    Apply RVS to simulated_output if present in payload:
    final = QUARANTINE  if RVS >= 0.30
    final = WARN        if RVS >= 0.15 (or PERAI-WARN already)
    final = ALLOW       otherwise

Budget accounting: budget updated only for ALLOW or WARN
(calls that would actually execute).

Session state: JSON file at SESSION_STATE_FILE.

No FastAPI, no Redis, no external dependencies. Stdlib only.
"""

import json
import os
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Import sibling modules
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from perai import evaluate_perai, CALL_HARD_LIMIT, CALL_WARN_THRESHOLD, SESSION_BUDGET  # noqa
from rvs import evaluate_rvs, RVS_QUARANTINE_THRESHOLD, RVS_WARN_THRESHOLD              # noqa

# ---------------------------------------------------------------------------
# AADV configuration
# ---------------------------------------------------------------------------

PRIVILEGE_LEVELS: dict[str, int] = {
    "READ": 0, "WRITE": 1, "DELETE": 2, "ADMIN": 3,
}
MAX_PRIVILEGE = max(PRIVILEGE_LEVELS.values())   # 3

RESOURCE_QUOTA      = 1_000
CDDI_SOFT_THRESHOLD = 0.40

SUSPICIOUS_SEQUENCES: list[tuple[str, ...]] = [
    ("list_pods", "list_secrets", "get_secret"),
    ("list_pods", "describe_service_account", "list_secrets"),
    ("read_database", "read_database", "read_database"),
]

SESSION_STATE_FILE: str = os.environ.get(
    "GATEWAY_SESSION_FILE", "gateway/session_state.json"
)

AADV_WEIGHTS: dict[str, float] = {
    "D_scope":       1 / 6,
    "D_privilege":   1 / 6,
    "D_identity":    1 / 6,
    "D_sequence":    1 / 6,
    "D_persistence": 1 / 6,
    "D_resource":    1 / 6,
}

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def load_session() -> dict[str, Any]:
    if os.path.exists(SESSION_STATE_FILE):
        with open(SESSION_STATE_FILE) as fh:
            state = json.load(fh)
        if "perai" not in state:
            state["perai"] = {"budget_used": 0.0, "estimation_errors": [], "call_costs": []}
        if "rvs_quarantined" not in state:
            state["rvs_quarantined"] = 0
        if "cddi_peak" not in state:
            state["cddi_peak"] = 0.0
        if "rvs_peak" not in state:
            state["rvs_peak"] = 0.0
        return state
    return {
        "call_history":    [],
        "block_count":     0,
        "total_calls":     0,
        "rvs_quarantined": 0,
        "cddi_peak":       0.0,
        "rvs_peak":        0.0,
        "perai": {
            "budget_used":       0.0,
            "estimation_errors": [],
            "call_costs":        [],
        },
    }


def save_session(state: dict[str, Any]) -> None:
    with open(SESSION_STATE_FILE, "w") as fh:
        json.dump(state, fh, indent=2)


# ---------------------------------------------------------------------------
# AADV dimensions
# ---------------------------------------------------------------------------

def _scope(req_ns: str, auth_ns: str) -> float:
    return 0.0 if req_ns == auth_ns else 1.0


def _privilege(required: str, granted: str) -> float:
    gap = max(0, PRIVILEGE_LEVELS.get(required, 0) - PRIVILEGE_LEVELS.get(granted, 0))
    return gap / MAX_PRIVILEGE


def _identity(target_tenant: str | None, auth_tenant: str) -> float:
    if target_tenant is None:
        return 0.0
    return 0.0 if target_tenant == auth_tenant else 1.0


def _sequence(history: list[dict]) -> float:
    recent = tuple(e["tool"] for e in history[-3:])
    return 1.0 if (len(recent) == 3 and recent in SUSPICIOUS_SEQUENCES) else 0.0


def _persistence(block_count: int, total_calls: int) -> float:
    return min(block_count / total_calls, 1.0) if total_calls > 0 else 0.0


def _resource(parameters: dict[str, Any]) -> float:
    vals = [float(v) for v in parameters.values() if isinstance(v, (int, float))]
    return min(max(vals) / RESOURCE_QUOTA, 1.0) if vals else 0.0


def _cddi(aadv: dict[str, float]) -> float:
    # Calibration: A hard boundary breach indicates malicious intent. 
    # Weights should not dilute this signal. Spike CDDI to 1.0 immediately.
    if aadv["D_scope"] > 0.0 or aadv["D_privilege"] > 0.0 or aadv["D_identity"] > 0.0:
        return 1.0
    return sum(AADV_WEIGHTS[k] * aadv[k] for k in AADV_WEIGHTS)


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def evaluate(identity: dict, call: dict, session: dict) -> dict[str, Any]:

    # ---- AADV ----
    aadv = {
        "D_scope":       _scope(call["requested_namespace"], identity["authenticated_namespace"]),
        "D_privilege":   _privilege(call["required_privilege"], identity["granted_privilege"]),
        "D_identity":    _identity(call.get("target_tenant"), identity["tenant_id"]),
        "D_sequence":    _sequence(session["call_history"]),
        "D_persistence": _persistence(session["block_count"], session["total_calls"]),
        "D_resource":    _resource(call.get("parameters", {})),
    }
    cddi = _cddi(aadv)

    aadv_hard = aadv["D_scope"] > 0.0 or aadv["D_privilege"] > 0.0 or aadv["D_identity"] > 0.0
    aadv_soft = cddi >= CDDI_SOFT_THRESHOLD
    aadv_decision = "BLOCK" if (aadv_hard or aadv_soft) else "ALLOW"

    aadv_reasons: list[str] = []
    if aadv["D_scope"] > 0.0:
        aadv_reasons.append(f"D_scope={aadv['D_scope']:.4f}  — cross-tenant namespace")
    if aadv["D_privilege"] > 0.0:
        aadv_reasons.append(f"D_privilege={aadv['D_privilege']:.4f}  — privilege escalation")
    if aadv["D_identity"] > 0.0:
        aadv_reasons.append(f"D_identity={aadv['D_identity']:.4f}  — cross-tenant identity")
    if not aadv_hard and aadv_soft:
        aadv_reasons.append(f"CDDI={cddi:.4f} >= {CDDI_SOFT_THRESHOLD} — compound divergence")

    # ---- PERAI ----
    perai_result = evaluate_perai(
        tool=call["tool"],
        parameters=call.get("parameters", {}),
        budget_used=session["perai"]["budget_used"],
        c_actual=call.get("c_actual"),
    )

    # ---- Intermediate decision (pre-execution) ----
    if aadv_decision == "BLOCK" or perai_result["decision"] == "BLOCK":
        intermediate = "BLOCK"
    elif perai_result["decision"] == "WARN":
        intermediate = "WARN"
    else:
        intermediate = "ALLOW"

    # ---- RVS (post-execution gate, only for non-blocked calls) ----
    rvs_result: dict[str, Any] | None = None
    simulated_output: str | None = call.get("simulated_output")

    if intermediate != "BLOCK" and simulated_output is not None:
        rvs_result = evaluate_rvs(simulated_output)
        if rvs_result["decision"] == "QUARANTINE":
            final_decision = "QUARANTINE"
        elif rvs_result["decision"] == "RVS_WARN":
            final_decision = "WARN"
        else:
            final_decision = intermediate
    else:
        final_decision = intermediate

    return {
        "call_id":       call["call_id"],
        "tool":          call["tool"],
        "agent_id":      identity["agent_id"],
        "tenant_id":     identity["tenant_id"],
        "aadv":          aadv,
        "cddi":          cddi,
        "aadv_decision": aadv_decision,
        "aadv_reasons":  aadv_reasons,
        "perai":         perai_result,
        "rvs":           rvs_result,
        "decision":      final_decision,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_report(report: dict[str, Any]) -> None:
    sep = "=" * 68
    decision = report["decision"]
    print(sep)
    print(f"[GATEWAY] Call     : {report['call_id']} | {report['tool']}")
    print(f"[GATEWAY] Agent    : {report['agent_id']}  Tenant: {report['tenant_id']}")

    print(f"[GATEWAY] --- AADV ({report['aadv_decision']}) ---")
    for dim, val in report["aadv"].items():
        print(f"[GATEWAY]   {dim:<18} : {val:.4f}")
    print(f"[GATEWAY]   {'CDDI':<18} : {report['cddi']:.4f}  (thr={CDDI_SOFT_THRESHOLD})")
    for reason in report["aadv_reasons"]:
        print(f"[GATEWAY]   >> {reason}")

    pr = report["perai"]
    print(f"[GATEWAY] --- PERAI ({pr['decision']}) ---")
    print(f"[GATEWAY]   C_hat            : {pr['c_hat']:.2f} units")
    if pr.get("c_actual") is not None:
        print(f"[GATEWAY]   C_actual         : {pr['c_actual']:.2f} units")
        print(f"[GATEWAY]   Est. error       : {pr['estimation_error']:.3f} ({pr['estimation_error']*100:.1f}%)")
    print(f"[GATEWAY]   Budget used      : {pr['budget_used']:.2f} / {SESSION_BUDGET:.0f} units")
    if pr.get("block_reason"):
        print(f"[GATEWAY]   >> BLOCK: {pr['block_reason']}")
    if pr.get("warn_reason"):
        print(f"[GATEWAY]   >> WARN:  {pr['warn_reason']}")

    rvs = report.get("rvs")
    if rvs is not None:
        print(f"[GATEWAY] --- RVS ({rvs['decision']}) ---")
        print(f"[GATEWAY]   SR_score         : {rvs['sr_score']:.4f}  (semantic similarity to crown jewels)")
        print(f"[GATEWAY]   SSR_score        : {rvs['ssr_score']:.4f}  ({len(rvs['ssr_matches'])} of {9} patterns matched)")
        if rvs["ssr_matches"]:
            pattern_names = ", ".join(rvs["ssr_matches"].keys())
            print(f"[GATEWAY]   SSR matches      : {pattern_names}")
        print(f"[GATEWAY]   RVS              : {rvs['rvs_score']:.4f}  (Q-thr={RVS_QUARANTINE_THRESHOLD}, W-thr={RVS_WARN_THRESHOLD})")
        if rvs.get("reason"):
            print(f"[GATEWAY]   >> {rvs['decision']}: {rvs['reason']}")
    else:
        print(f"[GATEWAY] --- RVS (N/A) ---")
        if report["decision"] == "BLOCK":
            print(f"[GATEWAY]   Skipped — call blocked before execution")
        else:
            print(f"[GATEWAY]   Skipped — no simulated_output in payload")

    print(f"[GATEWAY] DECISION : {decision}")
    print(sep)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print("[GATEWAY] ERROR: no payload on stdin.", file=sys.stderr)
        return 2

    payload  = json.loads(raw)
    identity = payload["identity"]
    call     = payload["tool_call"]

    session = load_session()
    report  = evaluate(identity, call, session)
    print_report(report)

    # --- Update session state ---
    session["total_calls"] += 1
    if report["decision"] == "BLOCK":
        session["block_count"] += 1
    elif report["decision"] == "QUARANTINE":
        session["rvs_quarantined"] += 1

    session["cddi_peak"] = max(session.get("cddi_peak", 0.0), report["cddi"])
    if report.get("rvs"):
        session["rvs_peak"] = max(session.get("rvs_peak", 0.0), report["rvs"]["rvs_score"])

    session["call_history"].append({
        "call_id":  call["call_id"],
        "tool":     call["tool"],
        "decision": report["decision"],
    })

    # Budget consumed only when the call actually executes (ALLOW, WARN, QUARANTINE)
    # QUARANTINE: the call executed but the output was suppressed — cost was incurred
    pr = report["perai"]
    if report["decision"] in ("ALLOW", "WARN", "QUARANTINE"):
        session["perai"]["budget_used"] += pr["c_hat"]
        if pr.get("estimation_error") is not None:
            session["perai"]["estimation_errors"].append(pr["estimation_error"])

    session["perai"]["call_costs"].append({
        "call_id":  call["call_id"],
        "tool":     call["tool"],
        "c_hat":    pr["c_hat"],
        "decision": report["decision"],
    })

    save_session(session)
    return 1 if report["decision"] in ("BLOCK", "QUARANTINE") else 0


if __name__ == "__main__":
    sys.exit(main())
