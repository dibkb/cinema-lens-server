from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from .config import settings
from langchain_groq import ChatGroq

class MovieList(BaseModel):
    movies: list[str]

class MovieExtractor():
    def __init__(self):
        # self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.OPENAI_API_KEY)
        self.llm = ChatGroq(model="llama3-8b-8192", temperature=0, api_key=settings.GROQ_API_KEY)
        self.parser = PydanticOutputParser(pydantic_object=MovieList)
        self.prompt = PromptTemplate(
            template="""
            You are a helpful assistant that extracts movies from a given list of comments.
            Here is the list of comments:
            {comments}

            For each comment, extract the movies mentioned if the comment is about movies.
            
            Important instructions:
            1. Correct any typos in movie titles based on your knowledge (e.g., "The Matrics" should be "The Matrix")
            2. Complete partial movie names with their full titles (e.g., "TDK" should become "The Dark Knight")
            3. Use the official movie title rather than abbreviations or nicknames
            4. If a movie has a year mentioned, include it in parentheses after the title
            5. If you're unsure about a movie reference, include it anyway with your best correction
            6. Return only the titles, excluding year if present
            
            For example: 

            ['Heat', 'It's the same film! Absolutely love both', 'Have you seen The Dark Knight?', 'For real. Op is describing TDKR but it sounds more like he's looking for TDK lol', 'Gladiator, sort of', 'Apocalypto (2006)', 'The Batman', 'Looper (2012)', 'I'm just delighted you like The Dark Knight Rises so much. It's far and away my favorite of the trilogy and one of my favorite superhero movies ever.']

            Should return:
            ['Heat', 'The Dark Knight', 'The Dark Knight Rises', 'Gladiator', 'Apocalypto', 'The Batman', 'Looper']

            Here is the format you should use to extract the movies:
            {format_instructions}
            """,
            input_variables=["comments"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

    def extract_movies(self, comments: list[str]) -> list[str]:
        response = self.llm.invoke(self.prompt.format(comments=comments))
        return self.parser.parse(response.content)
