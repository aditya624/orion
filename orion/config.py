from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class GroqConfig(BaseModel):
    api_key: str = os.getenv("GROQ_API_KEY", "")
    model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    timeout_s: int = int(os.getenv("GROQ_TIMEOUT_S", "300"))
    max_iterations: int = int(os.getenv("GROQ_MAX_ITERATIONS", "6"))

class EmbeddingConfig(BaseModel):
    token: str = os.getenv("HF_TOKEN", "")
    model: str = os.getenv("HF_MODEL", "")
    timeout_s: int = int(os.getenv("EMBEDDING_TIMEOUT_S", "300"))

class MongodbConfig(BaseModel):
    uri: str = os.getenv("MONGODB_URI", "")
    database: str = os.getenv("MONGODB_DATABASE", "")
    collection: str = os.getenv("MONGODB_COLLECTION", "")
    history_size: int = int(os.getenv("MONGODB_HISTORY_SIZE", "6"))

class QdrantConfig(BaseModel):
    url: str = os.getenv("QDRANT_URL", "")
    api_key: str = os.getenv("QDRANT_API_KEY", "")
    collection: str = os.getenv("QDRANT_COLLECTION", "")

class LangfuseConfig(BaseModel):
    system_prompt_name: str = os.getenv("LANGFUSE_SYSTEM_PROMPT_NAME", "agent")
    system_prompt_version: str = os.getenv("LANGFUSE_SYSTEM_PROMPT_VERSION", None)

class Settings(BaseModel):
    env: str = os.getenv("SERVICE_ENV", "local")
    request_timeout_s: int = int(os.getenv("REQUEST_TIMEOUT_S", "350"))
    
    groq: GroqConfig = GroqConfig()
    langfuse: LangfuseConfig = LangfuseConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    qdrant: QdrantConfig = QdrantConfig()
    mongodb: MongodbConfig = MongodbConfig()

settings = Settings()