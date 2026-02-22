from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.models import db, create_tables, close_db
from app.routes import albums, browse, stats, admin
from app.auth import login, logout, is_authenticated
from app.config import SECRET_KEY

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield
    close_db(None)

app = FastAPI(title="Music Library", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })

@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if login(request, password):
        return RedirectResponse(url="/admin", status_code=303)
    return RedirectResponse(url="/login?error=Invalid+password", status_code=303)

@app.get("/logout")
async def logout_route(request: Request):
    logout(request)
    return RedirectResponse(url="/", status_code=303)

app.include_router(albums.router)
app.include_router(browse.router)
app.include_router(stats.router)
app.include_router(admin.router)
