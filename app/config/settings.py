from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal
import os


class Settings(BaseSettings):
    llm_provider: Literal["ollama", "openai"] = Field(default="ollama", alias="LLM_PROVIDER")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2:latest", alias="OLLAMA_MODEL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")

    chunk_size: int = Field(default=800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=150, alias="CHUNK_OVERLAP")

    faiss_index_path: str = Field(default="./data/faiss_index", alias="FAISS_INDEX_PATH")

    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")

    audio_dir: str = Field(default="./audio", alias="AUDIO_DIR")
    whisper_model: str = Field(default="base", alias="WHISPER_MODEL")

    top_k_retrieval: int = Field(default=5, alias="TOP_K_RETRIEVAL")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    model_config = {"env_file": ".env", "populate_by_name": True}

    def get_cors_origins(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

    def ensure_dirs(self):
        for d in [self.upload_dir, self.audio_dir, os.path.dirname(self.faiss_index_path)]:
            os.makedirs(d, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
