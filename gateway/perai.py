"""
perai.py -- Phase 2: Pre-Execution Resource Allocation Intelligence
Role: Standalone cost estimator and quota enforcement gate.

Exposes:
  estimate_cost(tool, parameters)           -> float  (C_hat)
  evaluate_perai(tool, parameters,
                 budget_used, c_actual)     -> dict   (PERAI report)

Cost model (Phase 2 baseline -- no ML, deterministic formula):
  C_hat = BASE_COST[tool] + max(numeric_param_values) * PER_UNIT_COST

Quota enforcement:
  BLOCK  -- C_hat > CALL_HARD_LIMIT  |OR|  budget_used + C_hat > SESSION_BUDGET
  WARN   -- C_hat > CALL_WARN_THRESHOLD  (allowed, but flagged)
  ALLOW  -- all thresholds satisfied

Estimation accuracy:
  When c_actual is supplied (from a post-execution measurement or
  simulation), the per-call estimation error is:
    epsilon = |C_hat - C_actual| / C_actual

  mean(epsilon) across a session is the PERAI calibration metric.
  Target for Phase 3 weight calibration: mean(epsilon) < 0.10 (10%).

No FastAPI, no Redis, no external dependencies. Stdlib only.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Cost model constants
# ---------------------------------------------------------------------------

# Base compute-unit cost per tool invocation
TOOL_BASE_COST: dict[str, float] = {
    "read_database":    10.0,
    "list_pods":         5.0,
    "list_secrets":      5.0,
    "get_secret":        3.0,
    "write_record":     20.0,
    "delete_secret":    30.0,
    "admin_reset":     500.0,
    "_default":         10.0,
}

PER_UNIT_COST: float = 0.01   # compute units per unit of largest numeric param

# ---------------------------------------------------------------------------
# Quota thresholds
# ---------------------------------------------------------------------------

CALL_WARN_THRESHOLD: float = 100.0   # C_hat above this triggers WARN
CALL_HARD_LIMIT:     float = 200.0   # C_hat above this triggers per-call BLOCK
SESSION_BUDGET:      float = 500.0   # total compute units per agent session

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def estimate_cost(tool: str, parameters: dict[str, Any]) -> float:
    """
    Compute C_hat for a single tool call.
    C_hat = base_cost(tool) + max(numeric_params) * PER_UNIT_COST
    """
    base = TOOL_BASE_COST.get(tool, TOOL_BASE_COST["_default"])
    numeric_vals: list[float] = [
        float(v) for v in parameters.values() if isinstance(v, (int, float))
    ]
    param_cost = max(numeric_vals) * PER_UNIT_COST if numeric_vals else 0.0
    return base + param_cost


def evaluate_perai(
    tool: str,
    parameters: dict[str, Any],
    budget_used: float,
    c_actual: float | None = None,
) -> dict[str, Any]:
    """
    Run the PERAI gate for one tool call.

    Args:
        tool         : tool name from the agent payload
        parameters   : tool parameter dict
        budget_used  : compute units already consumed in this session
        c_actual     : optional post-execution measurement for calibration

    Returns a dict with keys:
        c_hat             : float
        c_actual          : float | None
        estimation_error  : float | None  (|C_hat - C_actual| / C_actual)
        decision          : 'ALLOW' | 'WARN' | 'BLOCK'
        block_reason      : str | None
        warn_reason       : str | None
    """
    c_hat = estimate_cost(tool, parameters)

    # Estimation error (only meaningful for calls that actually execute)
    estimation_error: float | None = None
    if c_actual is not None and c_actual > 0:
        estimation_error = abs(c_hat - c_actual) / c_actual

    # Enforcement
    block_reason: str | None = None
    warn_reason:  str | None = None

    if c_hat > CALL_HARD_LIMIT:
        decision = "BLOCK"
        block_reason = (
            f"C_hat={c_hat:.2f} > call_limit={CALL_HARD_LIMIT:.0f} units"
        )
    elif budget_used + c_hat > SESSION_BUDGET:
        decision = "BLOCK"
        block_reason = (
            f"budget_used={budget_used:.2f} + C_hat={c_hat:.2f} "
            f"> session_budget={SESSION_BUDGET:.0f} units"
        )
    elif c_hat > CALL_WARN_THRESHOLD:
        decision = "WARN"
        warn_reason = (
            f"C_hat={c_hat:.2f} > warn_threshold={CALL_WARN_THRESHOLD:.0f} units"
        )
    else:
        decision = "ALLOW"

    return {
        "c_hat":            c_hat,
        "c_actual":         c_actual,
        "estimation_error": estimation_error,
        "decision":         decision,
        "block_reason":     block_reason,
        "warn_reason":      warn_reason,
        "budget_used":      budget_used,    # current session total BEFORE this call
    }
