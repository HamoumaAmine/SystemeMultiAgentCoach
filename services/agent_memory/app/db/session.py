from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Pour la V1, on utilise une base SQLite locale.
# Le fichier sera créé dans le dossier de l'agent_memory.
DATABASE_URL = "sqlite:///./agent_memory.db"

# check_same_thread=False est nécessaire pour SQLite avec FastAPI / Uvicorn
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

