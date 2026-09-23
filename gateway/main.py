from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, Dict
import sys
import os

# Import our existing gateway evaluation logic
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tool_gateway import evaluate, load_session, save_session

app = FastAPI(title="Semantic Gateway API")

class GatewayRequest(BaseModel):
    identity: Dict[str, Any]
    tool_call: Dict[str, Any]

@app.post("/evaluate")
def evaluate_call(req: GatewayRequest):
    session = load_session()
    
    try:
        report = evaluate(req.identity, req.tool_call, session)
        
        # Update session state based on the report
        session["total_calls"] += 1
        if report["decision"] == "BLOCK":
            session["block_count"] += 1
        elif report["decision"] == "QUARANTINE":
            session["rvs_quarantined"] += 1
            
        session["cddi_peak"] = max(session.get("cddi_peak", 0.0), report.get("cddi", 0.0))
        if report.get("rvs"):
            session["rvs_peak"] = max(session.get("rvs_peak", 0.0), report["rvs"].get("rvs_score", 0.0))
            
        session["call_history"].append({
            "call_id": req.tool_call.get("call_id", "unknown"),
            "tool": req.tool_call.get("tool", "unknown"),
            "decision": report["decision"]
        })
        
        # Budget consumed only when the call actually executes (ALLOW, WARN, QUARANTINE)
        pr = report["perai"]
        if report["decision"] in ("ALLOW", "WARN", "QUARANTINE"):
            session["perai"]["budget_used"] += pr["c_hat"]
            if pr.get("estimation_error") is not None:
                session["perai"]["estimation_errors"].append(pr["estimation_error"])

        session["perai"]["call_costs"].append({
            "call_id": req.tool_call.get("call_id", "unknown"),
            "tool": req.tool_call.get("tool", "unknown"),
            "c_hat": pr["c_hat"],
            "decision": report["decision"],
        })
        
        save_session(session)
        
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session")
def get_session():
    return load_session()

@app.delete("/session")
def reset_session():
    session_file = os.environ.get("GATEWAY_SESSION_FILE", "gateway/session_state.json")
    if os.path.exists(session_file):
        os.remove(session_file)
    return {"status": "reset"}
