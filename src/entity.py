from typing import Dict, Optional, List
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from .config import settings

class MovieEntities(BaseModel):
    movie: Optional[List[str]] = Field(None, description="Name of the movie")
    movies_present: Optional[bool] = Field(None, description="Whether the movie is present in the query")
    actor: Optional[List[str]] = Field(None, description="List of the actors in the movie")
    director: Optional[List[str]] = Field(None, description="List of the directors of the movie")
    year_start: Optional[int] = Field(None, description="Start year")
    year_end: Optional[int] = Field(None, description="End year")
    genre: Optional[List[str]] = Field(None, description="Movie genres")

    actors_union: Optional[bool] = Field(None, description="Union of actors in the movie")
    genres_union: Optional[bool] = Field(None, description="Union of genres in the movie")

    search_query: Optional[str] = Field(None, description="Search query to be used for web search based on the users intent")

    parsing_review: Optional[str] = Field(None, description="Review of the parsing of the query")

class EntityExtractorAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7,api_key=settings.OPENAI_API_KEY)
        # self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=.7,api_key=settings.GEMINI_API_KEY)
        # self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0,api_key=settings.GEMINI_API_KEY)
        # self.llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0, api_key=settings.GROQ_API_KEY)
        # self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.GROQ_API_KEY)
        self.parser = PydanticOutputParser(pydantic_object=MovieEntities)
        self.genres = ['drama', 'war', 'crime', 'animation', 'comedy', 'romance', 'history', 'family', 'sci-fi', 'documentary', 'music', 'tv movie', 'children', 'imax', 'western', 'musical', 'film-noir', 'action', 'fantasy', 'mystery', 'horror', 'thriller', 'adventure']
        
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """### Entity Extraction & Movie Suggestion Rules
        - If genres and year are provided, populate them only, dont generate anything
        1. **Movie Titles**
        - If query includes movie titles:
            - Populate ONLY the `movie` field.
            - Correct any spelling errors.
            - Set `movies_present=true`.

        2. **Person Entities (Actors/Directors)**
        - If actors or directors are mentioned:
            - Populate only the corresponding fields.
            - Always complete/correct partial names:
                - "spielberg" → "Steven Spielberg"
                - "kubrick" → "Stanley Kubrick"
                - "nolan" → "Christopher Nolan"
                - "leo" → "Leonardo DiCaprio"
            - Do not suggest movies or infer genres.
            - Set appropriate field (actor/director) based on the person's primary role.
            - Handle possessive forms ("Spielberg's movies", "Kubrick's films").

        3. **Mandatory Movie Suggestions (No Titles/People)**
        - If the query lacks movie titles, actors, or directors:
            - Populate `movie` with 1-3 specific, well-known suggestions matching the query (e.g., "parody movies": ["Airplane!", "Scary Movie", "Hot Shots!"]).
            - NEVER leave the `movie` field empty.
            - Set `movies_present=false`.
        - If the query explicitly mentions a movie:
            - Just populate the `movie` field with the movie names.
            - Set `movies_present=true`.

        4. **Genre & Theme Mapping**
        - Allowed genres come from: {genres}.
        - Map themes to genres:
            - "Mind-bending" → ["thriller", "sci-fi"]
            - "Tearjerker" → ["drama"]
            - "Parody" → ["comedy"]
        - Set era year ranges:
            - "90s movies" → year_start: 1990, year_end: 1999
            - "Old/Classic/Vintage movies" → year_start: 1920, year_end: 1960
            - "Silent era" → year_start: 1890, year_end: 1929
            - "Golden Age Hollywood" → year_start: 1930, year_end: 1959
            - "Cold War era" → year_start: 1947, year_end: 1991
            - "Modern movies" → year_start: 2000, year_end: null
            - "Contemporary" → year_start: 2010, year_end: null

        5. **Search Query Generation**
        - Always populate `search_query`.
        - Only shorten if too lengthy. otherwise keep it as is.

        6. **Union Fields Handling**
        - For `actors_union`:
            - Set to false if all specified actors must be in the movie. (false if strictly specified in the query)
            - Set to true if any one is sufficient.
        - For `genres_union`:
            - Set to false if the movie must include all specified genres. (false if strictly specified in the query)
            - Set to true if the movie can include any of them.
        - If specified in the query (e.g., "both" vs "either"), enforce accordingly.

        7. **Validation & Output**
        - Reject any entries not in {genres}.
        - `parsing_review` must explain:
            - Why titles or people were prioritized.
            - Rationale for genre selection.
            - Justification for movie suggestions (if provided).
            - Any spelling corrections made.

        **Formatting Instructions:**  
        {format_instructions}

        **Available Genres:**  
        {genres}"""
            ),
            ("user", "{query} {min_year} {max_year} {user_genres}")
        ])



    async def extract_entities(self, query: str, min_year: Optional[str] = None, max_year: Optional[str] = None, genres: Optional[str] = None) -> MovieEntities:

        formatted_prompt = self.prompt.format(
            query=query,
            min_year=min_year if min_year != "Infinity" else None,
            max_year=max_year if max_year != "-Infinity" else None,
            user_genres=genres,
            genres=self.genres,
            format_instructions=self.parser.get_format_instructions()
        )
        
        response = await self.llm.ainvoke(formatted_prompt)
        
        result = self.parser.parse(response.content)
        return result