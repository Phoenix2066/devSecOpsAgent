import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    fastapi_port: int = int(os.getenv("FASTAPI_PORT", "8001"))
    database_url: str = os.getenv("DATABASE_URL", "postgres://anvil:anvil@localhost:5432/devsecops")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    serper_api_key: str = os.getenv("SERPER_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "anvilpassword")
    omium_api_key: str = os.getenv("OMIUM_API_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")


settings = Settings()
