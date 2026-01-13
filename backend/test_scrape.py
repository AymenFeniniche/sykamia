import asyncio
from tools import get_titles, get_filters, scrape_details

async def main():
    # 1) enrichit + écrit le cache
    data = await get_titles("series", order="asc")
    print("Total:", data["total"])
    print("Exemple:", data["items"][:3])

    # 2) ensuite seulement on calcule les filtres
    print(await get_filters("series"))

    # 3) test d'une page détail
    print(await scrape_details("https://www.themoviedb.org/tv/1396-breaking-bad"))

asyncio.run(main())
