import os

from dotenv import load_dotenv

load_dotenv()

LLM_CONFIGS = [
    {
        "name": "Groq",
        "base": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        "key": os.getenv("GROQ_API_KEY", ""),
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    },
    {
        "name": "9router",
        "base": os.getenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1"),
        "key": os.getenv("NINEROUTER_API_KEY", ""),
        "model": os.getenv("NINEROUTER_MODEL", "groq/llama-3.3-70b-versatile"),
    },
    {
        "name": "Gemini",
        "base": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    },
]


class Config:
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
    HF_TOKEN = os.getenv("HF_TOKEN", "")

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

    LLM_CONFIGS = LLM_CONFIGS


config = Config()
