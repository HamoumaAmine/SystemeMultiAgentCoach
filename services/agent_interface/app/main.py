from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import coach, auth, profile, dashboard, ui
from app.core.logging import setup_logging, log_requests_middleware

setup_logging()

app = FastAPI(title="SMARTCOACH - Agent Interface")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
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
