from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.rag.embedder import EmbeddingProvider
from app.rag.fusion import reciprocal_rank_fusion
from app.rag.pgvector_store import PGVectorStore
from app.rag.qdrant_store import QdrantStore
from app.rag.reranker import CrossEncoderReranker, RerankedResult


@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    text: str
    title: str
    category: str
    classification: str
    chunk_index: int
    token_count: int
    pgvector_rank: int | None
    qdrant_dense_rank: int | None
    qdrant_sparse_rank: int | None
    rrf_score: float
    cross_score: float
    source_paths: list[str]


@dataclass
class RetrievalStats:
    pgvector_results: int
    qdrant_dense_results: int
    qdrant_sparse_results: int
    after_fusion: int
    after_rerank: int
    after_relevance_gate: int
    quarantined_by_defense: int
    filtered_by_classification: int
    query_time_ms: int


CLEARANCE_HIERARCHY = ["public", "internal", "confidential"]


class HybridRetriever:

    def __init__(self):
        self.embedder = EmbeddingProvider()
        self.pgvector = PGVectorStore()
        self.qdrant = QdrantStore()
        self.reranker = CrossEncoderReranker.get()

    def _clearance_levels(self, user_clearance: str) -> list[str]:
        try:
            idx = CLEARANCE_HIERARCHY.index(user_clearance)
        except ValueError:
            idx = 0
        return CLEARANCE_HIERARCHY[: idx + 1]

    async def retrieve(
        self,
        query: str,
        user_clearance: str,
        session: AsyncSession,
        category_filter: str | None = None,
        top_k: int | None = None,
        rerank_top_n: int | None = None,
    ) -> tuple[list[RetrievalResult], RetrievalStats]:
        if top_k is None:
            top_k = settings.RAG_TOP_K_PER_PATH
        if rerank_top_n is None:
            rerank_top_n = settings.RAG_RERANK_TOP_N

        t_start = time.monotonic()
        clearance_levels = self._clearance_levels(user_clearance)

        query_vector = await self.embedder.embed_query(query)
        sparse_vec = self.qdrant._build_sparse_vector(query)

        pgvector_task = self.pgvector.similarity_search(
            query_vector=query_vector,
            session=session,
            category=category_filter,
            classification_levels=clearance_levels,
            top_k=top_k,
        )
        qdrant_task = self.qdrant.hybrid_search(
            query_dense=query_vector,
            query_sparse=sparse_vec,
            classification_filter=clearance_levels,
            category_filter=category_filter,
            top_k=top_k,
        )

        pgvector_res, qdrant_res = await asyncio.gather(pgvector_task, qdrant_task)

        dense_res = qdrant_res[: len(qdrant_res) // 2 + len(qdrant_res) % 2]
        sparse_res = qdrant_res[len(qdrant_res) // 2 + len(qdrant_res) % 2 :]

        fused = reciprocal_rank_fusion(pgvector_res, dense_res, sparse_res)
        reranked = self.reranker.rerank(query, fused, top_n=rerank_top_n)

        results = [
            RetrievalResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                title=r.title,
                category=r.category,
                classification=r.classification,
                chunk_index=r.chunk_index,
                token_count=r.token_count,
                pgvector_rank=r.pgvector_rank,
                qdrant_dense_rank=r.qdrant_dense_rank,
                qdrant_sparse_rank=r.qdrant_sparse_rank,
                rrf_score=r.rrf_score,
                cross_score=r.cross_score,
                source_paths=r.source_paths,
            )
            for r in reranked
        ]

        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        stats = RetrievalStats(
            pgvector_results=len(pgvector_res),
            qdrant_dense_results=len(dense_res),
            qdrant_sparse_results=len(sparse_res),
            after_fusion=len(fused),
            after_rerank=len(results),
            after_relevance_gate=len(results),
            quarantined_by_defense=0,
            filtered_by_classification=0,
            query_time_ms=elapsed_ms,
        )
        return results, stats
