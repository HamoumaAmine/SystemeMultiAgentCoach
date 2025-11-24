from fastapi import FastAPI
from routers import coach, auth, profile, dashboard, ui
from core.logging import setup_logging, log_requests_middleware
from fastapi.staticfiles import StaticFiles

setup_logging()

app = FastAPI(title="SMARTCOACH - Agent Interface")

app.mount("/static", StaticFiles(directory="static"), name="static")


# middleware logs
app.middleware("http")(log_requests_middleware)

@app.get("/")
def root():
    return {"message": "Agent Interface is running"}

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(dashboard.router)
app.include_router(coach.router)
app.include_router(ui.router)

@app.get("/health")
def health():
    return {"status": "ok"}
