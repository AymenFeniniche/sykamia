from __future__ import annotations

import json
import time
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import httpx
from bs4 import BeautifulSoup

TitleType = Literal["movie", "series"]

# ----------------------------
# CONFIG
# ----------------------------

SOURCES: dict[TitleType, str] = {
    "movie": "https://www.themoviedb.org/movie",   # TODO
    "series": "https://www.themoviedb.org/tv",  # TODO
}

# sécurité: n'autoriser que certains domaines
ALLOWED_DOMAINS = {"www.themoviedb.org"}

# cache local (pas une DB): 1h
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 3600


@dataclass
class TitleItem:
    title: str
    year: Optional[int] = None
    genre: Optional[str] = None
    country: Optional[str] = None
    poster_url: str = ""
    url: str = ""  # lien vers la page détail (optionnel)


def _domain_from_url(url: str) -> str:
    return url.split("//", 1)[-1].split("/", 1)[0].lower()


def _ensure_allowed(url: str) -> None:
    domain = _domain_from_url(url)
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"Domaine non autorisé pour scraping: {domain}")


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _read_cache(key: str) -> Optional[list[dict]]:
    path = _cache_path(key)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    ts = payload.get("ts", 0)
    if time.time() - ts > CACHE_TTL_SECONDS:
        return None
    return payload.get("value")


def _write_cache(key: str, value: list[dict]) -> None:
    path = _cache_path(key)
    payload = {"ts": time.time(), "value": value}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _safe_text(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _to_int(s: str) -> Optional[int]:
    s = "".join(ch for ch in s if ch.isdigit())
    return int(s) if s.isdigit() else None


async def scrape_titles(type_: TitleType) -> list[TitleItem]:
    source_url = SOURCES[type_]
    _ensure_allowed(source_url)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(
            source_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    items: list[TitleItem] = []

    # ----------------------------
    # TODO: ADAPTER ICI
    # ----------------------------
    # Exemple générique: chaque "card" contient titre + image + metadata
    for card in soup.select("div.card"):
        link = card.select_one("a.image")
        img = card.select_one("img")

        if not link:
            continue

        title = link.get("title", "").strip()
        if not title:
            continue

        url = link.get("href", "")
        if url.startswith("/"):
            url = "https://www.themoviedb.org" + url

        poster_url = img.get("src", "") if img else ""

        items.append(
            TitleItem(
                title=title,
                year=None,        
                genre=None,       
                country=None,     
                poster_url=poster_url,
                url=url,
            )
        )

    return items

async def scrape_details(detail_url: str) -> dict:
    _ensure_allowed(detail_url)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(detail_url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # Année (extrait d'un header)
    header = soup.select_one("h2")
    header_text = _safe_text(header)

    m = re.search(r"\b(19\d{2}|20\d{2})\b", header_text)
    year = int(m.group(1)) if m else None

    # Genres (liens /genre)
    genres = [a.get_text(strip=True) for a in soup.select('a[href*="/genre/"]')]
    genre = genres[0] if genres else None

    
    country = None  # Pays: pas fiable sur TMDb via scraping HTML -> on laisse None

    return {"year": year, "genre": genre, "country": country}


def filter_and_sort(
    items: list[TitleItem],
    q: str | None = None,
    genre: str | None = None,
    year: int | None = None,
    country: str | None = None,
    order: Literal["asc", "desc"] = "asc",
) -> list[TitleItem]:
    def norm(s: str) -> str:
        return s.strip().lower()

    out: list[TitleItem] = []
    for it in items:
        if q and norm(q) not in norm(it.title):
            continue
        if genre and it.genre != genre:
            continue
        if year is not None and it.year != year:
            continue
        if country and it.country != country:
            continue
        out.append(it)

    out.sort(key=lambda x: x.title.lower(), reverse=(order == "desc"))
    return out


async def get_titles(
    type_: TitleType,
    q: str | None = None,
    genre: str | None = None,
    year: int | None = None,
    country: str | None = None,
    order: Literal["asc", "desc"] = "asc",
) -> dict:
    """
    Fonction "tool" principale côté backend:
    - charge depuis cache si possible
    - sinon scrape
    - applique filtres/tri
    - renvoie dict JSON-friendly
    """
    cache_key = f"titles_{type_}"
    cached = _read_cache(cache_key)

    if cached is not None:
        items = [TitleItem(**d) for d in cached]
    else:
        items = await scrape_titles(type_)
        for it in items[:20]:
            if it.url:
                try:
                    d = await scrape_details(it.url)
                    it.year = d.get("year") or it.year
                    it.genre = d.get("genre") or it.genre
                    it.country = d.get("country") or it.country
                except Exception as e:
                    print("DETAIL ERROR:", it.url, e)


        _write_cache(cache_key, [it.__dict__ for it in items])


    filtered = filter_and_sort(items, q=q, genre=genre, year=year, country=country, order=order)

    return {
        "total": len(filtered),
        "items": [it.__dict__ for it in filtered],
    }


async def get_filters(type_: TitleType) -> dict:
    # on récupère les titres enrichis (via get_titles)
    data = await get_titles(type_)
    items = [TitleItem(**d) for d in data["items"]]

    genres = sorted({it.genre for it in items if it.genre})
    years = sorted({it.year for it in items if it.year}, reverse=True)
    countries = sorted({it.country for it in items if it.country})

    return {"genres": genres, "years": years, "countries": countries}

