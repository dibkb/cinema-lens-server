from contextlib import asynccontextmanager
from qdrant_client import QdrantClient, models
import os
import asyncio

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
                        match=models.MatchText(text=title)
                    )
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=True,
        )
    return reference_movie


async def get_movie_by_reference(reference_movie:dict):
    async with get_qdrant_client() as qdrant_client:
        reference_embedding = reference_movie[0].vector
        # Use asyncio.to_thread to make the synchronous Qdrant operation non-blocking
        similar_movies = await asyncio.to_thread(
            qdrant_client.search,
            collection_name="movies_plot",
            query_vector=reference_embedding,
            query_filter=models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="title", 
                        match=models.MatchValue(value=reference_movie[0].payload["title"])
                    )
                ]
            ),
            limit=10,
            with_payload=True,
            with_vectors=False,
        )
    return [movie.payload["title"].strip().lower() for movie in similar_movies]