import os
import requests
import time
import sys

from gateway.stub_agent import TOOL_CALLS, AGENT_IDENTITY

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")

def send_to_gateway(identity, call):
    payload = {
        "identity": identity,
        "tool_call": call
    }
    try:
        resp = requests.post(f"{GATEWAY_URL}/evaluate", json=payload)
        resp.raise_for_status()
        report = resp.json()
        print(f"[AGENT] {call['call_id']} | decision: {report['decision']}")
    except Exception as e:
        print(f"[AGENT ERROR] {call['call_id']}: {e}", file=sys.stderr)

def main():
    print(f"Waiting for Gateway at {GATEWAY_URL}...")
    for _ in range(10):
        try:
            requests.delete(f"{GATEWAY_URL}/session")
            print("Connected to Gateway. Session reset.")
            break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        print("Could not connect to Gateway.", file=sys.stderr)
        sys.exit(1)

    print("=" * 68)
    print(" STUB AGENT (DOCKER) v5")
    print("=" * 68)

    for call in TOOL_CALLS:
        send_to_gateway(AGENT_IDENTITY, call)
        time.sleep(0.1)

    print("Session complete.")

if __name__ == "__main__":
    main()
