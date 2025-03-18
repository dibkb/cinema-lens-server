from typing import Dict, Optional, List
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
load_dotenv()

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
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=MovieEntities)
        self.genres = ['drama', 'war', 'crime', 'animation', 'comedy', 'romance', 'history', 'family', 'sci-fi', 'documentary', 'music', 'tv movie', 'children', 'imax', 'western', 'musical', 'film noir', 'action', 'fantasy', 'mystery', 'horror', 'thriller', 'adventure']
            
    #     self.prompt = ChatPromptTemplate.from_messages([
    #     (
    #         "system",
    #         "Extract movie-related entities from the given query and return the response in JSON format.\n"
    #         "The genre should be selected from the following list: {genres}.\n\n"
    #         "Important formatting rules:\n"
    #         "- Always return 'actor' and 'genre' as arrays/lists, even for single values.\n"
    #         "- For a single actor, use: \"actor\": [\"Tom Cruise\"]\n"
    #         "- For a single genre, use: \"genre\": [\"action\"]\n"
    #         "- For multiple values, use: \"actor\": [\"Tom Cruise\", \"Leonardo DiCaprio\"]\n\n"
    #         "Intent Inference:\n"
    #         "- If the query implies a request for similar or related movies, populate a 'related_movies' field with movie suggestions inferred from the user's intent.\n"
    #         "- If the query does not explicitly provide a genre or related movies, infer them based on the context of the user's intent.\n"
    #         "- If the movie title is abbreviated or incomplete, output the full movie title using your knowledge base.\n"
    #         "- **Special Case:** If the query includes terms like 'dark comedy movies', do not stop at extracting 'comedy' as the genre. Instead, also infer similar movies (e.g., other films with dark humor or similar style) and include them in the 'related_movies' field to make the search more efficient.\n\n"
    #         "Additionally, identify `actors_union` and `genres_union` based on the query:\n"
    #         "- If the user specifies multiple actors with 'and' (e.g., 'Suggest me movies with Tom Cruise and Leonardo DiCaprio'), set `actors_union` to `false`.\n"
    #         "- If the user specifies multiple genres with 'or' (e.g., 'Suggest me movies with drama or comedy'), set `genres_union` to `true`.\n"
    #         "- If the user lists genres without 'or' (e.g., 'crime, thriller movies'), set `genres_union` to `false`.\n\n"
    #         "Year range inference rules:\n"
    #         "- When specific years are mentioned (e.g., '2010 to 2020', 'between 1990 and 2000'), use those as year_start and year_end.\n"
    #         "- For decades (e.g., '90s movies', '1980s films'), set year_start to the beginning of the decade (e.g., 1990, 1980) and year_end to the end (e.g., 1999, 1989).\n"
    #         "- For specific periods: 'recent movies' should be last 3 years, 'new movies' should be last 2 years, 'old movies' should be pre-1980s.\n"
    #         "- For eras: 'classic Hollywood' typically means 1930-1960, 'golden age' means 1930-1945, 'modern films' means 2000-present.\n"
    #         "- For mentions like 'early 2000s', set year_start to 2000 and year_end to 2005.\n"
    #         "- For 'movies from the last decade', calculate based on the current year (approximately 10 years back).\n"
    #         "- For single year mentions (e.g., 'movies from 1995'), set both year_start and year_end to that year.\n"
    #         "- For contextual references (e.g., 'Cold War movies', 'Vietnam era films'), infer appropriate year ranges.\n\n"
    #         "Additional requirement:\n"
    #         "- Correct any typos in popular actor, movie, or director names and output the full correct name. For example, if the query contains 'Spilberg', it should be corrected to 'Steven Spielberg'.\n\n"
    #         "{format_instructions}"
    #     ),
    #     ("user", "{query}")
    # ])

        self.prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Extract and infer movie-related entities from the user query following these rules:\n"
            "1. Genre Selection & Theme Inference:\n"
            "- Primary genres must come from: {genres}\n"
            "- For non-standard terms (e.g., 'revenge porn', 'cyberpunk'), infer underlying themes and map to 2-3 relevant genres\n"
            "- When themes suggest hybrid genres (e.g., 'action comedy'), include all relevant genres\n\n"
            "2. Mandatory Field Population:\n"
            "- ALWAYS populate at least one of: movie, actor, director, genre, or related_movies\n"
            "- Prioritize movie suggestions when query is thematic (e.g., 'dark tech movies' → suggest 'Black Mirror', 'Ex Machina')\n\n"
            "3. Query Interpretation:\n"
            "- Treat slang/idioms as thematic descriptors (e.g., 'porn' → 'visually intense', 'excessive')\n"
            "- For single-word queries (e.g., 'cyberpunk'), suggest the most iconic movies in that category\n"
            "- For mood-based queries (e.g., 'feel-good'), infer 2-3 matching genres and suggest movies\n\n"
            "4. Movie Suggestion Rules:\n"
            "- Suggest 3-5 movies for vague queries using this priority:\n"
            "  1. Genre matches\n"
            "  2. Theme matches\n"
            "  3. Director/style matches\n"
            "  4. Actor matches\n"
            "  5. Movies should be in the order of matching the query, popularity\n"
            "- Include cult classics when appropriate (e.g., 'mind-bending' → 'Inception', 'Memento')\n\n"
            "5. Error Correction & Inference:\n"
            "- Fix typos using movie knowledge (e.g., 'Nolan movees' → Christopher Nolan films)\n"
            "- For actor/director-style requests (e.g., 'Hitchcockian'), suggest 2-3 characteristic movies\n\n"
            "6. Special Cases Handling:\n"
            "- For potentially sensitive terms (e.g., 'porn'), focus on cinematic interpretation\n"
            "- For era-based styles (e.g., '80s vibe'), suggest movies from AND inspired by that period\n\n"
            "7. Output Requirements:\n"
            "- In parsing_review, explain:\n"
            "  - How vague terms were interpreted\n"
            "  - Why specific movies were suggested\n"
            "  - Any field population rationales\n"
            "- If no direct matches, state inferred connections in parsing_review\n\n"
            "Formatting Rules:\n{format_instructions}\n"
            "Genre List: {genres}"
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