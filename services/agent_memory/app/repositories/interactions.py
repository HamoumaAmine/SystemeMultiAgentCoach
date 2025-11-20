from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.models import Interaction


def create_interaction(
    db: Session,
    user_id: str,
    role: str,
    text: str,
    metadata: Dict[str, Any] | None = None,
) -> Interaction:
    """
    Crée une nouvelle interaction et la sauvegarde dans la base.
    """
    metadata = metadata or {}

    db_interaction = Interaction(
        user_id=user_id,
        role=role,
        text=text,
        metadata_json=metadata,  # ⚠️ on utilise metadata_json ici
    )
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction


def get_user_history(
    db: Session,
    user_id: str,
    limit: int = 10,
) -> List[Interaction]:
    """
    Retourne les dernières interactions pour un utilisateur,
    triées du plus récent au plus ancien.
    """
    q = (
        db.query(Interaction)
        .filter(Interaction.user_id == user_id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
    )
    return q.all()
