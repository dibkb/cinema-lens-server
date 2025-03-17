from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
from dotenv import load_dotenv
from .qdrant import get_movie_by_title, get_movie_by_reference
from .query import CypherQueryGenerator, MovieEntities
from .entity import EntityExtractorAgent
from .neo4j import process_result
from neo4j import AsyncGraphDatabase
import os
load_dotenv()

app = FastAPI(
    title="Cinema Lens API",
    description="API for Cinema Lens - A platform for cinema and photography enthusiasts",
    version="1.0.0"
)
neo4j = AsyncGraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")))



# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Cinema Lens API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/stream-response")
async def stream_response(query: str):
    async def event_generator():
        try:
            # Stream entity extraction process
            yield "data: Starting entity extraction process...\n\n"
            yield "data: Initializing entity extractor agent...\n\n"
            entity_extractor = EntityExtractorAgent()
            # entities = await entity_extractor.extract_entities(query)
            yield "data: Analyzing query for movie references and parameters...\n\n"
            entities = MovieEntities(movie=["Law Abiding Citizen"],genres_union=False)
            yield f"data: Entity extraction complete. Found entities: {entities}\n\n"

            if entities.movie:
                yield "data: Movie reference detected in query...\n\n"
                yield "data: Starting movie similarity search process...\n\n"
                normalized_title = " ".join([x.capitalize() for x in entities.movie[0].strip().split(" ")])
                
                # Stream movie search process
                yield f"data: Normalizing movie title to: {normalized_title}\n\n"
                yield f"data: Searching database for movie: {normalized_title}\n\n"
                reference_movie = get_movie_by_title(normalized_title)

                if len(reference_movie) > 0:
                    yield "data: Successfully found reference movie in database\n\n"
                    yield "data: Initiating similarity search based on plot and features...\n\n"
                    similar_movies = get_movie_by_reference(reference_movie)
                    yield f"data: Similarity search complete. Found {len(similar_movies)} similar movies\n\n"
                    yield "data: Processing similarity results...\n\n"
                else:
                    yield f"data: Warning: Could not find movie '{normalized_title}' in database\n\n"
                    similar_movies = None
            else:
                yield "data: No specific movie reference found in query\n\n"
                yield "data: Proceeding with general search parameters...\n\n"
                similar_movies = None

            # Stream Cypher query generation
            yield "data: Starting Cypher query generation...\n\n"
            yield "data: Initializing query generator...\n\n"
            query_generator = CypherQueryGenerator()
            cypher_query = query_generator.generate_query_manually(entities)
            yield "data: Query generation complete\n\n"
            
            # Format the Cypher query to be SSE-friendly
            formatted_query = cypher_query.replace('\n', ' ').replace('\r', ' ')
            yield f"data: Generated Cypher query: {formatted_query}\n\n"


            # Stream Cypher query execution
            yield "data: Initiating connection to Neo4j database...\n\n"
            yield "data: Executing Cypher query...\n\n"
            async with neo4j.session() as session:
                yield "data: Database session established\n\n"
                result = await session.run(cypher_query)
                yield "data: Query executed, fetching results...\n\n"
                records = await result.data()
            yield "data: Successfully retrieved results from database\n\n"
            
            # Send final results
            yield "data: Preparing final response...\n\n"
            final_result = {
                "entities": entities,
                "result": records,
                "similar_movies_by_plot": similar_movies
            }
            yield "data: Final results compiled\n\n"
            yield f"data: {str(final_result)}\n\n"
            
        except Exception as e:
            yield f"data: Error occurred: {str(e)}\n\n"
            yield "data: Process terminated due to error\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@app.get("/{id}")
async def get_movie(id: int):
    cypher_query = """
        MATCH (target {id: $id})
        OPTIONAL MATCH (target)-[r]-(connected)
        RETURN 
            target { .* } AS target,
            COLLECT({
                relationship: TYPE(r),
                direction: CASE WHEN startNode(r) = target THEN 'OUTGOING' ELSE 'INCOMING' END,
                connected: connected { .* }
            }) AS connections
    """

    async with neo4j.session() as session:
        result = await session.run(cypher_query, {"id": id})
        records = await result.data()

    if len(records) != 1:
        return {"message": "No movie found"}

    return process_result(records[0])

@app.post("/movies/batch")
async def get_movies(ids: list[int]):
    cypher_query = """
        UNWIND $ids as id
        MATCH (target {id: id})
        OPTIONAL MATCH (target)-[r]-(connected)
        RETURN 
            target { .* } AS target,
            COLLECT({
                relationship: TYPE(r),
                direction: CASE WHEN startNode(r) = target THEN 'OUTGOING' ELSE 'INCOMING' END,
                connected: connected { .* }
            }) AS connections
    """

    async with neo4j.session() as session:
        result = await session.run(cypher_query, {"ids": ids})
        records = await result.data()

    if not records:
        return {"message": "No movies found"}
    

    tasks = [asyncio.to_thread(process_result, record) for record in records]
    processed_results = await asyncio.gather(*tasks)
    return processed_results

# Query routes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
