from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from app.config import ADMIN_PASSWORD

SESSION_KEY = "is_admin"

def is_authenticated(request: Request) -> bool:
    return request.session.get(SESSION_KEY, False)

def require_admin(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return True

def login(request: Request, password: str) -> bool:
    if password == ADMIN_PASSWORD:
        request.session[SESSION_KEY] = True
        return True
    return False

def logout(request: Request):
    request.session.pop(SESSION_KEY, None)
