from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class InteractionBase(BaseModel):
    """
    Champs de base d'une interaction stockée en base.
    """
    user_id: str
    role: str
    text: str
    metadata: Optional[Dict[str, Any]] = None


class InteractionCreate(InteractionBase):
    """
    Schéma pour créer une interaction (si API REST un jour).
    """
    pass


class InteractionRead(InteractionBase):
    """
    Schéma de lecture renvoyé par l'API quand on lit la base.
    """
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
