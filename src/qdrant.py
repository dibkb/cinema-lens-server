from qdrant_client import  models
import os
import asyncio
from typing import List
import numpy as np
from .entity import MovieEntities
from .qdrant_client_singleton import QdrantClientSingleton


async def get_movie_by_title(title: str):
        # Use asyncio.to_thread to make the synchronous Qdrant operation non-blocking
    client = await QdrantClientSingleton.get_instance()
    reference_movie = await asyncio.to_thread(
            client.scroll,
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




async def find_similar_by_embedding(embedding: List[float], top_k: int = 10) -> List[dict]:
    """
    Find similar movies by embedding
    """

        # Use asyncio.to_thread to make the synchronous operation non-blocking
    client = await QdrantClientSingleton.get_instance()
    results = await asyncio.to_thread(
            client.search,
            collection_name="movies_plot",
            query_vector=embedding,
            limit=top_k,
            with_payload=["title"],
            score_threshold=0.5
    )
    return [hit.payload["title"] for hit in results]

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

        # Use asyncio.to_thread to make the synchronous operation non-blocking
    client = await QdrantClientSingleton.get_instance()
    results = await asyncio.to_thread(
            client.search,
            collection_name="movies_plot",
            query_vector=query_vector,
            query_filter=exclude_filter,
            limit=top_k,
            with_payload=["title"]
    )
    return [hit.payload["title"] for hit in results]




import requests 
jina_api_key = os.getenv("JINA_API_KEY")
async def embed_text(text:str):
    url = 'https://api.jina.ai/v1/embeddings'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jina_api_key}'
    }
    data = {
        "model": "jina-embeddings-v3",
        "task": "retrieval.query",
        "input": [
            text
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    json = response.json()
    if "data" in json and len(json["data"]) > 0:
        return json["data"][0]["embedding"]
    else:
        return None


