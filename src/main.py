from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
from dotenv import load_dotenv
from .extractor import MovieExtractor
from .reddit import RedditPost
from .serp import search_google
from .search_query import build_reddit_search_query
from .qdrant import find_similar_by_plot
from .query import CypherQueryGenerator, MovieEntities
from .entity import EntityExtractorAgent
from .neo4j import process_result
from neo4j import AsyncGraphDatabase
from .config import settings
from typing import List, Optional
import logging
load_dotenv()
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cinema Lens API",
    description="API for Cinema Lens - A platform for cinema and photography enthusiasts",
    version="1.0.0"
)

# Initialize Neo4j driver with connection validation

async def init_neo4j():
    global neo4j
    try:
        if settings.NEO4J_URI and settings.NEO4J_USERNAME and settings.NEO4J_PASSWORD:
            logger.info(f"Initializing Neo4j connection to {settings.NEO4J_URI}")
            driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_lifetime=60  # Shorter connection lifetime to refresh connections more often
            )
            # Verify connection works
            async with driver.session() as session:
                await session.run("RETURN 1")
                logger.info("Neo4j connection verified")
            neo4j = driver
            return True
        else:
            logger.error("Missing Neo4j connection details in environment variables")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        neo4j = None
        return False

# Initialize at startup
@app.on_event("startup")
async def startup_event():
    await init_neo4j()

@app.on_event("shutdown")
async def shutdown_event():
    if neo4j:
        await neo4j.close()

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
            yield "data: Starting parallel processing...\n\n"
            await asyncio.sleep(0.01)  # Small delay to ensure immediate sending
            
            # Initialize entity extractor
            yield "data: Initializing entity extractor agent...\n\n"
            await asyncio.sleep(0.01)
            entity_extractor = EntityExtractorAgent()
            
            # Define async functions for each process
            
            async def process_entity_extraction():
                yield "data: Analyzing query for movie references and parameters...\n\n"
                entities = await entity_extractor.extract_entities(query)
                yield f"data: Entity extraction complete. Found entities: \n\n"
                yield f"data:xx--data--entities--{json.dumps(entities.model_dump())}\n\n"
                yield ("result", entities)
            
            async def process_movie_similarity(entities):
                if entities.movie:
                    yield "data: Movie reference detected in query...\n\n"
                    yield "data: Starting movie similarity search process...\n\n"
                    similar_movies = await find_similar_by_plot(entities, top_k=10)
                    yield f"data:xx--data--similar_movies--{json.dumps(similar_movies)}\n\n"
                    yield ("result", similar_movies)
                else:
                    yield "data: No specific movie reference found in query\n\n"
                    yield "data: Proceeding with general search parameters...\n\n"
                    yield ("result", None)
            
            async def process_reddit_search(entities):
                yield "data:Searching Reddit for movie recommendations...\n\n"
                reddit_search_query = build_reddit_search_query(entities)
                yield f"data:xx--data--reddit_search_query--{reddit_search_query}\n\n"
                
                # Run Google search in a separate thread to not block
                google_results = await asyncio.to_thread(search_google, reddit_search_query)
                reddit_links = [x['link'] for x in google_results if str(x['link']).startswith('https://www.reddit.com')]

                if len(reddit_links) == 0:
                    yield "data: No Reddit links found in Google search results\n\n"
                    yield ("result", None)
                    return
                
                yield f"data:xx--data--reddit_links--{reddit_links}\n\n"
                
                links = reddit_links[0:min(len(reddit_links), 3)]
                for link in links:
                    yield f"data:Searching in {link}...\n\n"
                    post = RedditPost(link)
                    await asyncio.to_thread(post.initialize)
                    movie_extractor = MovieExtractor()

                    comments = post.get_comments()
                    # Run movie extraction in a separate thread if it's CPU-intensive
                    movies = await asyncio.to_thread(movie_extractor.extract_movies, comments)
                
                    yield f"data:xx--data--reddit_results--{movies.movies}\n\n"
                    yield ("result", movies)
            
            async def process_cypher_query(entities):
                yield "data: Starting Cypher query generation...\n\n"
                yield "data: Initializing query generator...\n\n"
                
                query_generator = CypherQueryGenerator()
                # Run query generation in a thread if it's CPU-intensive
                cypher_query = await asyncio.to_thread(query_generator.generate_query_manually, entities)
                
                yield "data: Query generation complete\n\n"
                
                # Format the Cypher query to be SSE-friendly
                formatted_query = cypher_query.replace('\n', ' ').replace('\r', ' ')
                yield f"data: Generated Cypher query: {formatted_query}\n\n"
                
                # Neo4j query execution
                yield "data: Initiating connection to Neo4j database...\n\n"
                
                if not neo4j:
                    yield "data: Neo4j connection not available. Attempting to reconnect...\n\n"
                    connection_success = await init_neo4j()
                    if not connection_success:
                        yield "data: Could not establish connection to Neo4j database. Skipping database operations.\n\n"
                        yield ("result", [])
                        return
                
                try:
                    yield "data: Executing Cypher query...\n\n"
                    async with neo4j.session() as session:
                        yield "data: Database session established\n\n"
                        result = await session.run(cypher_query)
                        yield "data: Query executed, fetching results...\n\n"
                        records = await result.data()
                    
                    yield "data: Successfully retrieved results from database\n\n"
                    yield f"data:xx--data--related_movies--{json.dumps([x['title'] for x in records])}\n\n"
                    yield ("result", records)
                except Exception as e:
                    error_message = str(e)
                    yield f"data: Database error: {error_message}\n\n"
                    yield "data: Could not complete database operation. Continuing with other processes.\n\n"
                    yield ("result", [])
            
            # First, extract entities (we need this for other processes)
            entities_generator = process_entity_extraction()
            entities_result = None
            async for message in entities_generator:
                if isinstance(message, tuple) and message[0] == "result":
                    entities_result = message[1]
                else:
                    yield message
            
            if entities_result is None:
                yield "data: Failed to extract entities from query\n\n"
                return
                
            entities = entities_result
            
            # Create the generators but don't start them yet
            generators = [
                process_movie_similarity(entities),
                process_reddit_search(entities),
                process_cypher_query(entities)
            ]
            
            results = []
            for generator in generators:
                try:
                    process_result = None
                    async for message in generator:
                        if isinstance(message, tuple) and message[0] == "result":
                            process_result = message[1]
                        else:
                            yield message
                    
                    if process_result is not None:
                        results.append(process_result)
                except Exception as e:
                    yield f"data: Error in process: {str(e)}\n\n"
                
        except Exception as e:
            yield f"data: Error occurred: {str(e)}\n\n"
            yield "data: Process terminated due to error\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  
        }
    )

@app.get("/{id}")
async def get_movie(id: int):
    if not neo4j:
        if not await init_neo4j():
            return {"error": "Database connection not available"}

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

    try:
        async with neo4j.session() as session:
            result = await session.run(cypher_query, {"id": id})
            records = await result.data()

        if len(records) != 1:
            return {"message": "No movie found"}

        return process_result(records[0])
    except Exception as e:
        logger.error(f"Error retrieving movie with ID {id}: {e}")
        return {"error": f"Database error: {str(e)}"}

@app.post("/movies/batch-by-ids")
async def get_movies(ids: List[int]):
    if not neo4j:
        if not await init_neo4j():
            return {"error": "Database connection not available"}
            
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

    try:
        async with neo4j.session() as session:
            result = await session.run(cypher_query, {"ids": ids})
            records = await result.data()

        if not records:
            return {"message": "No movies found"}
        
        tasks = [asyncio.to_thread(process_result, record) for record in records]
        processed_results = await asyncio.gather(*tasks)
        return processed_results
    except Exception as e:
        logger.error(f"Error retrieving movies with IDs {ids}: {e}")
        return {"error": f"Database error: {str(e)}"}

@app.post("/movies/batch-by-title")
async def get_movies(title: List[str]):
    if not neo4j:
        if not await init_neo4j():
            return {"error": "Database connection not available"}
            
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

    try:
        async with neo4j.session() as session:
            result = await session.run(cypher_query, {"titles": title})
            records = await result.data()

        if not records:
            return {"message": "No movies found"}
        
        tasks = [asyncio.to_thread(process_result, record) for record in records]
        processed_results = await asyncio.gather(*tasks)
        return processed_results
    except Exception as e:
        logger.error(f"Error retrieving movies with titles {title}: {e}")
        return {"error": f"Database error: {str(e)}"}

# Query routes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
