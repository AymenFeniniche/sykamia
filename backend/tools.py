from __future__ import annotations

import asyncio
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
    "movie": "https://www.themoviedb.org/movie",  
    "series": "https://www.themoviedb.org/tv",  
}

# sécurité: n'autoriser que certains domaines
ALLOWED_DOMAINS = {"www.themoviedb.org"}

# cache local (pas une DB): 7 jours
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

CACHE_TTL_SECONDS = 604800  # 7 jours


@dataclass
class TitleItem:
    title: str
    year: Optional[int] = None
    genre: Optional[str] = None
    country: Optional[str] = None
    poster_url: str = ""
    url: str = ""  # lien vers la page détail (optionnel)
    id: str = ""  # identifiant unique
    synopsis: Optional[str] = None
    duration: Optional[str] = None
    release_date: Optional[str] = None
    directors: Optional[str] = None
    actors: Optional[str] = None


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

    items: list[TitleItem] = []
    
    # Scraper plusieurs pages pour obtenir plus de contenu
    # TMDb affiche environ 20 items par page
    num_pages = 25  # Récupérer 25 pages = environ 500 films/séries
    
    for page in range(1, num_pages + 1):
        page_url = f"{source_url}?language=fr-FR&page={page}"
        print(f"Scraping page {page}/{num_pages}: {page_url}")
        
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(
                page_url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")

        # ----------------------------
        # TODO: ADAPTER ICI
        # ----------------------------
        # Exemple générique: chaque "card" contient titre + image + metadata
        page_items = 0
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

            # Générer un ID unique basé sur l'URL
            item_id = url.split('/')[-1] if url else f"item_{len(items)}"
            
            items.append(
                TitleItem(
                    title=title,
                    year=None,        
                    genre=None,       
                    country=None,     
                    poster_url=poster_url,
                    url=url,
                    id=item_id,
                )
            )
            page_items += 1
        
        print(f"  -> {page_items} items trouvés sur la page {page}")
        
        # Délai suffisant entre les pages pour éviter le blocage TMDb
        if page < num_pages:
            await asyncio.sleep(3)

    print(f"Total: {len(items)} items récupérés")
    return items

async def scrape_details(detail_url: str) -> dict:
    _ensure_allowed(detail_url)

    # Ajouter le paramètre de langue si pas présent
    if "?" not in detail_url:
        detail_url += "?language=fr-FR"
    elif "language=" not in detail_url:
        detail_url += "&language=fr-FR"

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(detail_url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    
    # Déterminer si c'est une série ou un film
    is_series = '/tv/' in detail_url

    # Année (extrait d'un header)
    header = soup.select_one("h2")
    header_text = _safe_text(header)

    m = re.search(r"\b(19\d{2}|20\d{2})\b", header_text)
    year = int(m.group(1)) if m else None

    # Genres (liens /genre)
    genres = [a.get_text(strip=True) for a in soup.select('a[href*="/genre/"]')]
    genre = " & ".join(genres[:3]) if genres else None
    
    # Synopsis
    synopsis_el = soup.select_one(".overview p")
    synopsis = _safe_text(synopsis_el) if synopsis_el else None
    
    # Durée ou nombre de saisons
    duration = None
    if is_series:
        # Pour les séries : chercher le nombre de saisons avec plusieurs méthodes
        all_text = soup.get_text()
        season_counts = []
        
        # Méthode 1: Chercher "Dernière saison Saison X"
        m1 = re.search(r'Derni[èe]re saison\s+Saison\s+(\d+)', all_text, re.IGNORECASE)
        if m1:
            season_counts.append(int(m1.group(1)))
        
        # Méthode 2: Chercher le maximum dans toutes les "Saison X" trouvées
        all_seasons_fr = re.findall(r'Saison\s+(\d+)', all_text)
        if all_seasons_fr:
            season_counts.append(max(map(int, all_seasons_fr)))
        
        # Méthode 3: Chercher "Season X" (en anglais)
        all_seasons_en = re.findall(r'Season\s+(\d+)', all_text, re.IGNORECASE)
        if all_seasons_en:
            season_counts.append(max(map(int, all_seasons_en)))
        
        # Méthode 4: Chercher "X saisons" ou "X seasons"
        m4 = re.search(r'(\d+)\s+saisons?', all_text, re.IGNORECASE)
        if m4:
            season_counts.append(int(m4.group(1)))
        
        m5 = re.search(r'(\d+)\s+seasons?', all_text, re.IGNORECASE)
        if m5:
            season_counts.append(int(m5.group(1)))
        
        # Prendre le maximum de toutes les méthodes
        if season_counts:
            num_seasons = max(season_counts)
            duration = f"{num_seasons} saison{'s' if num_seasons > 1 else ''}"
    else:
        # Pour les films : chercher la durée
        runtime_el = soup.select_one(".runtime")
        if runtime_el:
            duration = _safe_text(runtime_el)
    
    # Date de sortie
    release_date = None
    release_el = soup.select_one(".release_date")
    if release_el:
        release_date = _safe_text(release_el)
    
    # Réalisateurs (pour films) ou Créateurs (pour séries)
    directors = []
    crew_items = soup.select('ol.people li')
    
    # Pour les séries, chercher "Créateur/Créatrice"
    # Pour les films, chercher "Director"
    search_role = "Créateur" if is_series else "Director"
    
    for item in crew_items:
        job_el = item.select_one('p.character')
        if job_el:
            job_text = _safe_text(job_el)
            if search_role in job_text or (not is_series and 'Director' in job_text):
                name_el = item.select_one('p a')
                if name_el:
                    directors.append(_safe_text(name_el))
                    if len(directors) >= 3:
                        break
    
    directors_str = ", ".join(directors) if directors else None
    
    # Acteurs principaux (Cast)
    actors = []
    all_people = soup.select('ol.people li')
    
    for item in all_people:
        character_el = item.select_one('p.character')
        name_el = item.select_one('p a')
        
        if name_el and character_el:
            character_text = _safe_text(character_el)
            if not any(role in character_text for role in ['Director', 'Writer', 'Producer', 'Screenplay', 'Story', 'Novel', 'Characters', 'Créateur', 'Créatrice']):
                actors.append(_safe_text(name_el))
                if len(actors) >= 5:
                    break
    
    actors_str = ", ".join(actors) if actors else None
    
    country = None

    return {
        "year": year, 
        "genre": genre, 
        "country": country,
        "synopsis": synopsis,
        "duration": duration,
        "release_date": release_date,
        "directors": directors_str,
        "actors": actors_str
    }


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
        # Scraper les détails pour les 50 premiers items seulement (pour performance)
        for i, it in enumerate(items[:50]):
            if it.url:
                try:
                    print(f"Détails {i+1}/50: {it.title}")
                    d = await scrape_details(it.url)
                    it.year = d.get("year") or it.year
                    it.genre = d.get("genre") or it.genre
                    it.country = d.get("country") or it.country
                    it.synopsis = d.get("synopsis")
                    it.duration = d.get("duration")
                    it.release_date = d.get("release_date")
                    it.directors = d.get("directors")
                    it.actors = d.get("actors")
                    await asyncio.sleep(1)  # Délai entre les requêtes
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

