from fastapi import FastAPI
from routers import coach

app = FastAPI(title="Agent Interface")

# Inclure le router
app.include_router(coach.router)

@app.get("/health")
def health():
    return {"status": "ok"}
