from typing import Dict, Optional, List
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
from .config import settings

class MovieEntities(BaseModel):
    movie: Optional[List[str]] = Field(None, description="Name of the movie")
    actor: Optional[List[str]] = Field(None, description="Name of the actors in the movie")
    director: Optional[List[str]] = Field(None, description="Name of the director of the movie")
    year_start: Optional[int] = Field(None, description="Start year")
    year_end: Optional[int] = Field(None, description="End year")
    genre: Optional[List[str]] = Field(None, description="Movie genres")

    actors_union: Optional[bool] = Field(None, description="Union of actors in the movie")
    genres_union: Optional[bool] = Field(None, description="Union of genres in the movie")

    search_query: Optional[str] = Field(None, description="Search query to be used for web search based on the users intent")

    parsing_review: Optional[str] = Field(None, description="Review of the parsing of the query")

class EntityExtractorAgent:
    def __init__(self):
        # self.llm = ChatOpenAI(model="gpt-4", temperature=0,api_key=settings.OPENAI_API_KEY)
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.GROQ_API_KEY)
        self.parser = PydanticOutputParser(pydantic_object=MovieEntities)
        self.genres = ['drama', 'war', 'crime', 'animation', 'comedy', 'romance', 'history', 'family', 'sci-fi', 'documentary', 'music', 'tv movie', 'children', 'imax', 'western', 'musical', 'film noir', 'action', 'fantasy', 'mystery', 'horror', 'thriller', 'adventure']
        
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """### Entity Extraction Guidelines

        1. **Explicit Movie Title Priority**
        - If the query explicitly mentions one or more movie titles, output only these titles.
        - Do not infer or extract additional details (e.g., genres, actors, director, start/end year) when a movie is provided.
        - Correct any spelling or formatting issues for explicit movie titles.

        2. **Genre Handling (Only When No Explicit Movie Title is Provided, or No Director or Actor is Provided)**
        - MUST select genres exclusively from the provided list: {genres}.
        - Map non-standard terms to their closest matches from the list:
            - "Revenge action" → ["action", "thriller"]
            - "Cyberpunk" → ["sci-fi", "action"]
            - "Feel-good" → ["comedy", "romance"]
        - For hybrid requests (e.g., "Action comedy"), combine genres: ["action", "comedy"]

        3. **Entity Priority (When No Explicit Movie Title is Provided)**
        - Prioritize extraction in the order: director > actor > genre.
        - Derive implied genres from themes or moods present in the query.

        4. **Movie Extraction and Suggestions**
        - **Movie Extraction:** If movie titles are explicitly mentioned, populate the "movie" field with those titles only.
        - **Movie Suggestions:** If no explicit movie title, director, or actor is mentioned, then suggest 1-3 movie titles based on inferred user intent, theme match, critical acclaim, or cult classic status.

        5. **Search Query Generation**
        - Always populate the search_query field, regardless of what other entities are extracted.
        - The search_query should summarize the user's intent for web searching in 3-4 words, optimized for web search.
        - When explicit entities are present (movie titles, actors, directors, genres), the search_query should capture those specific entities.
        - Examples:
            - "I want something that makes me cry" → search_query: "emotional tearjerker movies"
            - "Show me films about space exploration" → search_query: "space exploration films"
            - "I need a movie with plot twists" → search_query: "movies with twists"
            - "Movies by Christopher Nolan" → search_query: "christopher nolan films"
            - "The Godfather" → search_query: "the godfather movie"

        6. **Query Interpretation**
        - **Slang Handling:**
            - "Porn" → interpret as "visually intense" (apply as a genre if applicable).
            - "Mindf*ck" → map to ["thriller", "mystery"].
        - **Era Detection:**
            - "80s vibe" → set year_start:1980, year_end:1989.
            - "Modern classics" → set year_start:2010.

        7. **Validation Rules**
        - Reject any genres not included in the provided {genres} list.
        - Correct typos/terms:
            - "Spilberg" → "Steven Spielberg"
            - "Di Caprio" → "Leonardo DiCaprio"

        8. **Output Requirements**
        - Include a `parsing_review` that explains:
            - The rationale behind the selected genres from {genres} (if applicable).
            - The logic for handling movie titles—whether using the explicitly mentioned titles or generating suggestions.
            - Any corrections made to spelling or terms.
            - The reasoning behind the search_query selection (if applicable).
        - Format arrays consistently:
            - Single entry: ["action"]
            - Multiple entries: ["action", "comedy"]

        **Genre List Reference**
        {genres}

        {format_instructions}"""
            ),
            ("user", "{query}")
        ])


    async def extract_entities(self, query: str) -> MovieEntities:
        formatted_prompt = self.prompt.format(
            query=query,
            genres=self.genres,
            format_instructions=self.parser.get_format_instructions()
        )
        
        response = await self.llm.ainvoke(formatted_prompt)
        
        result = self.parser.parse(response.content)
        return result
from typing import Dict, Optional, List
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
from .config import settings

class MovieEntities(BaseModel):
    movie: Optional[List[str]] = Field(None, description="Name of the movie")
    actor: Optional[List[str]] = Field(None, description="Name of the actors in the movie")
    director: Optional[List[str]] = Field(None, description="Name of the director of the movie")
    year_start: Optional[int] = Field(None, description="Start year")
    year_end: Optional[int] = Field(None, description="End year")
    genre: Optional[List[str]] = Field(None, description="Movie genres")

    actors_union: Optional[bool] = Field(None, description="Union of actors in the movie")
    genres_union: Optional[bool] = Field(None, description="Union of genres in the movie")

    search_query: Optional[str] = Field(None, description="Search query to be used for web search based on the users intent")

    parsing_review: Optional[str] = Field(None, description="Review of the parsing of the query")

class EntityExtractorAgent:
    def __init__(self):
        # self.llm = ChatOpenAI(model="gpt-4", temperature=0,api_key=settings.OPENAI_API_KEY)
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.GROQ_API_KEY)
        self.parser = PydanticOutputParser(pydantic_object=MovieEntities)
        self.genres = ['drama', 'war', 'crime', 'animation', 'comedy', 'romance', 'history', 'family', 'sci-fi', 'documentary', 'music', 'tv movie', 'children', 'imax', 'western', 'musical', 'film noir', 'action', 'fantasy', 'mystery', 'horror', 'thriller', 'adventure']
        
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """### Entity Extraction Guidelines

        1. **Explicit Movie Title Priority**
        - If the query explicitly mentions one or more movie titles, output only these titles.
        - Do not infer or extract additional details (e.g., genres, actors, director, start/end year) when a movie is provided.
        - Correct any spelling or formatting issues for explicit movie titles.

        2. **Genre Handling (Only When No Explicit Movie Title is Provided, or No Director or Actor is Provided)**
        - MUST select genres exclusively from the provided list: {genres}.
        - Map non-standard terms to their closest matches from the list:
            - "Revenge action" → ["action", "thriller"]
            - "Cyberpunk" → ["sci-fi", "action"]
            - "Feel-good" → ["comedy", "romance"]
        - For hybrid requests (e.g., "Action comedy"), combine genres: ["action", "comedy"]

        3. **Entity Priority (When No Explicit Movie Title is Provided)**
        - Prioritize extraction in the order: director > actor > genre.
        - Derive implied genres from themes or moods present in the query.

        4. **Movie Extraction and Suggestions**
        - **Movie Extraction:** If movie titles are explicitly mentioned, populate the "movie" field with those titles only.
        - **Movie Suggestions:** If no explicit movie title, director, or actor is mentioned, then suggest 1-3 movie titles based on inferred user intent, theme match, critical acclaim, or cult classic status.

        5. **Search Query Generation**
        - Always populate the search_query field, regardless of what other entities are extracted.
        - The search_query should summarize the user's intent for web searching in 3-4 words, optimized for web search.
        - When explicit entities are present (movie titles, actors, directors, genres), the search_query should capture those specific entities.
        - Examples:
            - "I want something that makes me cry" → search_query: "emotional tearjerker movies"
            - "Show me films about space exploration" → search_query: "space exploration films"
            - "I need a movie with plot twists" → search_query: "movies with twists"
            - "Movies by Christopher Nolan" → search_query: "christopher nolan films"
            - "The Godfather" → search_query: "the godfather movie"

        6. **Query Interpretation**
        - **Slang Handling:**
            - "Porn" → interpret as "visually intense" (apply as a genre if applicable).
            - "Mindf*ck" → map to ["thriller", "mystery"].
        - **Era Detection:**
            - "80s vibe" → set year_start:1980, year_end:1989.
            - "Modern classics" → set year_start:2010.

        7. **Validation Rules**
        - Reject any genres not included in the provided {genres} list.
        - Correct typos/terms:
            - "Spilberg" → "Steven Spielberg"
            - "Di Caprio" → "Leonardo DiCaprio"

        8. **Output Requirements**
        - Always include a search_query that captures the user's intent, whether or not other entities were extracted.
        - Include a `parsing_review` that explains:
            - The rationale behind the selected genres from {genres} (if applicable).
            - The logic for handling movie titles—whether using the explicitly mentioned titles or generating suggestions.
            - Any corrections made to spelling or terms.
            - The reasoning behind the search_query selection.
        - Format arrays consistently:
            - Single entry: ["action"]
            - Multiple entries: ["action", "comedy"]

        **Genre List Reference**
        {genres}

        {format_instructions}"""
            ),
            ("user", "{query}")
        ])


    async def extract_entities(self, query: str) -> MovieEntities:
        formatted_prompt = self.prompt.format(
            query=query,
            genres=self.genres,
            format_instructions=self.parser.get_format_instructions()
        )
        
        response = await self.llm.ainvoke(formatted_prompt)
        
        result = self.parser.parse(response.content)
        return result