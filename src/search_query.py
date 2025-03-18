from .entity import MovieEntities

def build_reddit_search_query(entities: MovieEntities) -> str:
    if entities.search_query:
        return f"site:reddit.com {entities.search_query}"
    return ""
def build_letterboxd_search_query(entities: MovieEntities) -> str:
    if entities.search_query:
        return f"site:letterboxd.com {entities.search_query}"
    return ""