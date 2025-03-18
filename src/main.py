from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
from dotenv import load_dotenv
from .qdrant import find_similar_by_plot
from .query import CypherQueryGenerator, MovieEntities
from .entity import EntityExtractorAgent
from .neo4j import process_result
from neo4j import AsyncGraphDatabase
import os
from typing import List
load_dotenv()
import json
app = FastAPI(
    title="Cinema Lens API",
    description="API for Cinema Lens - A platform for cinema and photography enthusiasts",
    version="1.0.0"
)
neo4j = AsyncGraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")))



# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # In production, replace with specific origins
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
            # Add a small delay between events to ensure they're sent immediately
            # Stream entity extraction process
            yield "data: Starting entity extraction process...\n\n"
            await asyncio.sleep(0.01)  # Small delay to ensure immediate sending
            
            yield "data: Initializing entity extractor agent...\n\n"
            await asyncio.sleep(0.01)
            
            entity_extractor = EntityExtractorAgent()
            # In a real scenario, you would use the actual entity extraction
            # entities = await entity_extractor.extract_entities(query)


            movie=['The Dark Knight','Batman Begins']
            # movie=['Looper','Interstellar']
            genre=['sci-fi', 'adventure', 'action']
            entities = MovieEntities(movie=movie)

            yield "data: Analyzing query for movie references and parameters...\n\n"
            await asyncio.sleep(0.01)
            
            # For demonstration, using hardcoded entities
            yield f"data: Entity extraction complete. Found entities: {entities}\n\n"
            await asyncio.sleep(0.01)

            if entities.movie:
                yield "data: Movie reference detected in query...\n\n"
                await asyncio.sleep(0.01)
                
                yield "data: Starting movie similarity search process...\n\n"
                await asyncio.sleep(0.01)

                similar_movies = await find_similar_by_plot(
                    entities.movie,
                    top_k=10
                )
                yield f"data:xx--data--similar_movies--{json.dumps(similar_movies)}\n\n"
                await asyncio.sleep(0.01)

            else:
                yield "data: No specific movie reference found in query\n\n"
                await asyncio.sleep(0.01)
                
                yield "data: Proceeding with general search parameters...\n\n"
                await asyncio.sleep(0.01)
                
                similar_movies = None

            # Stream Cypher query generation
            yield "data: Starting Cypher query generation...\n\n"
            await asyncio.sleep(0.01)
            
            yield "data: Initializing query generator...\n\n"
            await asyncio.sleep(0.01)
            
            query_generator = CypherQueryGenerator()
            cypher_query = query_generator.generate_query_manually(entities)
            yield "data: Query generation complete\n\n"
            await asyncio.sleep(0.01)
            
            # Format the Cypher query to be SSE-friendly
            formatted_query = cypher_query.replace('\n', ' ').replace('\r', ' ')
            yield f"data: Generated Cypher query: {formatted_query}\n\n"
            await asyncio.sleep(0.01)

            # Stream Cypher query execution
            yield "data: Initiating connection to Neo4j database...\n\n"
            await asyncio.sleep(0.01)
            
            yield "data: Executing Cypher query...\n\n"
            await asyncio.sleep(0.01)
            
            async with neo4j.session() as session:
                yield "data: Database session established\n\n"
                await asyncio.sleep(0.01)
                
                result = await session.run(cypher_query)
                yield "data: Query executed, fetching results...\n\n"
                await asyncio.sleep(0.01)
                
                records = await result.data()
            yield "data: Successfully retrieved results from database\n\n"
            await asyncio.sleep(0.01)
            yield f"data:xx--data--related_movies--{json.dumps([x['title'] for x in records])}\n\n"
    
            
            
        except Exception as e:
            yield f"data: Error occurred: {str(e)}\n\n"
            yield "data: Process terminated due to error\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering if you're using Nginx
        }
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

@app.post("/movies/batch-by-ids")
async def get_movies(ids: List[int]):
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

@app.post("/movies/batch-by-title")
async def get_movies(title: List[str]):
    cypher_query = """
        UNWIND $titles as title
        MATCH (target {title: title})
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
        result = await session.run(cypher_query, {"titles": title})
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
