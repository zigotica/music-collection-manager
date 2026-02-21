import os
import json
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from peewee import fn
from app.models import Album, db
from app.config import UPLOAD_DIR
from app.services.lastfm import scrape_album
from app.services.image_utils import resize_image

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, search: str = "", sort: str = "title", order: str = "asc"):
    query = Album.select().where(Album.is_wanted == False)
    
    if search:
        query = query.where(
            (Album.title.contains(search)) | 
            (Album.artist.contains(search))
        )
    
    if sort == "artist":
        query = query.order_by(Album.artist.asc() if order == "asc" else Album.artist.desc())
    elif sort == "year":
        query = query.order_by(Album.year.asc() if order == "asc" else Album.year.desc())
    else:
        query = query.order_by(Album.title.asc() if order == "asc" else Album.title.desc())
    
    albums = list(query)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "albums": albums,
        "search": search,
        "sort": sort,
        "order": order
    })

@router.get("/wanted", response_class=HTMLResponse)
async def wanted(request: Request, search: str = "", sort: str = "title", order: str = "asc"):
    query = Album.select().where(Album.is_wanted == True)
    
    if search:
        query = query.where(
            (Album.title.contains(search)) | 
            (Album.artist.contains(search))
        )
    
    if sort == "artist":
        query = query.order_by(Album.artist.asc() if order == "asc" else Album.artist.desc())
    elif sort == "year":
        query = query.order_by(Album.year.asc() if order == "asc" else Album.year.desc())
    else:
        query = query.order_by(Album.title.asc() if order == "asc" else Album.title.desc())
    
    albums = list(query)
    
    return templates.TemplateResponse("wanted.html", {
        "request": request,
        "albums": albums,
        "search": search,
        "sort": sort,
        "order": order
    })

@router.get("/albums/new", response_class=HTMLResponse)
async def new_album_form(request: Request):
    return templates.TemplateResponse("album_form.html", {
        "request": request,
        "album": None,
        "is_edit": False
    })

@router.post("/albums")
async def create_album(
    title: str = Form(...),
    artist: str = Form(...),
    year: int = Form(None),
    physical_format: str = Form(None),
    genres: str = Form(""),
    notes: str = Form(None),
    is_wanted: bool = Form(False),
    cover: UploadFile = File(None)
):
    cover_path = None
    if cover and cover.filename:
        if allowed_file(cover.filename):
            content = await cover.read()
            resized_content, ext = resize_image(content)
            filename = f"{artist}_{title}.{ext}".replace(" ", "_").replace("/", "_")
            filepath = os.path.join(UPLOAD_DIR, filename)
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(resized_content)
            cover_path = f"/static/uploads/{filename}"
    
    genre_list = [g.strip() for g in genres.split(",") if g.strip()] if genres else []
    
    album = Album.create(
        title=title,
        artist=artist,
        year=year,
        physical_format=physical_format,
        genres=genre_list,
        cover_image_path=cover_path,
        is_wanted=is_wanted,
        notes=notes
    )
    
    return RedirectResponse(url=f"/albums/{album.id}", status_code=303)

@router.get("/albums/{album_id}", response_class=HTMLResponse)
async def get_album(request: Request, album_id: int, message: str = None):
    try:
        album = Album.get_by_id(album_id)
    except Album.DoesNotExist:
        raise HTTPException(status_code=404, detail="Album not found")
    
    return templates.TemplateResponse("album_detail.html", {
        "request": request,
        "album": album,
        "message": message
    })

@router.get("/albums/{album_id}/edit", response_class=HTMLResponse)
async def edit_album_form(request: Request, album_id: int):
    try:
        album = Album.get_by_id(album_id)
    except Album.DoesNotExist:
        raise HTTPException(status_code=404, detail="Album not found")
    
    return templates.TemplateResponse("album_form.html", {
        "request": request,
        "album": album,
        "is_edit": True
    })

@router.post("/albums/{album_id}")
async def update_album(
    album_id: int,
    title: str = Form(...),
    artist: str = Form(...),
    year: int = Form(None),
    physical_format: str = Form(None),
    genres: str = Form(""),
    notes: str = Form(None),
    is_wanted: bool = Form(False),
    cover: UploadFile = File(None)
):
    try:
        album = Album.get_by_id(album_id)
    except Album.DoesNotExist:
        raise HTTPException(status_code=404, detail="Album not found")
    
    if cover and cover.filename:
        if allowed_file(cover.filename):
            content = await cover.read()
            resized_content, ext = resize_image(content)
            filename = f"{artist}_{title}_{album_id}.{ext}".replace(" ", "_").replace("/", "_")
            filepath = os.path.join(UPLOAD_DIR, filename)
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(resized_content)
            album.cover_image_path = f"/static/uploads/{filename}"
    
    genre_list = [g.strip() for g in genres.split(",") if g.strip()] if genres else []
    
    album.title = title
    album.artist = artist
    album.year = year
    album.physical_format = physical_format
    album.genres = genre_list
    album.is_wanted = is_wanted
    album.notes = notes
    album.save()
    
    return RedirectResponse(url=f"/albums/{album.id}", status_code=303)

@router.post("/albums/{album_id}/delete")
async def delete_album(album_id: int):
    try:
        album = Album.get_by_id(album_id)
        if album.cover_image_path:
            filepath = os.path.join("app", album.cover_image_path.lstrip("/"))
            if os.path.exists(filepath):
                os.remove(filepath)
        album.delete_instance()
    except Album.DoesNotExist:
        raise HTTPException(status_code=404, detail="Album not found")
    
    return RedirectResponse(url="/", status_code=303)

@router.post("/albums/{album_id}/scrape")
async def scrape_single_album(album_id: int):
    try:
        album = Album.get_by_id(album_id)
    except Album.DoesNotExist:
        raise HTTPException(status_code=404, detail="Album not found")
    
    result = await scrape_album(album)
    
    if result["updated"]:
        message = "Album updated"
    else:
        message = "No updates needed"
    
    return RedirectResponse(
        url=f"/albums/{album_id}?message={message}", 
        status_code=303
    )
