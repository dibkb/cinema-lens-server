from typing import Dict, Optional, List
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
from .config import settings

class MovieEntities(BaseModel):
    movie: Optional[List[str]] = Field(None, description="Name of the movie")
    movies_present: Optional[bool] = Field(None, description="Whether the movie is present in the query")
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
                """### Entity Extraction Rules

        1. **Explicit Title Handling**
        - If query contains movie titles:
        → Populate ONLY `movie` field
        → Never infer genres/years/actors/directors
        → Correct spelling: "avengers endagme" → "Avengers: Endgame"

        2. **Person Entities (Actors/Directors)**
        - If actors/directors mentioned:
        → Populate ONLY relevant fields
        → Never suggest movies/infer genres
        → Correct formatting: "nolan" → "Christopher Nolan"

        3. **MANDATORY Movie Suggestions (No Titles/People)**
        - When no movie titles, actors, or directors are mentioned:
        → YOU MUST populate the `movie` field with 1-3 specific movie title suggestions (compulsory)
        → For example, for "parody movies":
            • `movie`: ["Airplane!", "Scary Movie", "Hot Shots!"]
        → Suggestions must be well-known, popular examples matching the query
        → NEVER leave `movie` field empty/null in this case
        -> When you infer movie titles, set movies_present=false
        -> when the movies are present in the query, set movies_present=true
        → Genres MUST come from: {genres}

        → Map themes→genres:
            • "Mind-bending" → ["thriller", "sci-fi"]
            • "Tearjerker" → ["drama"]
            • "Parody" → ["comedy"]
        → Set year ranges for eras:
            • "90s movies" → year_start:1990, year_end:1999
            • "Old/Classic/Vintage movies" → year_start:1920, year_end:1960
            • "Silent era" → year_start:1890, year_end:1929
            • "Golden Age Hollywood" → year_start:1930, year_end:1959
            • "Cold War era" → year_start:1947, year_end:1991
            • "Modern movies" → year_start:2000, year_end:null
            • "Contemporary" → year_start:2010, year_end:null

        4. **Search Query Generation**
        - Always populate `search_query`:
        → Optimize for web search by narrowing down only if too lengthy

        5. **Union Fields Handling**
        - For actors_union and genres_union:
        → Set actors_union=false if multiple actors should ALL be in the movie
        → Set actors_union=true if ANY of the actors should be in the movie
        → Set genres_union=false if movie must contain ALL specified genres
        → Set genres_union=true if movie should contain ANY of the specified genres
        -> set the genres_union=false or actors_union=false if its specified in the query
        Example:
        - "Movies with both action AND comedy" → genres_union=false
        - "Movies with either action OR comedy" → genres_union=true
        - "Movies with both Tom Hanks AND Tom Cruise" → actors_union=false
        - "Movies with either Tom Hanks OR Tom Cruise" → actors_union=true

        6. **Validation & Output**
        - Reject non-{genres} entries
        - parsing_review MUST explain:
        → Why titles/people were prioritized
        → Genre selection rationale
        → Movie suggestions rationale (when provided)
        → Spelling corrections made

        {format_instructions}

        **Available Genres**
        {genres}"""
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