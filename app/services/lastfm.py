import os
import html
import httpx
import logging
import re
from urllib.parse import quote
from typing import Optional, List
from app.config import LASTFM_API_KEY, COVERS_DIR, ARTISTS_DIR
from app.services.image_utils import resize_image
from app.models import Artist

logger = logging.getLogger(__name__)
LASTFM_API_BASE = "https://ws.audioscrobbler.com/2.0/"


async def get_artist_image_from_html(artist_name: str) -> Optional[str]:
    """Scrape artist image from Last.fm HTML page"""
    try:
        encoded_name = quote(artist_name, safe='')
        url = f"https://www.last.fm/music/{encoded_name}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # Look for header-new-background-image with background-image style
            match = re.search(r'header-new-background-image[^>]*style="background-image:\s*url\(([^)]+)\)', response.text)
            if match:
                image_url = match.group(1).strip('"\'')
                logger.info(f"Found artist image from HTML for {artist_name}: {image_url}")
                return image_url
            
            # Also try the content attribute on the same element
            match = re.search(r'header-new-background-image[^>]*content="([^"]+)"', response.text)
            if match:
                image_url = match.group(1)
                logger.info(f"Found artist image from content attr for {artist_name}: {image_url}")
                return image_url
            
            logger.info(f"No artist image found in HTML for {artist_name}")
            return None
    except Exception as e:
        logger.error(f"Error scraping artist HTML for {artist_name}: {e}")
        return None


async def get_artist_info(artist_name: str) -> dict:
    if not LASTFM_API_KEY:
        logger.warning("LASTFM_API_KEY not configured")
        return {}
    
    params = {
        "method": "artist.getinfo",
        "artist": artist_name,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(LASTFM_API_BASE, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "artist" not in data:
                logger.warning(f"No artist data for: {artist_name}")
                return {}
            
            result = {}
            artist_data = data["artist"]
            
            # Try scraping image from HTML instead of API
            image_url = await get_artist_image_from_html(artist_name)
            if image_url:
                result["image_url"] = image_url
            
            if "bio" in artist_data and "summary" in artist_data["bio"]:
                bio = artist_data["bio"]["summary"]
                bio = html.unescape(bio)
                if "<a" in bio:
                    bio = bio.split("<a")[0].strip()
                if bio:
                    result["bio"] = bio
            
            if "tags" in artist_data and "tag" in artist_data["tags"]:
                tags = artist_data["tags"]["tag"]
                if not isinstance(tags, list):
                    tags = [tags] if tags else []
                result["genres"] = [tag["name"] for tag in tags[:5] if isinstance(tag, dict) and "name" in tag]
            
            if "url" in artist_data:
                result["lastfm_url"] = artist_data["url"]
            
            return result
    except Exception as e:
        logger.error(f"Error fetching artist info for {artist_name}: {e}")
        return {}


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


async def get_album_release_year_from_html(artist: str, album: str) -> Optional[int]:
    try:
        encoded_artist = quote(artist, safe='')
        encoded_album = quote(album, safe='')
        url = f"https://www.last.fm/music/{encoded_artist}/{encoded_album}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            import re
            match = re.search(r'<dd class="catalogue-metadata-description">(\d+)\s+\w+\s+(\d{4})</dd>', response.text)
            if match:
                return int(match.group(2))
            
            match = re.search(r'<dd class="catalogue-metadata-description">(\d{4})</dd>', response.text)
            if match:
                return int(match.group(1))
            
            logger.warning(f"No release date found for {artist} - {album}")
            return None
    except Exception as e:
        logger.error(f"Error scraping album HTML for {artist} - {album}: {e}")
        return None


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
            
            year = await get_album_release_year_from_html(artist, album)
            if year:
                result["year"] = year
            
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
            
            content = response.content
            resized_content, ext = resize_image(content)
            
            filename = filename.rsplit('.', 1)[0] + f'.{ext}'
            
            os.makedirs(COVERS_DIR, exist_ok=True)
            filepath = os.path.join(COVERS_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(resized_content)
            
            return filename
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


async def download_artist_image(image_url: str, artist_name: str) -> Optional[str]:
    if not image_url:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            
            content = response.content
            resized_content, ext = resize_image(content)
            
            filename = f"{artist_name.replace(' ', '_').replace('/', '_')}.{ext}"
            
            os.makedirs(ARTISTS_DIR, exist_ok=True)
            filepath = os.path.join(ARTISTS_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(resized_content)
            
            return filename
    except Exception as e:
        logger.error(f"Error downloading artist image for {artist_name}: {e}")
        return None


async def scrape_artist(artist_name: str) -> dict:
    result = {
        "updated": False,
        "created": False,
        "image_updated": False,
        "bio_updated": False,
        "genres_updated": False
    }
    
    if not LASTFM_API_KEY:
        return result
    
    artist_info = await get_artist_info(artist_name)
    
    if not artist_info:
        return result
    
    artist = Artist.select().where(Artist.name == artist_name).first()
    
    image_filename = None
    if artist_info.get("image_url"):
        image_filename = await download_artist_image(artist_info["image_url"], artist_name)
    
    if not artist:
        artist = Artist.create(
            name=artist_name,
            image_url=image_filename,
            bio=artist_info.get("bio"),
            genres=artist_info.get("genres", []),
            lastfm_url=artist_info.get("lastfm_url")
        )
        result["created"] = True
        result["updated"] = True
        return result
    
    if image_filename and image_filename != artist.image_url:
        artist.image_url = image_filename
        result["image_updated"] = True
        result["updated"] = True
    
    if artist_info.get("bio") and artist_info["bio"] != artist.bio:
        artist.bio = artist_info["bio"]
        result["bio_updated"] = True
        result["updated"] = True
    
    if artist_info.get("genres") and artist_info["genres"] != artist.genres:
        artist.genres = artist_info["genres"]
        result["genres_updated"] = True
        result["updated"] = True
    
    if artist_info.get("lastfm_url") and artist_info["lastfm_url"] != artist.lastfm_url:
        artist.lastfm_url = artist_info["lastfm_url"]
    
    if result["updated"]:
        artist.save()
    
    return result


def get_or_create_artist(artist_name: str):
    artist = Artist.select().where(Artist.name == artist_name).first()
    return artist
