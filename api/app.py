import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import config
from api.routes import router
from api.websocket import ws_router

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv()

os.makedirs(config.UPLOAD_DIR, exist_ok=True)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

app = FastAPI(
    title="Risalah Rapat API",
    description="Pipeline otomatis risalah rapat — Audio/Folder → DOCX",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ws_router)


@app.get("/")
def root():
    return {"message": "Risalah Rapat API v2.0", "docs": "/docs"}
