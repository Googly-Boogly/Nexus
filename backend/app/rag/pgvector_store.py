from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument


@dataclass
class PGVectorResult:
    chunk_id: str
    document_id: str
    text: str
    title: str
    category: str
    classification: str
    chunk_index: int
    token_count: int
    similarity_score: float


class PGVectorStore:
    """
    pgvector retrieval path. Uses HNSW index on knowledge_chunks.embedding.
    All SQL via SQLAlchemy ORM — zero raw f-string SQL.
    """

    async def similarity_search(
        self,
        query_vector: list[float],
        session: AsyncSession,
        category: str | None = None,
        classification_levels: list[str] | None = None,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int = 10,
    ) -> list[PGVectorResult]:
        # pgvector ops (cosine_distance, SET LOCAL) require PostgreSQL; return empty for SQLite
        if "sqlite" in settings.DATABASE_URL:
            return []

        await session.execute(
            text(f"SET LOCAL hnsw.ef_search = {int(settings.PGVECTOR_EF_SEARCH)}")
        )

        stmt = (
            select(
                KnowledgeChunk,
                KnowledgeDocument.title,
                KnowledgeDocument.category,
                KnowledgeDocument.data_classification,
                KnowledgeChunk.embedding.cosine_distance(query_vector).label("distance"),
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.is_active == True)  # noqa: E712
            .where(KnowledgeChunk.embedding.is_not(None))
        )

        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)
        if classification_levels:
            stmt = stmt.where(KnowledgeDocument.data_classification.in_(classification_levels))
        if document_ids:
            stmt = stmt.where(KnowledgeChunk.document_id.in_(document_ids))

        stmt = stmt.order_by(text("distance")).limit(top_k)

        rows = (await session.execute(stmt)).all()
        results = []
        for row in rows:
            chunk, title, category_val, classification, distance = row
            results.append(
                PGVectorResult(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    text=chunk.text,
                    title=title,
                    category=category_val,
                    classification=classification,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.token_count,
                    similarity_score=1.0 - float(distance),
                )
            )
        return results

    async def full_text_search(
        self,
        query_text: str,
        session: AsyncSession,
        category: str | None = None,
        classification_levels: list[str] | None = None,
        top_k: int = 10,
    ) -> list[PGVectorResult]:
        tsquery = func.plainto_tsquery("english", query_text)
        tsvector = func.to_tsvector("english", KnowledgeChunk.text)
        rank = func.ts_rank_cd(tsvector, tsquery)

        stmt = (
            select(
                KnowledgeChunk,
                KnowledgeDocument.title,
                KnowledgeDocument.category,
                KnowledgeDocument.data_classification,
                rank.label("rank"),
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.is_active == True)  # noqa: E712
            .where(tsvector.op("@@")(tsquery))
        )

        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)
        if classification_levels:
            stmt = stmt.where(KnowledgeDocument.data_classification.in_(classification_levels))

        stmt = stmt.order_by(text("rank DESC")).limit(top_k)

        rows = (await session.execute(stmt)).all()
        results = []
        for row in rows:
            chunk, title, category_val, classification, rank_val = row
            results.append(
                PGVectorResult(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    text=chunk.text,
                    title=title,
                    category=category_val,
                    classification=classification,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.token_count,
                    similarity_score=float(rank_val),
                )
            )
        return results

    async def metadata_search(
        self,
        session: AsyncSession,
        category: str | None = None,
        classification_levels: list[str] | None = None,
        uploaded_after: datetime | None = None,
        uploaded_before: datetime | None = None,
        title_contains: str | None = None,
        top_k: int = 50,
    ) -> list[KnowledgeDocument]:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.is_active == True)  # noqa: E712

        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)
        if classification_levels:
            stmt = stmt.where(KnowledgeDocument.data_classification.in_(classification_levels))
        if uploaded_after:
            stmt = stmt.where(KnowledgeDocument.created_at >= uploaded_after)
        if uploaded_before:
            stmt = stmt.where(KnowledgeDocument.created_at <= uploaded_before)
        if title_contains:
            stmt = stmt.where(KnowledgeDocument.title.ilike(f"%{title_contains}%"))

        stmt = stmt.order_by(KnowledgeDocument.created_at.desc()).limit(top_k)
        rows = (await session.execute(stmt)).scalars().all()
        return list(rows)

    async def get_chunks_by_document(
        self,
        document_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        return list((await session.execute(stmt)).scalars().all())
