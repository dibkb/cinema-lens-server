from serpapi import GoogleSearch
from .config import settings

def search_google(query: str) -> list[str]:
    params = {
        "engine": "google",
        "q": query,
        "api_key": settings.SERP_API_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    if "organic_results" not in results:
        return []

    return results["organic_results"]
