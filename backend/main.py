from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
from pydantic import BaseModel
import httpx

from tools import get_titles, get_filters

# Types autorisés
TitleType = Literal["movie", "series"]
OrderType = Literal["asc", "desc"]

# 🔹 Création de l'app FastAPI
app = FastAPI(title="IA Bot API")

# 🔹 CORS (pour que le front puisse appeler l'API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500","http://127.0.0.1:8000","http://localhost:8000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 🔹 Endpoint : récupérer films / séries
@app.get("/api/titles")
async def api_titles(
    type: TitleType = Query(..., description="movie ou series"),
    q: str | None = None,
    genre: str | None = None,
    year: int | None = None,
    order: OrderType = "asc",
):
    return await get_titles(
        type,
        q=q,
        genre=genre,
        year=year,
        order=order,
    )

# 🔹 Endpoint : récupérer les filtres
@app.get("/api/filters")
async def api_filters(
    type: TitleType = Query(..., description="movie ou series"),
):
    return await get_filters(type)

# 🔹 Endpoint : récupérer les détails d'un film/série
@app.get("/api/details")
async def api_details(
    type: TitleType = Query(..., description="movie ou series"),
    id: str = Query(..., description="ID du film ou série"),
):
    """
    Récupère les détails complets d'un film ou série
    """
    from tools import get_titles
    
    # Récupérer tous les titres pour trouver celui qui correspond à l'ID
    data = await get_titles(type)
    items = data.get("items", [])
    
    # Trouver l'item correspondant
    item = None
    for it in items:
        if it.get("id") == id:
            item = it
            break
    
    if not item:
        return {
            "id": id,
            "title": "Film/Série non trouvé",
            "poster_url": "",
            "genre": "N/A",
            "year": "N/A",
            "duration": "N/A",
            "synopsis": "Les détails de ce titre ne sont pas disponibles.",
            "directors": "N/A",
            "actors": "N/A",
            "release_date": "N/A"
        }
    
    # Construire la réponse avec les données disponibles
    return {
        "id": item.get("id", ""),
        "title": item.get("title", "Titre inconnu"),
        "poster_url": item.get("poster_url", ""),
        "genre": item.get("genre", "Non spécifié"),
        "year": str(item.get("year", "")) if item.get("year") else "N/A",
        "duration": item.get("duration") or "N/A",
        "synopsis": item.get("synopsis") or "Synopsis non disponible pour le moment.",
        "directors": item.get("directors") or "Non disponible",
        "actors": item.get("actors") or "Non disponible",
        "release_date": item.get("release_date") or (str(item.get("year", "N/A")) if item.get("year") else "N/A")
    }

# 🔹 Endpoint : récupérer les recommandations
@app.get("/api/recommendations")
async def api_recommendations(
    type: TitleType = Query(..., description="movie ou series"),
    id: str = Query(..., description="ID du film ou série actuel"),
    limit: int = Query(6, description="Nombre de recommandations"),
):
    """
    Récupère des recommandations basées sur le genre du titre actuel
    """
    from tools import get_titles
    
    # Récupérer tous les titres
    data = await get_titles(type)
    items = data.get("items", [])
    
    # Trouver l'item actuel pour obtenir son genre
    current_item = None
    for it in items:
        if it.get("id") == id:
            current_item = it
            break
    
    if not current_item:
        return {"items": []}
    
    # Extraire les genres de l'item actuel
    current_genres = (current_item.get("genre") or "").split(" & ")
    
    # Trouver des items similaires
    recommendations = []
    for item in items:
        # Ne pas recommander l'item lui-même
        if item.get("id") == id:
            continue
        
        # Vérifier si partage au moins un genre
        item_genres = (item.get("genre") or "").split(" & ")
        if any(g in item_genres for g in current_genres if g):
            recommendations.append({
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "poster_url": item.get("poster_url", ""),
                "genre": item.get("genre", ""),
                "year": item.get("year")
            })
        
        if len(recommendations) >= limit:
            break
    
    return {"items": recommendations}

@app.get("/ping")
def ping():
    return {"status": "ok"}

class ChatRequest(BaseModel):
    message: str
    model: str | None = "llama3.2"   # tu peux changer plus tard


@app.post("/api/chat")
async def api_chat(payload: ChatRequest):

    # Instructions données à l'IA
    prompt = f"""
Tu es un assistant de recommandation de films/séries.

Règle 1 : si la demande est vague (ex: "conseille-moi un film" sans genre / mood / époque / film vs série),
pose d'abord 2 questions maximum pour préciser (genre, ambiance, époque, durée, pays, film ou série).
Ne donne pas de liste tant que l'utilisateur n'a pas répondu.

Règle 2 : si l'utilisateur donne au moins un critère (genre OU ambiance OU année/époque OU film/série),
alors réponds avec une liste claire (maximum 5).

Format liste :
- Titre — année — genre — 1 raison courte

Important : si tu fais une liste, utilise des puces "-" (pas de paragraphe).

Message utilisateur :
{payload.message}
"""

    # Appel à Ollama (IA locale)
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": payload.model or "llama3.2",
                "prompt": prompt,
                "stream": False
            }
        )

    data = response.json()

    # On renvoie uniquement la réponse texte de l'IA
    return {
        "answer": data.get("response", "").strip()
    }
