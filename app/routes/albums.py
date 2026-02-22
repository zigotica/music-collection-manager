import os
import json
import re
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from peewee import fn
from app.models import Album, db
from app.config import COVERS_DIR
from app.services.lastfm import scrape_album
from app.services.image_utils import resize_image
from app.auth import require_admin
from app.templates_globals import templates

router = APIRouter()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def album_url(album):
    slug = re.sub(r'[^\w\-]', '', album.title.replace(' ', '-')).lower()
    return f"/albums/{album.id}-{slug}"

templates.env.globals["album_url"] = album_url

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
async def new_album_form(request: Request, _: bool = Depends(require_admin)):
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
    cover: UploadFile = File(None),
    _: bool = Depends(require_admin)
):
    cover_path = None
    if cover and cover.filename:
        if allowed_file(cover.filename):
            content = await cover.read()
            resized_content, ext = resize_image(content)
            filename = f"{artist}_{title}.{ext}".replace(" ", "_").replace("/", "_")
            os.makedirs(COVERS_DIR, exist_ok=True)
            filepath = os.path.join(COVERS_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resized_content)
            cover_path = filename
    
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

@router.get("/albums/{album_slug:path}", response_class=HTMLResponse)
async def get_album(request: Request, album_slug: str, message: str = None):
    try:
        album_id = int(album_slug.split('-')[0])
        album = Album.get_by_id(album_id)
    except (ValueError, Album.DoesNotExist):
        raise HTTPException(status_code=404, detail="Album not found")
    
    return templates.TemplateResponse("album_detail.html", {
        "request": request,
        "album": album,
        "message": message
    })

@router.get("/albums/{album_slug:path}/edit", response_class=HTMLResponse)
async def edit_album_form(request: Request, album_slug: str, _: bool = Depends(require_admin)):
    try:
        album_id = int(album_slug.split('-')[0])
        album = Album.get_by_id(album_id)
    except (ValueError, Album.DoesNotExist):
        raise HTTPException(status_code=404, detail="Album not found")
    
    return templates.TemplateResponse("album_form.html", {
        "request": request,
        "album": album,
        "is_edit": True
    })

@router.post("/albums/{album_slug:path}")
async def update_album(
    album_slug: str,
    title: str = Form(...),
    artist: str = Form(...),
    year: int = Form(None),
    physical_format: str = Form(None),
    genres: str = Form(""),
    notes: str = Form(None),
    is_wanted: bool = Form(False),
    cover: UploadFile = File(None),
    _: bool = Depends(require_admin)
):
    try:
        album_id = int(album_slug.split('-')[0])
        album = Album.get_by_id(album_id)
    except (ValueError, Album.DoesNotExist):
        raise HTTPException(status_code=404, detail="Album not found")
    
    if cover and cover.filename:
        if allowed_file(cover.filename):
            content = await cover.read()
            resized_content, ext = resize_image(content)
            filename = f"{artist}_{title}_{album_id}.{ext}".replace(" ", "_").replace("/", "_")
            os.makedirs(COVERS_DIR, exist_ok=True)
            filepath = os.path.join(COVERS_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resized_content)
            album.cover_image_path = filename
    
    genre_list = [g.strip() for g in genres.split(",") if g.strip()] if genres else []
    
    album.title = title
    album.artist = artist
    album.year = year
    album.physical_format = physical_format
    album.genres = genre_list
    album.is_wanted = is_wanted
    album.notes = notes
    album.save()
    
    return RedirectResponse(url=album_url(album), status_code=303)

@router.post("/albums/{album_slug:path}/delete")
async def delete_album(album_slug: str, _: bool = Depends(require_admin)):
    try:
        album_id = int(album_slug.split('-')[0])
        album = Album.get_by_id(album_id)
        if album.cover_image_path:
            filepath = os.path.join(COVERS_DIR, album.cover_image_path)
            if os.path.exists(filepath):
                os.remove(filepath)
        album.delete_instance()
    except (ValueError, Album.DoesNotExist):
        raise HTTPException(status_code=404, detail="Album not found")
    
    return RedirectResponse(url="/", status_code=303)

@router.post("/albums/{album_slug:path}/scrape")
async def scrape_single_album(album_slug: str, _: bool = Depends(require_admin)):
    try:
        album_id = int(album_slug.split('-')[0])
        album = Album.get_by_id(album_id)
    except (ValueError, Album.DoesNotExist):
        raise HTTPException(status_code=404, detail="Album not found")
    
    result = await scrape_album(album)
    
    if result["updated"]:
        message = "Album updated"
    else:
        message = "No updates needed"
    
    return RedirectResponse(
        url=f"{album_url(album)}?message={message}", 
        status_code=303
    )

@router.post("/albums/{album_slug:path}/accept-discogs-year")
async def accept_discogs_year(album_slug: str, _: bool = Depends(require_admin)):
    try:
        album_id = int(album_slug.split('-')[0])
        album = Album.get_by_id(album_id)
    except (ValueError, Album.DoesNotExist):
        raise HTTPException(status_code=404, detail="Album not found")
    
    if album.year_discogs_release:
        album.year = album.year_discogs_release
        album.save()
        message = "Year updated from Discogs"
    else:
        message = "No Discogs year available"
    
    return RedirectResponse(
        url=f"{album_url(album)}?message={message}", 
        status_code=303
    )
