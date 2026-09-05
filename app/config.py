from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "gemini"       # gemini | openai | azure_openai
    vector_store: str = "chroma"       # chroma | pinecone | azure_search

    google_api_key: str = ""
    openai_api_key: str = ""

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"

    pinecone_api_key: str = ""
    pinecone_index: str = "rag-doc-chat"

    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index: str = "rag-doc-chat"

    chroma_persist_dir: str = "./chroma_db"

    session_ttl_hours: int = 6
    max_upload_mb: int = 15
    backend_url: str = "http://127.0.0.1:8091"

    class Config:
        env_file = ".env"


settings = Settings()
