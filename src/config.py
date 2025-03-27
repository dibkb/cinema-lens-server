from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
load_dotenv()

class Settings(BaseSettings):
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    NEO4J_URI: str = os.getenv("NEO4J_URI")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY")
    QDRANT_URI: str = os.getenv("QDRANT_URI")
    SERP_API_KEY: str = os.getenv("SERP_API_KEY")
    BRAVE_SEARCH_API_KEY: str = os.getenv("BRAVE_SEARCH_API_KEY")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_SECRET: str = os.getenv("REDDIT_SECRET")


    
    class Config:
        env_file = "../.env"

settings = Settings()