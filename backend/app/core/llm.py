import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm():
    """
    Initializes and returns the configured Chat LLM.

    Free-tier quota comparison (as of 2025):
    - gemini-2.0-flash:   1,500 req/day, 15 req/min  ← PRIMARY
    - gemini-1.5-flash:   1,500 req/day, 15 req/min  ← SECONDARY
    - gemini-2.5-flash:      20 req/day               ← LAST RESORT
    - OpenAI gpt-4o-mini: quota exhausted             ← DISABLED

    Priority order: 2.0-flash → 1.5-flash → 2.5-flash → OpenAI
    """
    openai_key = settings.OPENAI_API_KEY
    if not openai_key or openai_key == ".\\.c":
        openai_key = os.getenv("OPEN_API_KEY", "")
    gemini_key = settings.GEMINI_API_KEY

    if gemini_key:
        # Primary: gemini-2.0-flash (best free-tier quota)
        for model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]:
            try:
                return ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=gemini_key,
                    temperature=0.1,
                    max_retries=5
                )
            except Exception as e:
                print(f"Failed to initialize {model}: {e}")
                continue

    # Last resort: OpenAI (quota may be exhausted)
    if openai_key:
        try:
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_key,
                temperature=0.1,
                max_retries=5
            )
        except Exception as e:
            print(f"Failed to initialize OpenAI LLM: {e}")

    raise ValueError("No valid LLM API key detected. Please configure GEMINI_API_KEY or OPENAI_API_KEY.")
