"""
FastAPI application - DarGlobal & Wasalt AI Chatbot.
"""

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.retrieval import RetrievalEngine
from app.chat import ChatEngine

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Initialize retrieval engine
chunks_path = DATA_DIR / "knowledge_chunks.json"
retrieval_engine = RetrievalEngine(str(chunks_path) if chunks_path.exists() else None)

# Initialize chat engine
chat_engine = ChatEngine(retrieval_engine)

# FastAPI app
app = FastAPI(
    title="DarGlobal & Wasalt AI Chatbot",
    description="AI-powered chatbot for DarGlobal and Wasalt real estate information",
    version="1.0.0",
)

# Static files and templates
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# --- Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the chatbot UI."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Process a chat message and return AI response."""
    session_id = req.session_id or str(uuid.uuid4())
    response = await chat_engine.chat(req.message, session_id)
    return ChatResponse(response=response, session_id=session_id)


@app.post("/api/clear")
async def clear_chat(req: ChatRequest):
    """Clear conversation history."""
    session_id = req.session_id or "default"
    chat_engine.clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    has_api_key = bool(os.getenv("OPENROUTER_API_KEY"))
    return {
        "status": "healthy",
        "knowledge_chunks": len(retrieval_engine.chunks),
        "openrouter_configured": has_api_key,
        "model": chat_engine.model,
    }


@app.get("/api/info")
async def info():
    """Return information about the chatbot configuration."""
    return {
        "name": "DarGlobal & Wasalt AI Chatbot",
        "version": "1.0.0",
        "data_sources": ["DarGlobal (darglobal.co.uk)", "Wasalt (wasalt.com)"],
        "knowledge_chunks": len(retrieval_engine.chunks),
        "model": chat_engine.model,
        "features": [
            "RAG-based retrieval from scraped DarGlobal and Wasalt data",
            "TF-IDF similarity search for relevant context",
            "Conversational memory within sessions",
            "OpenRouter integration with free LLM models",
            "Fallback through multiple free models",
        ],
    }
