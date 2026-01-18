from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DocuBuddy Backend"
    debug: bool = True
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # MongoDB Configuration
    mongodb_url: str = "mongodb://docubuddy:docubuddy123@localhost:27017/docubuddy_db?authSource=admin"
    mongodb_db_name: str = "docubuddy_db"
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7
    
    # ChromaDB Configuration
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection_name: str = "documentation"
    
    # Documentation Path
    docs_path: str = "../docu-buddy-frontend/docs"
    
    # Conversation Memory
    max_conversation_length: int = 20
    conversation_ttl_hours: int = 24
    
    # Retrieval Configuration
    retrieval_top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings() # pyright: ignore[reportCallIssue]