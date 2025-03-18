from .entity import MovieEntities

def build_reddit_search_query(entities: MovieEntities) -> str:
    query_parts = []

    # Process movie titles
    if entities.movie:
        movie_query = " OR ".join(f'"{title}"' for title in entities.movie)
        query_parts.append(f"({movie_query})")

        combined_query = " AND ".join(query_parts)
        search_query = f"site:reddit.com Movies like {combined_query}"
        return search_query

    # Process actors
    if entities.actor:
        actor_query = " OR ".join(f'"{name}"' for name in entities.actor)
        query_parts.append(f"({actor_query})")

        combined_query = " AND ".join(query_parts)
        search_query = f"site:reddit.com Movies starring {combined_query}"
        return search_query

    # Process directors
    if entities.director:
        director_query = " OR ".join(f'"{name}"' for name in entities.director)
        query_parts.append(f"({director_query})")

        combined_query = " AND ".join(query_parts)
        search_query = f"site:reddit.com Movies directed by {combined_query}"
        return search_query

    # Process genres
    if entities.genre:
        genre_query = " OR ".join(f'"{genre}"' for genre in entities.genre)
        query_parts.append(f"({genre_query})")

        combined_query = " AND ".join(query_parts)
        search_query = f"site:reddit.com Movies in {combined_query}"
        return search_query
