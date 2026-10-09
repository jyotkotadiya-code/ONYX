import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Local Multimodal RAG"
    APP_VERSION: str = "1.0.0"

    OFFLINE_MODE: bool = True

    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M"
    LLM_BASE_URL: str = "http://127.0.0.1:11434/v1"
    OLLAMA_NATIVE_URL: str = "http://127.0.0.1:11434"

    EMBEDDING_PROVIDER: str = "sentence_transformers"
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    EMBEDDING_DEVICE: str = "cpu"

    VECTOR_DB: str = "chroma"
    VECTOR_DB_PATH: str = "./data/vector_db"

    SQLITE_DB_PATH: str = "./data/metadata/app.db"

    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    CACHE_DIR: str = "./data/cache"
    MODELS_DIR: str = "./models"
    LOG_DIR: str = "./logs"

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120

    TOP_K: int = 5
    HYBRID_SEARCH_ENABLED: bool = True

    OCR_ENABLED: bool = True
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    OCR_LANGUAGES: str = "eng+hin+guj"
    AUDIO_ENABLED: bool = False
    WHISPER_MODEL_SIZE: str = "base"

    MAX_FILE_SIZE_MB: int = 100
    SECRET_KEY: str = "local-rag-private-key-8f94a2b1c0d3e4f5a6b7c8d9e0f1a2b3"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    FRONTEND_HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 3000

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def resolve_path(self, relative_or_abs: str) -> Path:
        p = Path(relative_or_abs)
        if not p.is_absolute():
            p = (BASE_DIR / p).resolve()
        return p

    def ensure_dirs(self) -> None:
        for dir_attr in [
            self.VECTOR_DB_PATH,
            os.path.dirname(self.SQLITE_DB_PATH),
            self.UPLOAD_DIR,
            self.PROCESSED_DIR,
            self.CACHE_DIR,
            self.MODELS_DIR,
            self.LOG_DIR,
        ]:
            path = self.resolve_path(dir_attr)
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()

# Enforce telemetry disablement for ChromaDB and HuggingFace when OFFLINE_MODE is active
if settings.OFFLINE_MODE:
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ["CHROMA_TELEMETRY"] = "False"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
