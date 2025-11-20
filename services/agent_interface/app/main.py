from fastapi import FastAPI
from routers import coach

app = FastAPI(title="Agent Interface")

# ➕ AJOUTER ÇA
@app.get("/")
def root():
    return {"message": "Agent Interface is running"}

# Inclure les routes du coach
app.include_router(coach.router)

@app.get("/health")
def health():
    return {"status": "ok"}
