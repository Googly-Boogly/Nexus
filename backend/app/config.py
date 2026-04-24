from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production-min32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql+asyncpg://nexus:nexus@postgres:5432/nexus"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    REDIS_URL: str = "redis://:nexusredis@redis:6379/0"
    REDIS_PASSWORD: str = "nexusredis"

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    PRIMARY_LLM_PROVIDER: str = "openai"
    OPENAI_MODEL: str = "gpt-5-nano"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    DEMO_MODE: bool = True
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_BATCH_SIZE: int = 100

    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION: str = "nexus_knowledge"

    OPA_URL: str = "http://opa:8181"

    RAG_CHUNK_SIZE_TOKENS: int = 512
    RAG_CHUNK_OVERLAP_TOKENS: int = 50
    RAG_TOP_K_PER_PATH: int = 10
    RAG_RERANK_TOP_N: int = 4
    RAG_MIN_SCORE: float = 0.65
    RAG_MAX_QUERY_LENGTH: int = 500

    PGVECTOR_EF_SEARCH: int = 64
    PGVECTOR_INDEX_LISTS: int = 100

    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    MAX_INPUT_LENGTH: int = 2000
    MAX_AGENT_ITERATIONS: int = 10
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 30

    LOG_LEVEL: str = "INFO"


settings = Settings()
