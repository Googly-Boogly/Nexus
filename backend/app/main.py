from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.api.routes import auth, tasks, audit, approvals, knowledge
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Qdrant collection on startup
    try:
        from app.rag.qdrant_store import QdrantStore
        qdrant = QdrantStore()
        await qdrant.create_collection_if_not_exists()
    except Exception:
        pass

    # Warm up reranker in background (non-blocking)
    if not settings.DEMO_MODE:
        try:
            from app.rag.reranker import CrossEncoderReranker
            CrossEncoderReranker.get()
        except Exception:
            pass

    yield


app = FastAPI(
    title="NEXUS Enterprise IT Automation Platform",
    version="1.0.0",
    description="Multi-agent IT automation with dual-DB RAG pipeline",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(audit.router)
app.include_router(approvals.router)
app.include_router(knowledge.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "nexus-api", "version": "1.0.0"}
