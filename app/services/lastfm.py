import os
import httpx
from typing import Optional, List
from app.config import LASTFM_API_KEY, UPLOAD_DIR

LASTFM_API_BASE = "https://ws.audioscrobbler.com/2.0/"


async def get_artist_top_tags(artist: str) -> List[str]:
    if not LASTFM_API_KEY:
        return []
    
    params = {
        "method": "artist.gettoptags",
        "artist": artist,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(LASTFM_API_BASE, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "toptags" not in data or "tag" not in data["toptags"]:
                return []
            
            tags = data["toptags"]["tag"]
            if not isinstance(tags, list):
                tags = [tags] if tags else []
            
            return [tag["name"] for tag in tags[:5] if isinstance(tag, dict) and "name" in tag]
    except Exception:
        return []


async def get_album_info(artist: str, album: str) -> dict:
    if not LASTFM_API_KEY:
        return {}
    
    params = {
        "method": "album.getinfo",
        "artist": artist,
        "album": album,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(LASTFM_API_BASE, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "album" not in data:
                return {}
            
            result = {}
            album_data = data["album"]
            
            if "image" in album_data:
                images = album_data["image"]
                for img in images:
                    if img.get("size") == "extralarge" and img.get("#text"):
                        result["cover_url"] = img["#text"]
                        break
            
            if "wiki" in album_data and "published" in album_data["wiki"]:
                published = album_data["wiki"]["published"]
                if published:
                    try:
                        result["year"] = int(published.split()[2][:4])
                    except (ValueError, IndexError):
                        pass
            
            return result
    except Exception:
        return {}


async def download_cover(cover_url: str, filename: str) -> Optional[str]:
    if not cover_url:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(cover_url)
            response.raise_for_status()
            
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            return f"/static/uploads/{filename}"
    except Exception:
        return None


async def scrape_album(album) -> dict:
    result = {
        "updated": False,
        "cover_updated": False,
        "year_updated": False,
        "genres_updated": False
    }
    
    needs_cover = not album.cover_image_path
    needs_year = not album.year
    needs_genres = not album.genres or album.genres == [] or album.genres == '[]'
    
    if not needs_cover and not needs_year and not needs_genres:
        return result
    
    if needs_cover or needs_year:
        album_info = await get_album_info(album.artist, album.title)
        
        if needs_cover and "cover_url" in album_info and album_info["cover_url"]:
            ext = album_info["cover_url"].split(".")[-1] or "jpg"
            if ext not in ["jpg", "jpeg", "png", "gif", "webp"]:
                ext = "jpg"
            filename = f"{album.artist}_{album.title}_{album.id}.{ext}".replace(" ", "_").replace("/", "_")
            cover_path = await download_cover(album_info["cover_url"], filename)
            if cover_path:
                album.cover_image_path = cover_path
                result["cover_updated"] = True
                result["updated"] = True
        
        if needs_year and "year" in album_info and album_info["year"]:
            album.year = album_info["year"]
            result["year_updated"] = True
            result["updated"] = True
    
    if needs_genres:
        tags = await get_artist_top_tags(album.artist)
        if tags:
            album.genres = tags
            result["genres_updated"] = True
            result["updated"] = True
    
    if result["updated"]:
        album.save()
    
    return result
