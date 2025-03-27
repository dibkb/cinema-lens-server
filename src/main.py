from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
from dotenv import load_dotenv
from .brave import search_brave
from .letterboxd import Letterboxd
from .extractor import MovieExtractor
from .reddit import RedditPost, RedditResult
from .search_query import build_letterboxd_search_query, build_reddit_search_query
from .qdrant import embed_text, find_similar_by_embedding, find_similar_by_plot
from .query import CypherQueryGenerator, MovieEntities
from .entity import EntityExtractorAgent
from .neo4j import process_result
from neo4j import AsyncGraphDatabase
from .config import settings
from typing import List, Optional
import logging
load_dotenv()
import json
from .qdrant_client_singleton import QdrantClientSingleton
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cinema Lens API",
    description="API for Cinema Lens - A platform for cinema and photography enthusiasts",
    version="1.0.0"
)

async def get_qdrant_client():
    return await QdrantClientSingleton.get_instance()
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
    await get_qdrant_client()
@app.on_event("shutdown")
async def shutdown_event():
    if neo4j:
        await neo4j.close()
    await QdrantClientSingleton.close()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://cinema.borborah.xyz"],  # In production, replace with specific origins
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



@app.get("/stream-response-summary")
async def stream_response_summary(
    query: str,
):
    async def event_generator():
        yield "data: Recieved query...\n\n"
        yield f"data:{query}\n\n"
        yield "data: Getting embedding of the query\n\n"
        
        # Create and execute the embedding task
        embedding_task = asyncio.create_task(embed_text(query))
        
        try:
            embedding = await embedding_task
            yield "data: Found embedding of the query\n\n"
            yield f"data: Searching for top 10 similar movies based on embedding\n\n"
            similar_movies = await find_similar_by_embedding(embedding,5)
            yield f"data:xx--data--similar_movies--{json.dumps(similar_movies)}\n\n"
        except Exception as e:
            yield f"data: Error getting embedding: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  
        }
    )
    
@app.get("/stream-response")
async def stream_response(
    query: str,
    min_year: Optional[str] = None,  # single year
    max_year: Optional[str] = None,
    genres: Optional[str] = None,
    reddit: Optional[bool] = None,
    letterboxd: Optional[bool] = None
):
    async def event_generator():
        try:
            # Add a small delay between events to ensure they're sent immediately
            yield "data: Starting parallel processing...\n\n"
            yield f"data: received query: {query}\n\n"
            yield f"data: received min_year: {min_year}\n\n"
            yield f"data: received max_year: {max_year}\n\n"
            yield f"data: received genres: {genres}\n\n"
            yield f"data: received reddit: {reddit}\n\n"
            yield f"data: received letterboxd: {letterboxd}\n\n"


            
            # Initialize entity extractor
            yield "data: Initializing entity extractor agent...\n\n"
            
            entity_extractor = EntityExtractorAgent()
            
            # Define async functions for each process
            
            async def process_entity_extraction():
                yield "data: Analyzing query for movie references and parameters...\n\n"
                entities = await entity_extractor.extract_entities(query,min_year,max_year,genres)
                yield f"data: Entity extraction complete. Found entities: {entities}\n\n"
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

            async def process_letterboxd_search(entities):
                yield "data:Searching Letterboxd for movie recommendations...\n\n"
                letterboxd_search_query = build_letterboxd_search_query(entities)

                yield f"data:xx--data--letterboxd_search_query--{letterboxd_search_query}\n\n"
                letterboxd_results = await asyncio.to_thread(search_brave, letterboxd_search_query)


                letterboxd_links = [x['url'] for x in letterboxd_results if x is not None and str(x['url']).startswith('https://letterboxd.com')]

                if len(letterboxd_links) == 0:
                    yield "data: No Letterboxd links found in Google search results\n\n"
                    yield ("result", None)
                    return
                
                links = letterboxd_links[0:min(len(letterboxd_links), 3)]

                letterboxd_results:List[RedditResult] = []
                letterboxd_tasks = []
                for link in links:
                    yield f"data:Searching in {link}...\n\n"
                    async def process_single_letterboxd_link(link_url):
                        letterboxd = Letterboxd(link_url)
                        movies = letterboxd.get_movies()
                        if (len(movies) > 0):
                            return RedditResult(movies=movies[0:min(len(movies), 10)], site_url=link_url)

                    letterboxd_tasks.append(process_single_letterboxd_link(link))

                if letterboxd_tasks:
                    for task in asyncio.as_completed(letterboxd_tasks):
                        result_data = await task
                        letterboxd_results.append(result_data)

                yield f"data:xx--data--letterboxd_results--{json.dumps([x.model_dump() for x in letterboxd_results if x is not None])}\n\n"

            
            async def process_reddit_search(entities):
                yield "data:Searching Reddit for movie recommendations...\n\n"
                reddit_search_query = build_reddit_search_query(entities)
                yield f"data:xx--data--reddit_search_query--{reddit_search_query}\n\n"
                
                # Run Google search in a separate thread to not block
                google_results = await asyncio.to_thread(search_brave, reddit_search_query)

                reddit_links = [x['url'] for x in google_results if x is not None and str(x['url']).startswith('https://www.reddit.com')]

                if len(reddit_links) == 0:
                    yield "data: No Reddit links found in Google search results\n\n"
                    yield ("result", None)
                    return
                
                links = reddit_links[0:min(len(reddit_links), 3)]
                reddit_results:List[RedditResult] = []
                
                # Create tasks for processing each Reddit link in parallel
                reddit_tasks = []
                for link in links:
                    yield f"data:Searching in {link}...\n\n"
                    
                    # Define as a regular async function, not an async generator
                    async def process_single_reddit_link(link_url):
                        post = RedditPost(link_url)
                        comments = post.get_comments()
                        movie_extractor = MovieExtractor()
                        movies = await asyncio.to_thread(movie_extractor.extract_movies, comments)
                        return RedditResult(movies=movies.movies, site_url=link_url)
                    
                    reddit_tasks.append(process_single_reddit_link(link))
                
                # Process all Reddit links concurrently
                if reddit_tasks:
                    for task in asyncio.as_completed(reddit_tasks):
                        result_data = await task
                        reddit_results.append(result_data)

                yield f"data:xx--data--reddit_results--{json.dumps([x.model_dump() for x in reddit_results if x is not None])}\n\n"
            
            async def process_cypher_query(entities:MovieEntities):
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
                    llm_suggested = [x.lower() for x in entities.movie if x is not None] if entities.movies_present ==False and entities.movie is not None else []
                    yield f"data:xx--data--related_movies--{json.dumps(llm_suggested + [x['title'].lower() for x in records if x is not None])}\n\n"
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
            
            # Helper function to drain a generator and capture its yield values
            async def self_drain_generator(generator):
                messages = []
                result = None
                async for message in generator:
                    if isinstance(message, tuple) and message[0] == "result":
                        result = message[1]
                    else:
                        messages.append(message)
                return messages, result
            
            # Create the generators but don't start them yet
            similarity_generator = process_movie_similarity(entities)
            reddit_generator = process_reddit_search(entities)
            cypher_generator = process_cypher_query(entities)
            letterboxd_generator = process_letterboxd_search(entities)
            # Run all generators concurrently
            tasks = [
                asyncio.create_task(self_drain_generator(similarity_generator)),
                asyncio.create_task(self_drain_generator(cypher_generator)),
            ]
            if reddit:
                tasks.append(asyncio.create_task(self_drain_generator(reddit_generator)))
            if letterboxd:
                tasks.append(asyncio.create_task(self_drain_generator(letterboxd_generator)))
            results = []
            # Wait for all tasks to complete and yield their messages in the order they complete
            for completed_task in asyncio.as_completed(tasks):
                messages, result = await completed_task
                for message in messages:
                    yield message
                if result is not None:
                    results.append(result)
                
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
            
    # Modified query to use exact matches only
    cypher_query = """
        UNWIND $titles as search_title
        MATCH (target)
        WHERE target.title = search_title
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
            return []
        
        processed_results = []
        failed_titles = []
        
        async def process_record_safely(record):
            try:
                return await asyncio.to_thread(process_result, record)
            except Exception as e:
                logger.error(f"Failed to process record: {e}")
                if 'target' in record and 'title' in record['target']:
                    failed_titles.append(record['target']['title'])
                return None
        
        tasks = [process_record_safely(record) for record in records]
        results = await asyncio.gather(*tasks)
        
        # Filter out None values (failed processing)
        processed_results = [r for r in results if r is not None]
        
            
        return processed_results
        
    except Exception as e:
        logger.error(f"Error retrieving movies with titles {title}: {e}")
        return {"error": f"Database error: {str(e)}"}

# Query routes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
