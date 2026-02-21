from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from peewee import fn
from app.models import Album

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/artist/{artist_name}", response_class=HTMLResponse)
async def browse_artist(request: Request, artist_name: str, sort: str = "year", order: str = "asc"):
    query = Album.select().where(Album.artist == artist_name)
    
    if sort == "title":
        query = query.order_by(Album.title.asc() if order == "asc" else Album.title.desc())
    else:
        query = query.order_by(Album.year.asc() if order == "asc" else Album.year.desc())
    
    albums = list(query)
    
    return templates.TemplateResponse("browse_artist.html", {
        "request": request,
        "albums": albums,
        "artist_name": artist_name,
        "sort": sort,
        "order": order
    })

@router.get("/year/{year}", response_class=HTMLResponse)
async def browse_year(request: Request, year: int, sort: str = "title", order: str = "asc"):
    query = Album.select().where(Album.year == year)
    
    if sort == "artist":
        query = query.order_by(Album.artist.asc() if order == "asc" else Album.artist.desc())
    else:
        query = query.order_by(Album.title.asc() if order == "asc" else Album.title.desc())
    
    albums = list(query)
    
    return templates.TemplateResponse("browse_year.html", {
        "request": request,
        "albums": albums,
        "year": year,
        "sort": sort,
        "order": order
    })

@router.get("/format/{format_name}", response_class=HTMLResponse)
async def browse_format(request: Request, format_name: str, sort: str = "artist", order: str = "asc"):
    query = Album.select().where(Album.physical_format == format_name)
    
    if sort == "title":
        query = query.order_by(Album.title.asc() if order == "asc" else Album.title.desc())
    elif sort == "year":
        query = query.order_by(Album.year.asc() if order == "asc" else Album.year.desc())
    else:
        query = query.order_by(Album.artist.asc() if order == "asc" else Album.artist.desc())
    
    albums = list(query)
    
    return templates.TemplateResponse("browse_format.html", {
        "request": request,
        "albums": albums,
        "format_name": format_name,
        "sort": sort,
        "order": order
    })

@router.get("/genre/{tag}", response_class=HTMLResponse)
async def browse_genre(request: Request, tag: str, sort: str = "artist", order: str = "asc"):
    albums = list(Album.select().where(Album.genres.contains(tag)))
    
    if sort == "title":
        albums.sort(key=lambda a: a.title, reverse=(order == "desc"))
    elif sort == "year":
        albums.sort(key=lambda a: a.year or 0, reverse=(order == "desc"))
    else:
        albums.sort(key=lambda a: a.artist, reverse=(order == "desc"))
    
    return templates.TemplateResponse("browse_genre.html", {
        "request": request,
        "albums": albums,
        "tag": tag,
        "sort": sort,
        "order": order
    })
