import os
import html
import httpx
import logging
import re
import asyncio
import time
from urllib.parse import quote
from typing import Optional, List
from app.config import LASTFM_API_KEY, USER_AGENT, COVERS_DIR, ARTISTS_DIR
from app.services.image_utils import resize_image
from app.models import Artist
from app.utils.artists import split_artists, apply_artist_mapping, sanitize_filename

logger = logging.getLogger(__name__)
LASTFM_API_BASE = "https://ws.audioscrobbler.com/2.0/"

_last_request_time = 0.0


async def rate_limited_request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    global _last_request_time
 
    headers = kwargs.pop("headers", {})
    headers["User-Agent"] = USER_AGENT

    params = kwargs.pop("params", None)

    full_url = url
    if params:
        full_url = str(httpx.URL(url).copy_with(params=params))

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        elapsed = time.time() - _last_request_time
        if elapsed < 1.0:
            wait_time = 1.0 - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        logger.debug(f"Last.fm request: {method} {full_url}")

        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params, **kwargs)
            else:
                response = await client.post(url, headers=headers, params=params, **kwargs)

            _last_request_time = time.time()

            if response.status_code >= 500:
                logger.warning(f"Last.fm server error {response.status_code}, attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue

            if response.status_code >= 400:
                safe_url = re.sub(r'api_key=[^&]*', 'api_key=***', full_url)
                logger.error(f"Last.fm error: {response.status_code} {response.reason_phrase} for {safe_url}")
                raise Exception(f"Last.fm error: {response.status_code} {response.reason_phrase}")

            logger.debug(f"Last.fm response: {response.status_code} - Success")
            return response
        except httpx.HTTPStatusError as e:
            _last_request_time = time.time()
            if attempt < max_retries - 1:
                logger.warning(f"Last.fm HTTP error, retrying: {e.response.status_code} {e.response.reason_phrase}")
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            safe_url = re.sub(r'api_key=[^&]*', 'api_key=***', str(e.request.url))
            logger.error(f"Last.fm error: {e.response.status_code} {e.response.reason_phrase} for {safe_url}")
            raise
        except Exception as e:
            _last_request_time = time.time()
            if attempt < max_retries - 1:
                logger.warning(f"Last.fm request failed, retrying: {e}")
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            safe_url = re.sub(r'api_key=[^&]*', 'api_key=***', full_url)
            logger.error(f"Last.fm request failed: {e} for {safe_url}")
            raise

    raise Exception(f"Last.fm request failed after {max_retries} retries: {full_url}")


async def get_artist_image_and_genres_from_html(artist_name: str) -> tuple:
    """Scrape artist image and genres from Last.fm HTML page"""
    try:
        encoded_name = quote(artist_name, safe='').replace("%20", "+")
        url = f"https://www.last.fm/music/{encoded_name}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.debug(f"Last.fm scraping artist HTML: {artist_name}")
            response = await rate_limited_request(client, "GET", url, follow_redirects=True)

            image_url = None
            match = re.search(r'header-new-background-image[^>]*style="background-image:\s*url\(([^)]+)\)', response.text)
            if match:
                image_url = match.group(1).strip('"\'')
                logger.debug(f"Last.fm artist image found for {artist_name}: {image_url}")

            if not image_url:
                match = re.search(r'header-new-background-image[^>]*content="([^"]+)"', response.text)
                if match:
                    image_url = match.group(1)
                    logger.debug(f"Last.fm artist image found for {artist_name} (content attr): {image_url}")

            if not image_url:
                logger.debug(f"Last.fm no artist image found for {artist_name}")

            genres = []
            tag_matches = re.findall(r'data-tag-name="([^"]+)"', response.text)
            logger.debug(f"Last.fm tag matches (data-tag) for {artist_name}: {tag_matches}")
            if not tag_matches:
                tag_matches = re.findall(r'<a[^>]*href="/tag/([^"]+)"', response.text)
                logger.debug(f"Last.fm tag matches (/tag/) for {artist_name}: {tag_matches}")
            genres = [g.strip() for g in tag_matches if g.strip() and g.strip().lower() not in ['add tags', 'view all tags']][:5]

            bio = None
            bio_match = re.search(r'<div class="wiki-block-inner[^>]*>(.*?)</div>', response.text, re.DOTALL)
            if bio_match:
                bio = re.sub(r'<[^>]+>', '', bio_match.group(1)).strip()
                bio = re.sub(r'\s+', ' ', bio)

            if genres:
                logger.debug(f"Last.fm genres from HTML for {artist_name}: {genres}")
            if bio:
                logger.debug(f"Last.fm bio from HTML for {artist_name}: {bio[:100]}...")

            return image_url, genres, bio
    except Exception as e:
        logger.error(f"Last.fm error scraping artist HTML for {artist_name}: {e}")
        return None, []


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
            logger.debug(f"Last.fm API call: artist.getinfo for {artist_name}")
            response = await rate_limited_request(client, "GET", LASTFM_API_BASE, params=params)
            data = response.json()

            if "artist" not in data:
                logger.warning(f"Last.fm no artist data for: {artist_name}")
                return {}

            result = {}
            artist_data = data["artist"]

            image_url, html_genres, html_bio = await get_artist_image_and_genres_from_html(artist_name)
            if image_url:
                result["image_url"] = image_url

            if "bio" in artist_data and "summary" in artist_data["bio"]:
                bio = artist_data["bio"]["summary"]
                bio = html.unescape(bio)
                if "<a" in bio:
                    bio = bio.split("<a")[0].strip()
                if bio:
                    result["bio"] = bio

            if not result.get("bio") and html_bio:
                result["bio"] = html_bio

            if "tags" in artist_data and "tag" in artist_data["tags"]:
                tags = artist_data["tags"]["tag"]
                logger.debug(f"Last.fm raw tags for {artist_name}: {tags}")
                if not isinstance(tags, list):
                    tags = [tags] if tags else []
                result["genres"] = [tag["name"] for tag in tags[:5] if isinstance(tag, dict) and "name" in tag]
                logger.debug(f"Last.fm parsed genres for {artist_name}: {result.get('genres')}")

            if not result.get("genres") and html_genres:
                result["genres"] = html_genres
                logger.debug(f"Last.fm genres from HTML for {artist_name}: {html_genres}")

            if "url" in artist_data:
                result["lastfm_url"] = artist_data["url"]

            logger.debug(f"Last.fm artist info retrieved for {artist_name}")
            return result
    except Exception as e:
        logger.error(f"Last.fm error fetching artist info for {artist_name}: {e}")
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
            logger.debug(f"Last.fm API call: artist.gettoptags for {artist}")
            response = await rate_limited_request(client, "GET", LASTFM_API_BASE, params=params)
            data = response.json()

            if "toptags" not in data or "tag" not in data["toptags"]:
                logger.debug(f"Last.fm no top tags for {artist}")
                return []

            tags = data["toptags"]["tag"]
            logger.debug(f"Last.fm raw toptags for {artist}: {tags}")
            if not isinstance(tags, list):
                tags = [tags] if tags else []

            result_tags = [tag["name"] for tag in tags[:5] if isinstance(tag, dict) and "name" in tag]
            logger.debug(f"Last.fm parsed toptags for {artist}: {result_tags}")
            return result_tags
    except Exception as e:
        logger.error(f"Last.fm error getting top tags for {artist}: {e}")
        return []


async def get_album_info_from_html(artist: str, album: str) -> dict:
    """Scrape album cover and year from Last.fm HTML page"""
    try:
        encoded_artist = quote(artist, safe='').replace("%20", "+")
        encoded_album = quote(album, safe='').replace("%20", "+")
        url = f"https://www.last.fm/music/{encoded_artist}/{encoded_album}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.debug(f"Last.fm scraping album HTML: {artist} - {album}")
            response = await rate_limited_request(client, "GET", url, follow_redirects=True)

            year = None
            year_patterns = [
                r'<dt class="catalogue-metadata-heading">Release Date</dt>\s*<dd class="catalogue-metadata-description">[^<]*(\d{4})</dd>',
                r'<dd class="catalogue-metadata-description">(\d+)\s+\w+\s+(\d{4})</dd>',
                r'<dd class="catalogue-metadata-description">(\d{4})</dd>',
                r'"datePublished"\s*:\s*"(\d{4})',
                r'<time[^>]*datetime="(\d{4})',
            ]
            for pattern in year_patterns:
                match = re.search(pattern, response.text)
                if match:
                    year = int(match.group(1))
                    logger.debug(f"Last.fm release year found for {artist} - {album}: {year}")
                    break

            if not year:
                logger.debug(f"Last.fm no release date found for {artist} - {album}")

            cover_url = None
            cover_match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
            if cover_match:
                cover_url = cover_match.group(1)
                logger.debug(f"Last.fm album cover found for {artist} - {album}: {cover_url}")

            return {"year": year, "cover_url": cover_url}
    except Exception as e:
        logger.error(f"Last.fm error scraping album HTML for {artist} - {album}: {e}")
        return {}


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

    result = {}
    api_success = False

    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Last.fm API call: album.getinfo for {artist} - {album}")
            response = await rate_limited_request(client, "GET", LASTFM_API_BASE, params=params)
            data = response.json()

            if "album" in data:
                api_success = True
                album_data = data["album"]

                if "image" in album_data:
                    images = album_data["image"]
                    for img in images:
                        if img.get("size") == "extralarge" and img.get("#text"):
                            result["cover_url"] = img["#text"]
                            break
    except Exception as e:
        logger.debug(f"Last.fm API failed for {artist} - {album}, trying HTML: {e}")

    if not result.get("cover_url") or not result.get("year"):
        html_info = await get_album_info_from_html(artist, album)

        if not result.get("cover_url") and html_info.get("cover_url"):
            result["cover_url"] = html_info["cover_url"]

        if not result.get("year") and html_info.get("year"):
            result["year"] = html_info["year"]

    if result:
        logger.debug(f"Last.fm album info retrieved for {artist} - {album}")

    return result


async def download_cover(cover_url: str, filename: str) -> Optional[str]:
    if not cover_url:
        return None

    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Downloading cover from: {cover_url}")
            response = await client.get(cover_url)
            response.raise_for_status()

            content = response.content
            resized_content, ext = resize_image(content)

            filename = filename.rsplit('.', 1)[0] + f'.{ext}'

            os.makedirs(COVERS_DIR, exist_ok=True)
            filepath = os.path.join(COVERS_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(resized_content)

            logger.debug(f"Cover downloaded successfully: {filename}")
            return filename
    except Exception as e:
        logger.error(f"Error downloading cover from {cover_url}: {e}")
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
    
    artist_list = split_artists(album.artist)
    artist_list = [apply_artist_mapping(a) for a in artist_list]
    artist_variants = artist_list.copy()
    for artist in artist_list:
        artist_variants.append(artist)

    if needs_cover or needs_year:
        album_info = {}
        for artist_name in artist_variants:
            album_info = await get_album_info(artist_name, album.title)
            if album_info.get('cover_url') or album_info.get('year'):
                break

        if needs_cover and album_info.get("cover_url"):
            ext = album_info["cover_url"].split(".")[-1] or "jpg"
            if ext not in ["jpg", "jpeg", "png", "gif", "webp"]:
                ext = "jpg"
            filename = f"{sanitize_filename(album.artist)}_{sanitize_filename(album.title)}_{album.id}.{ext}".replace(" ", "_").replace("/", "_")
            cover_path = await download_cover(album_info["cover_url"], filename)
            if cover_path:
                album.cover_image_path = cover_path
                result["cover_updated"] = True
                result["updated"] = True

        if needs_year and album_info.get("year"):
            album.year = album_info["year"]
            result["year_updated"] = True
            result["updated"] = True
    
    if needs_genres:
        for artist_name in artist_variants:
            tags = await get_artist_top_tags(artist_name)
            if tags:
                album.genres = tags
                result["genres_updated"] = True
                result["updated"] = True
                break

    if result["updated"]:
        album.save()

    return result


async def download_artist_image(image_url: str, artist_name: str) -> Optional[str]:
    if not image_url:
        return None

    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Downloading artist image from: {image_url}")
            response = await client.get(image_url)
            response.raise_for_status()

            content = response.content
            resized_content, ext = resize_image(content)

            filename = f"{artist_name.replace(' ', '_').replace('/', '_')}.{ext}"

            os.makedirs(ARTISTS_DIR, exist_ok=True)
            filepath = os.path.join(ARTISTS_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(resized_content)

            logger.debug(f"Artist image downloaded successfully: {filename}")
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
    if artist_info.get("image_url") and not (artist and artist.image_url):
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

    if image_filename:
        logger.debug(f"Image updated for {artist_name}: {image_filename}")
        artist.image_url = image_filename
        result["image_updated"] = True
        result["updated"] = True

    bio_val = artist_info.get("bio")
    if bio_val:
        logger.debug(f"Bio check for {artist_name}: new={bio_val[:50]}..., existing={(artist.bio or '')[:50]}...")
        if bio_val != (artist.bio or ""):
            artist.bio = bio_val
            result["bio_updated"] = True
            result["updated"] = True

    genres_val = artist_info.get("genres")
    if genres_val:
        logger.debug(f"Genres check for {artist_name}: new={genres_val}, existing={artist.genres or []}")
        if genres_val != (artist.genres or []):
            artist.genres = genres_val
            result["genres_updated"] = True
            result["updated"] = True
    
    logger.debug(f" scrape_artist result for {artist_name}: {result}")

    if artist_info.get("lastfm_url") and artist_info["lastfm_url"] != artist.lastfm_url:
        artist.lastfm_url = artist_info["lastfm_url"]

    if result["updated"]:
        artist.save()

    return result


def get_or_create_artist(artist_name: str):
    artist = Artist.select().where(Artist.name == artist_name).first()
    return artist
