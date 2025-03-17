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

class EntityExtractorAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=MovieEntities)
        self.genres = ['drama', 'war', 'crime', 'animation', 'comedy', 'romance', 'history', 'family', 'sci-fi', 'documentary', 'music', 'tv movie', 'children', 'imax', 'western', 'musical', 'film noir', 'action', 'fantasy', 'mystery', 'horror', 'thriller', 'adventure']
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Extract movie-related entities from the given query and return the response in JSON format.\n"
                "The genre should be selected from the following list: {genres}.\n\n"
                "Important formatting rules:\n"
                "- Always return 'actor' and 'genre' as arrays/lists, even for single values\n"
                "- For a single actor, use: \"actor\": [\"Tom Cruise\"]\n"
                "- For a single genre, use: \"genre\": [\"action\"]\n"
                "- For multiple values, use: \"actor\": [\"Tom Cruise\", \"Leonardo DiCaprio\"]\n\n"
                "Additionally, identify `actors_union` and `genres_union` based on the query:\n"
                "- If the user specifies multiple actors with 'and' (e.g., 'Suggest me movies with Tom Cruise and Leonardo DiCaprio'), set `actors_union` to `false`.\n"
                "- If the user specifies multiple genres with 'or' (e.g., 'Suggest me movies with drama or comedy'), set `genres_union` to `true`.\n"
                "- If the user lists genres without 'or' (e.g., 'crime, thriller movies'), set `genres_union` to `false`.\n\n"
                "{format_instructions}"
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