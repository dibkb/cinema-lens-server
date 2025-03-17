from contextlib import contextmanager
from qdrant_client import QdrantClient,models
import os

@contextmanager
def get_qdrant_client():
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URI"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    yield qdrant_client
    qdrant_client.close()


def get_movie_by_title(title: str):
    with get_qdrant_client() as qdrant_client:
        reference_movie = qdrant_client.scroll(
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
                )[0]
    return reference_movie


def get_movie_by_reference(reference_movie:dict):
    with get_qdrant_client() as qdrant_client:
        reference_embedding = reference_movie[0].vector
        similar_movies = qdrant_client.search(
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