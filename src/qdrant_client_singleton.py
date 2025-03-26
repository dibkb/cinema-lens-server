from qdrant_client import QdrantClient
from .config import settings
import logging

logger = logging.getLogger(__name__)

class QdrantClientSingleton:
    _instance = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            try:
                cls._instance = QdrantClient(
                    url=settings.QDRANT_URI,
                    api_key=settings.QDRANT_API_KEY
                )
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {e}")
                return None
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None 