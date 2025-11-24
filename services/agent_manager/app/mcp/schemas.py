from typing import Any, Dict
from pydantic import BaseModel


class MCPMessage(BaseModel):
    message_id: str
    from_agent: str
    to_agent: str
    type: str
    payload: Dict[str, Any]
    context: Dict[str, Any] = {}


class MCPResponse(BaseModel):
    message_id: str
    to_agent: str
    payload: Dict[str, Any]
    context: Dict[str, Any] = {}
