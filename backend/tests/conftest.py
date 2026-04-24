import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_PASSWORD", "")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("QDRANT_URL", "")

# Patch pgvector.sqlalchemy.VECTOR → SQLAlchemy Text so SQLite can create the schema
import pgvector.sqlalchemy as _pgvec
from sqlalchemy import Text as _Text
_pgvec.VECTOR = lambda dim=None: _Text()  # type: ignore[assignment]

from app.database import Base
from app.config import settings


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from app.database import get_db

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def make_token(username: str, role: str, clearance: str, user_id: str | None = None) -> str:
    from app.core.security import create_access_token
    return create_access_token({
        "sub": username,
        "role": role,
        "clearance": clearance,
        "user_id": user_id or str(uuid.uuid4()),
    })


@pytest.fixture
def admin_token():
    return make_token("admin", "admin", "confidential")


@pytest.fixture
def operator_token():
    return make_token("operator", "operator", "internal")


@pytest.fixture
def viewer_token():
    return make_token("viewer", "viewer", "public")


# ─── Mock stores for unit tests ───────────────────────────────────────────────

from app.rag.retriever import RetrievalResult


def make_retrieval_result(**kwargs) -> RetrievalResult:
    defaults = dict(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        text="Sample chunk text about incident response procedures.",
        title="Incident Response Runbook",
        category="runbook",
        classification="internal",
        chunk_index=0,
        token_count=50,
        pgvector_rank=1,
        qdrant_dense_rank=1,
        qdrant_sparse_rank=1,
        rrf_score=0.8,
        cross_score=0.75,
        source_paths=["pgvector", "qdrant_dense"],
    )
    defaults.update(kwargs)
    return RetrievalResult(**defaults)


class MockEmbedder:
    async def embed_texts(self, texts):
        import hashlib, math, random
        results = []
        for t in texts:
            seed = int(hashlib.md5(t.encode()).hexdigest(), 16) % (2**32)
            rng = random.Random(seed)
            v = [rng.gauss(0, 1) for _ in range(1536)]
            norm = math.sqrt(sum(x*x for x in v)) or 1.0
            results.append([x/norm for x in v])
        return results

    async def embed_query(self, query):
        return (await self.embed_texts([query]))[0]


class MockReranker:
    def rerank(self, query, candidates, top_n=None):
        from app.rag.reranker import RerankedResult
        if top_n is None:
            top_n = 4
        sorted_cands = sorted(candidates, key=lambda c: c.rrf_score, reverse=True)[:top_n]
        results = []
        for c in sorted_cands:
            d = {k: v for k, v in vars(c).items()}
            results.append(RerankedResult(**d, cross_score=c.rrf_score))
        return results


class MockPGVectorStore:
    def __init__(self, results=None):
        self._results = results or []

    async def similarity_search(self, **kwargs):
        from app.rag.pgvector_store import PGVectorResult
        return [
            PGVectorResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                title=r.title,
                category=r.category,
                classification=r.classification,
                chunk_index=r.chunk_index,
                token_count=r.token_count,
                similarity_score=r.cross_score,
            )
            for r in self._results
        ]


class MockQdrantStore:
    def __init__(self, results=None):
        self._results = results or []

    async def hybrid_search(self, **kwargs):
        from app.rag.qdrant_store import QdrantResult
        return [
            QdrantResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                title=r.title,
                category=r.category,
                classification=r.classification,
                chunk_index=r.chunk_index,
                token_count=r.token_count,
                score=r.cross_score,
            )
            for r in self._results
        ]

    def _build_sparse_vector(self, text):
        from app.rag.qdrant_store import SparseVector
        return SparseVector(indices=[1, 2, 3], values=[0.5, 0.3, 0.2])
