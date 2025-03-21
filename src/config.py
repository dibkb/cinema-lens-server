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
    SERP_API_KEY: str = os.getenv("SERP_API_KEY")


    
    class Config:
        env_file = "../.env"

settings = Settings()