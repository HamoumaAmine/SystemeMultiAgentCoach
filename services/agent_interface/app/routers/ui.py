# services/agent_interface/app/routers/ui.py

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# IMPORTANT : chemin vers app/templates
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/login", response_class=HTMLResponse)
def ui_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse)
def ui_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get("/onboarding", response_class=HTMLResponse)
def ui_onboarding(request: Request):
    return templates.TemplateResponse("onboarding.html", {"request": request})


@router.get("/home", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/nutrition", response_class=HTMLResponse)
def ui_nutrition(request: Request):
    return templates.TemplateResponse("nutrition.html", {"request": request})


@router.get("/training", response_class=HTMLResponse)
def ui_training(request: Request):
    return templates.TemplateResponse("training.html", {"request": request})


@router.get("/image", response_class=HTMLResponse)
def ui_image(request: Request):
    return templates.TemplateResponse("image.html", {"request": request})


@router.get("/history", response_class=HTMLResponse)
def ui_history(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})
