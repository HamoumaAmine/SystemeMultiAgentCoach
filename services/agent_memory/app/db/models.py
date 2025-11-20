from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)      # "user" ou "coach"
    text = Column(Text, nullable=False)

    # Attention : "metadata" est un nom réservé dans SQLAlchemy,
    # donc on appelle l'attribut Python "metadata_json".
    # On peut garder le nom de colonne SQL "metadata" si on veut.
    metadata_json = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
