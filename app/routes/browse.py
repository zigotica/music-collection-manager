from fastapi import APIRouter, Request, Form, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from peewee import fn
from urllib.parse import quote
import os
from app.models import Album, Artist
from app.services.lastfm import scrape_artist, get_or_create_artist
from app.services.image_utils import resize_image
from app.config import ARTISTS_DIR
from app.auth import require_admin
from app.templates_globals import templates

router = APIRouter()

@router.get("/artists", response_class=HTMLResponse)
async def browse_artists(request: Request, sort: str = "name", order: str = "asc"):
    artists_data = Album.select(
        Album.artist,
        fn.COUNT(Album.id).alias('album_count')
    ).where(
        Album.is_wanted == False
    ).group_by(
        Album.artist
    ).dicts()
    
    artists_list = []
    for a in artists_data:
        artist_name = a['artist']
        album_count = a['album_count']
        
        artist = Artist.select().where(Artist.name == artist_name).first()
        
        artists_list.append({
            'name': artist_name,
            'album_count': album_count,
            'image_url': artist.image_url if artist else None,
            'genres': artist.genres if artist else []
        })
    
    if sort == "albums":
        artists_list.sort(key=lambda x: x['album_count'], reverse=(order == "desc"))
    else:
        artists_list.sort(key=lambda x: x['name'].lower(), reverse=(order == "desc"))
    
    return templates.TemplateResponse("artists.html", {
        "request": request,
        "artists": artists_list,
        "sort": sort,
        "order": order
    })

@router.get("/artist/{artist_name:path}/edit", response_class=HTMLResponse)
async def edit_artist_form(request: Request, artist_name: str, _: bool = Depends(require_admin)):
    count = Album.select().where(Album.artist == artist_name).count()
    artist = Artist.select().where(Artist.name == artist_name).first()
    
    return templates.TemplateResponse("edit_artist.html", {
        "request": request,
        "artist_name": artist_name,
        "album_count": count,
        "artist": artist
    })

@router.post("/artist/{artist_name:path}/edit")
async def update_artist_name(
    artist_name: str,
    new_name: str = Form(...),
    bio: str = Form(None),
    genres: str = Form(None),
    image: UploadFile = File(None),
    _: bool = Depends(require_admin)
):
    if not new_name or not new_name.strip():
        return RedirectResponse(
            url=f"/artist/{quote(artist_name)}/edit?error=Name+cannot+be+empty",
            status_code=303
        )
    
    new_name = new_name.strip()
    
    updated = Album.update(artist=new_name).where(Album.artist == artist_name).execute()
    
    artist_record = Artist.select().where(Artist.name == artist_name).first()
    
    if image and image.filename:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = image.filename.rsplit('.', 1)[-1].lower() if '.' in image.filename else 'jpg'
        if ext in allowed_extensions:
            os.makedirs(ARTISTS_DIR, exist_ok=True)
            content = await image.read()
            resized_content, ext = resize_image(content)
            filename = f"{new_name.replace(' ', '_').replace('/', '_')}.{ext}"
            filepath = os.path.join(ARTISTS_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resized_content)
            
            if not artist_record:
                artist_record = Artist.create(
                    name=new_name,
                    image_url=filename
                )
            else:
                artist_record.image_url = filename
    
    genre_list = [g.strip() for g in genres.split(",") if g.strip()] if genres else []
    
    if not artist_record:
        artist_record = Artist.create(
            name=new_name,
            bio=bio.strip() if bio else None,
            genres=genre_list
        )
    else:
        artist_record.name = new_name
        artist_record.bio = bio.strip() if bio else None
        artist_record.genres = genre_list
        artist_record.save()
    
    return RedirectResponse(
        url=f"/artist/{quote(new_name)}?message=Artist+updated",
        status_code=303
    )

@router.post("/artist/{artist_name:path}/scrape")
async def scrape_artist_profile(artist_name: str, _: bool = Depends(require_admin)):
    result = await scrape_artist(artist_name)
    
    if result["updated"]:
        message = "Artist profile updated"
    else:
        message = "No updates available"
    
    return RedirectResponse(
        url=f"/artist/{quote(artist_name)}?message={message}",
        status_code=303
    )

@router.get("/artist/{artist_name:path}", response_class=HTMLResponse)
async def browse_artist(request: Request, artist_name: str, sort: str = "year", order: str = "asc", message: str = None):
    query = Album.select().where(Album.artist == artist_name)
    
    if sort == "title":
        query = query.order_by(Album.title.asc() if order == "asc" else Album.title.desc())
    else:
        query = query.order_by(Album.year.asc() if order == "asc" else Album.year.desc())
    
    albums = list(query)
    
    artist = Artist.select().where(Artist.name == artist_name).first()
    
    if not artist:
        result = await scrape_artist(artist_name)
        if result["created"]:
            artist = Artist.select().where(Artist.name == artist_name).first()
    
    return templates.TemplateResponse("browse_artist.html", {
        "request": request,
        "albums": albums,
        "artist_name": artist_name,
        "artist": artist,
        "sort": sort,
        "order": order,
        "message": message
    })

@router.get("/year/{year}", response_class=HTMLResponse)
async def browse_year(request: Request, year: int, sort: str = "title", order: str = "asc"):
    query = Album.select().where((Album.year == year) & (Album.is_wanted == False))
    
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

@router.get("/decade/{decade}", response_class=HTMLResponse)
async def browse_decade(request: Request, decade: str, sort: str = "artist", order: str = "asc"):
    try:
        decade_start = int(decade.replace('s', ''))
        decade_end = decade_start + 9
    except ValueError:
        decade_start = 0
        decade_end = 0
    
    query = Album.select().where(
        (Album.year >= decade_start) & (Album.year <= decade_end) & (Album.is_wanted == False)
    )
    
    if sort == "title":
        query = query.order_by(Album.title.asc() if order == "asc" else Album.title.desc())
    elif sort == "year":
        query = query.order_by(Album.year.asc() if order == "asc" else Album.year.desc())
    else:
        query = query.order_by(Album.artist.asc() if order == "asc" else Album.artist.desc())
    
    albums = list(query)
    
    return templates.TemplateResponse("browse_decade.html", {
        "request": request,
        "albums": albums,
        "decade": decade,
        "decade_start": decade_start,
        "decade_end": decade_end,
        "sort": sort,
        "order": order
    })

@router.get("/format/{format_name}", response_class=HTMLResponse)
async def browse_format(request: Request, format_name: str, sort: str = "artist", order: str = "asc"):
    query = Album.select().where((Album.physical_format == format_name) & (Album.is_wanted == False))
    
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
    albums = list(Album.select().where((Album.genres.contains(tag)) & (Album.is_wanted == False)))
    
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
