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

        **1. Genre Handling**
        - MUST select genres exclusively from the provided list: {genres}
        - Map non-standard terms to their closest matches from the list:
        - "Revenge action" → ["action", "thriller"]
        - "Cyberpunk" → ["sci-fi", "action"]
        - "Feel-good" → ["comedy", "romance"]
        - For hybrid requests (e.g., "Action comedy"), combine genres: ["action", "comedy"]

        **2. Entity Priority**
        1. **Explicit Entities:** Prioritize in the order: director > actor > genre.
        2. **Implied Genres:** Derive genres from themes or moods present in the query.
        3. **Movie Extraction and Suggestions:**
        - **Movie Extraction:** If movie titles are explicitly mentioned in the query, populate the "movie" field with those titles (after verifying spelling and correcting types as needed). Do not generate additional suggestions.
        - **Movie Suggestions:** Only if no movie titles, director, or actor are mentioned should the system infer and suggest 1-3 movie titles based on the user's intent, theme match, critical acclaim, or cult classic status.

        **3. Query Interpretation**
        - **Slang Handling:**
        - "Porn" → interpret as "visually intense" (populate as a genre if applicable).
        - "Mindf*ck" → map to ["thriller", "mystery"].
        - **Era Detection:**
        - "80s vibe" → set year_start:1980, year_end:1989.
        - "Modern classics" → set year_start:2010.

        **4. Validation Rules**
        - Reject any genres not included in the provided {genres} list.
        - Correct typos/terms:
        - "Spilberg" → "Steven Spielberg"
        - "Di Caprio" → "Leonardo DiCaprio"

        **5. Movie Handling Rules**
        - **Explicit Movie Titles:** If movie titles are present in the query, use only these (after correcting any spelling or formatting issues).
        - **Movie Suggestions:** If no explicit movie titles, and no director or actor is mentioned, then suggest 1-3 movie titles based on the inferred user intent.
        - Do not combine explicit movie extraction with additional movie suggestions.

        **6. Output Requirements**
        - Include a `parsing_review` that explains:
        - The rationale behind the selected genres from {genres}.
        - The logic for handling movie titles—whether using the explicitly mentioned titles or generating suggestions.
        - Any corrections made to spelling or terms.
        - Format arrays consistently:
        - Single entry: ["action"]
        - Multiple entries: ["action", "comedy"]

        {format_instructions}

        **Genre List Reference**
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