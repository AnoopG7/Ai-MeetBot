from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "finance-advisor"
    app_version: str = "0.1.0"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    livekit_url: str = "ws://localhost:7880"
    livekit_public_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "this-is-a-minimum-32-char-development-secret!!"

    redis_url: str = "redis://localhost:6379"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "finance_knowledge"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/advisor"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    llm_provider: Literal["openai", "ollama"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b-instruct-q4_K_M"

    stt_provider: Literal["deepgram", "whisper"] = "deepgram"
    deepgram_api_key: str = ""

    tts_provider: Literal["cartesia", "edge-tts", "elevenlabs"] = "cartesia"
    cartesia_api_key: str = ""
    cartesia_voice_id: str = "6f6a6c6c-6b6a-4e6f-8e6a-6c6c6b6a4e6f"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    project_root: Path = Path(__file__).resolve().parent.parent.parent.parent
    knowledge_dir: Path = project_root / "data" / "knowledge"


settings = Settings()
