from collections import Counter
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.models import Album
from app.templates_globals import templates

router = APIRouter()

def get_decade(year):
    if year is None or year == 0:
        return "Unknown"
    return f"{(year // 10) * 10}s"

def get_stats_data():
    albums = list(Album.select().where(Album.is_wanted == False))
    
    decade_counts = Counter(get_decade(a.year) for a in albums)
    decades = sorted(
        [(d, c) for d, c in decade_counts.items() if d != "Unknown"],
        key=lambda x: int(x[0][:-1])
    )
    if "Unknown" in decade_counts:
        decades.append(("Unknown", decade_counts["Unknown"]))
    
    format_counts = Counter(a.physical_format or "Unknown" for a in albums)
    formats = sorted(format_counts.items(), key=lambda x: -x[1])
    
    artist_counts = Counter(a.artist for a in albums)
    top_artists = artist_counts.most_common(20)
    
    return {
        "decades": decades,
        "formats": formats,
        "top_artists": top_artists,
        "total": len(albums)
    }

@router.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    return templates.TemplateResponse("stats.html", {
        "request": request
    })

@router.get("/stats/data")
async def stats_data():
    return JSONResponse(get_stats_data())
