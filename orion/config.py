from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class GroqConfig(BaseModel):
    api_key: str = os.getenv("GROQ_API_KEY", "")
    timeout_s: int = int(os.getenv("GROQ_TIMEOUT_S", "300"))
    max_iterations: int = int(os.getenv("GROQ_MAX_ITERATIONS", "6"))

class EmbeddingConfig(BaseModel):
    token: str = os.getenv("HF_TOKEN", "")
    model: str = os.getenv("HF_MODEL", "BAAI/bge-m3")
    timeout_s: int = int(os.getenv("EMBEDDING_TIMEOUT_S", "300"))

class MCPConfig(BaseModel):
    mcp_knowledge_transport: str = os.getenv("MCP_KNOWLEDGE_TRANSPORT", "streamable_http")
    mcp_knowledge_url: str = os.getenv("MCP_KNOWLEDGE_URL", "http://localhost:8181/mcp")

class MongodbConfig(BaseModel):
    uri: str = os.getenv("MONGODB_URI", "")
    database: str = os.getenv("MONGODB_DATABASE", "orion")
    collection: str = os.getenv("MONGODB_COLLECTION", "chat_history")
    history_size: int = int(os.getenv("MONGODB_HISTORY_SIZE", "6"))
    history_collection: str = os.getenv("MONGODB_HISTORY_COLLECTION", "histories")

class QdrantConfig(BaseModel):
    url: str = os.getenv("QDRANT_URL", "https://657e9ff8-daa0-4003-bf76-c531e697932d.europe-west3-0.gcp.cloud.qdrant.io:6333")
    api_key: str = os.getenv("QDRANT_API_KEY", "")
    collection: str = os.getenv("QDRANT_COLLECTION", "internal_knowledge")
    top_k: int = int(os.getenv("QDRANT_TOP_K", "10"))
    chunk_size: int = int(os.getenv("QDRANT_CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("QDRANT_CHUNK_OVERLAP", "100"))
    breakpoint_threshold_amount: int = int(os.getenv("QDRANT_BREAKPOINT_THRESHOLD_AMOUNT", "80"))

class LangfuseConfig(BaseModel):
    system_prompt_name: str = os.getenv("LANGFUSE_SYSTEM_PROMPT_NAME", "agent")
    system_prompt_version: str = os.getenv("LANGFUSE_SYSTEM_PROMPT_VERSION", None)

    knowledge_prompt_name: str = os.getenv("LANGFUSE_KNOWLEDGE_PROMPT_NAME", "knowledge")
    knowledge_prompt_version: str = os.getenv("LANGFUSE_KNOWLEDGE_PROMPT_VERSION", None)

    summary_prompt_name: str = os.getenv("LANGFUSE_SUMMARY_PROMPT_NAME", "summary")
    summary_prompt_version: str = os.getenv("LANGFUSE_SUMMARY_PROMPT_VERSION", None)

class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "orion")
    version: str = os.getenv("VERSION", "0.1.4")
    env: str = os.getenv("SERVICE_ENV", "local")
    token: str = os.getenv("TOKEN", "kajsdasdkjhsdf")
    request_timeout_s: int = int(os.getenv("REQUEST_TIMEOUT_S", "350"))
    
    groq: GroqConfig = GroqConfig()
    langfuse: LangfuseConfig = LangfuseConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    qdrant: QdrantConfig = QdrantConfig()
    mongodb: MongodbConfig = MongodbConfig()
    mcp: MCPConfig = MCPConfig()

settings = Settings()
