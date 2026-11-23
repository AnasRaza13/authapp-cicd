"""PRESENTATION LAYER - HTTP routes. Receives form data, calls the business layer,
and renders the Jinja2 template. No business rules and no database code here."""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.business.services import AuthError, AuthService
from app.data.database import get_db, ping
from app.version import APP_VERSION, BUILD_ID

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
# Available in every template: the footer shows "Version x.y.z - build runN-abc1234"
templates.env.globals.update(app_version=APP_VERSION, build_id=BUILD_ID)


def render(request: Request, mode: str = "login", status_code: int = 200, **context):
    return templates.TemplateResponse(
        request, "index.html", {"mode": mode, **context}, status_code=status_code
    )


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Used by the deployment and by the pipeline's final check to prove which build is live."""
    if not ping(db):
        return JSONResponse({"status": "error"}, status_code=503)
    return {"status": "ok", "version": APP_VERSION, "build": BUILD_ID}


@router.get("/", response_class=HTMLResponse)
def home(request: Request, mode: str = "login", db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    tenant_id = request.session.get("tenant_id")
    if user_id and tenant_id:
        service = AuthService(db)
        user = service.get_user(user_id, tenant_id)
        if user:
            return render(request, user=user, members=service.list_members(user))
        request.session.clear()  # stale or mismatched session (user deleted, wrong tenant...)
    return render(request, mode="register" if mode == "register" else "login")


@router.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    company: str = Form(""),
    username: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        AuthService(db).register(company, username, email, password, confirm_password)
    except AuthError as exc:
        return render(
            request, mode="register", status_code=400, error=str(exc),
            form={"company": company, "username": username, "email": email},
        )
    return render(
        request, mode="login", success="Account created! Please log in.",
        form={"company": " ".join(company.split()), "username": username.strip()},
    )


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    company: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = AuthService(db).authenticate(company, username, password)
    except AuthError as exc:
        return render(
            request, mode="login", status_code=401, error=str(exc),
            form={"company": company, "username": username},
        )
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["tenant_id"] = user.tenant_id
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
