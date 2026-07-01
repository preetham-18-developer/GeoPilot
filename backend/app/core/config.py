import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Recommendation System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Supabase config
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://wnjnebqwgrjfsmbkgiua.supabase.co")
    SUPABASE_KEY: str = os.getenv(
        "SUPABASE_KEY", 
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Induam5lYnF3Z3JqZnNtYmtnaXVhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MTQwMzksImV4cCI6MjA5NTI5MDAzOX0.T60uDBZGi2xXl4HONMnU9VNqfpFLuv7f_E50wRyM2Wg"
    )
    
    # LLM keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPEN_API_KEY", os.getenv("OPENAI_API_KEY", "")) # Fallback to user's detected OPEN_API_KEY
    
    # Qdrant config (default to local in-memory)
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "./qdrant_data")
    
    class Config:
        case_sensitive = True

settings = Settings()
