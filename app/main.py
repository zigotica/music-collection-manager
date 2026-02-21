from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import db, create_tables, close_db
from app.routes import albums, browse, stats, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield
    close_db(None)

app = FastAPI(title="Music Library", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(albums.router)
app.include_router(browse.router)
app.include_router(stats.router)
app.include_router(admin.router)
