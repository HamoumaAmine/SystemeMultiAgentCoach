from typing import Any, Dict, Optional
from pydantic import BaseModel


class MCPMessage(BaseModel):
    message_id: str
    type: str = "request"
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    message_id: str
    type: str = "response"
    from_agent: str
    to_agent: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
