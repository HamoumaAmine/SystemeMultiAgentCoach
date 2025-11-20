import uuid
import requests

def send_mcp(to_url: str, payload: dict, from_agent: str = "agent_interface"):
    """
    Envoi d’un message MCP standard à un autre agent.
    """
    message = {
        "message_id": str(uuid.uuid4()),
        "from": from_agent,
        "to": to_url,
        "type": "request",
        "payload": payload,
        "context": {}
    }

    resp = requests.post(f"{to_url}/mcp", json=message, timeout=10)
    resp.raise_for_status()
    return resp.json()
