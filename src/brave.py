import httpx
from .config import settings

def search_brave(query: str):
    print(f"Querying Brave with: {query}")
    url = "https://api.search.brave.com/res/v1/web/search"
    params = {
        "q": query,
    }
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY
    }

    response = httpx.get(url, params=params, headers=headers)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
        return None

    json_response = response.json()
    if "web" in json_response:
        results = json_response["web"]["results"]
        return results
    else:
        print("No results found")
        return None
