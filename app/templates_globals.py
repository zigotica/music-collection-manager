from fastapi.templating import Jinja2Templates
from app.config import COVERS_URL, ARTISTS_URL

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["COVERS_URL"] = COVERS_URL
templates.env.globals["ARTISTS_URL"] = ARTISTS_URL
