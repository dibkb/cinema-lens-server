from contextlib import asynccontextmanager
from qdrant_client import QdrantClient, models
import os
import asyncio
from typing import List
import numpy as np
from .entity import MovieEntities
@asynccontextmanager
async def get_qdrant_client():
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URI"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    yield qdrant_client
    qdrant_client.close()


async def get_movie_by_title(title: str):
    async with get_qdrant_client() as qdrant_client:
        # Use asyncio.to_thread to make the synchronous Qdrant operation non-blocking
        reference_movie = await asyncio.to_thread(
            qdrant_client.scroll,
            collection_name="movies_plot",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="title",
                        match=models.MatchText(text=title.lower())
                    )
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=True,
        )
    return reference_movie


async def get_movie_vectors(titles: List[str]):
    # Use gather to fetch all movie vectors in parallel
    tasks = [get_movie_by_title(title) for title in titles]
    results = await asyncio.gather(*tasks)
    
    vectors = []
    for result in results:
        if result[0] and len(result[0]) > 0:
            vectors.append(result[0][0].vector)
    
    return vectors


def average_vectors(vectors: List[np.ndarray]) -> np.ndarray:
    """Average multiple embeddings into a single vector"""
    if not vectors:
        raise ValueError("No vectors to average")
    return np.mean(vectors, axis=0).tolist()




async def find_similar_by_plot(entities: MovieEntities, top_k: int = 10) -> List[dict]:
    """
    Find similar movies by averaging plot embeddings of input titles
    Returns list of {title: str, similarity: float}
    """
    # Get reference movie vectors (already parallelized with the updated get_movie_vectors)
    vectors = await get_movie_vectors(entities.movie[0:min(len(entities.movie), 10)])
    if not vectors:
        return []
    # Create average vector
    query_vector = average_vectors(vectors)

    # Exclude original movies from results
    exclude_filter = models.Filter(
        must_not=[
            models.FieldCondition(
                key="title",
                match=models.MatchText(text=title.lower())
            )
            for title in entities.movie
        ]
    )

    # Search Qdrant
    async with get_qdrant_client() as qdrant_client:
        # Use asyncio.to_thread to make the synchronous operation non-blocking
        results = await asyncio.to_thread(
            qdrant_client.search,
            collection_name="movies_plot",
            query_vector=query_vector,
            query_filter=exclude_filter,
            limit=top_k,
            with_payload=["title"]
        )
    return [hit.payload["title"] for hit in results]



