from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.chunker import TokenAwareChunker
from app.rag.embedder import EmbeddingProvider
from app.rag.pgvector_store import PGVectorStore
from app.rag.qdrant_store import QdrantPoint, QdrantStore
from app.rag.rag_defense import RAGDefenseLayer, PoisonedDocumentError
from app.rag.retriever import HybridRetriever, RetrievalResult, RetrievalStats

AGENT_TYPE_CATEGORY_MAP: dict[str, str] = {
    "incident_response": "runbook",
    "compliance_scan": "compliance",
    "infrastructure_provisioning": "infrastructure",
}


@dataclass
class IngestResult:
    document_id: str
    chunk_count: int
    token_count: int
    qdrant_upserted: int
    pgvector_upserted: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class RAGContext:
    formatted_block: str
    sources: list[RetrievalResult]
    stats: RetrievalStats
    was_retrieved: bool


class RAGPipeline:

    def __init__(self):
        self.chunker = TokenAwareChunker()
        self.embedder = EmbeddingProvider()
        self.qdrant = QdrantStore()
        self.pgvector = PGVectorStore()
        self.retriever = HybridRetriever()
        self.defense = RAGDefenseLayer()

    async def ingest_document(
        self,
        file_text: str,
        title: str,
        category: str,
        classification: str,
        uploaded_by: uuid.UUID,
        session: AsyncSession,
    ) -> IngestResult:
        warnings: list[str] = []

        chunks = self.chunker.chunk_document(file_text, {"title": title, "category": category})
        if not chunks:
            warnings.append("No chunks produced")
            return IngestResult("", 0, 0, 0, 0, warnings)

        self.defense.check_chunks_at_ingest(chunks)

        texts = [c.text for c in chunks]
        vectors = await self.embedder.embed_texts(texts)
        total_tokens = sum(c.token_count for c in chunks)

        doc = KnowledgeDocument(
            title=title,
            source_filename=f"{title.lower().replace(' ', '_')}.md",
            category=category,
            data_classification=classification,
            chunk_count=len(chunks),
            token_count=total_tokens,
            embedding_model=settings.EMBEDDING_MODEL,
            uploaded_by=uploaded_by,
        )
        session.add(doc)
        await session.flush()

        qdrant_points = []
        db_chunks = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = uuid.uuid4()
            sparse_vec = self.qdrant._build_sparse_vector(chunk.text)
            qdrant_points.append(
                QdrantPoint(
                    id=str(point_id),
                    dense_vector=vector,
                    sparse_vector=sparse_vec,
                    payload={
                        "chunk_id": str(point_id),
                        "document_id": str(doc.id),
                        "chunk_index": i,
                        "text": chunk.text,
                        "title": title,
                        "category": category,
                        "classification": classification,
                        "token_count": chunk.token_count,
                        "is_active": True,
                    },
                )
            )
            db_chunks.append(
                KnowledgeChunk(
                    document_id=doc.id,
                    qdrant_point_id=point_id,
                    chunk_index=i,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    embedding=vector,
                    chunk_metadata=chunk.metadata,
                )
            )

        await self.qdrant.upsert_points(qdrant_points)
        session.add_all(db_chunks)
        await session.flush()

        return IngestResult(
            document_id=str(doc.id),
            chunk_count=len(chunks),
            token_count=total_tokens,
            qdrant_upserted=len(qdrant_points),
            pgvector_upserted=len(db_chunks),
            warnings=warnings,
        )

    async def retrieve_for_agent(
        self,
        query: str,
        agent_type: str,
        user_clearance: str,
        session: AsyncSession,
    ) -> RAGContext:
        category_filter = AGENT_TYPE_CATEGORY_MAP.get(agent_type)

        clean_query = self.defense.sanitize_query(query)

        results, stats = await self.retriever.retrieve(
            query=clean_query,
            user_clearance=user_clearance,
            session=session,
            category_filter=category_filter,
        )

        doc_ids = list({r.document_id for r in results})
        results, quarantined = await self.defense.check_retrieved_chunks(results, doc_ids, session)
        stats.quarantined_by_defense = quarantined

        results = self.defense.enforce_relevance_gate(results)
        stats.after_relevance_gate = len(results)

        results, filtered = self.defense.enforce_classification(results, user_clearance)
        stats.filtered_by_classification = filtered

        formatted = self.defense.format_context_block(results, stats)

        return RAGContext(
            formatted_block=formatted,
            sources=results,
            stats=stats,
            was_retrieved=bool(results),
        )

    async def search(
        self,
        query: str,
        user_clearance: str,
        category: str | None,
        session: AsyncSession,
        top_n: int = 10,
    ) -> tuple[list[RetrievalResult], RetrievalStats]:
        clean_query = self.defense.sanitize_query(query)

        results, stats = await self.retriever.retrieve(
            query=clean_query,
            user_clearance=user_clearance,
            session=session,
            category_filter=category,
            top_k=top_n,
            rerank_top_n=top_n,
        )

        doc_ids = list({r.document_id for r in results})
        results, quarantined = await self.defense.check_retrieved_chunks(results, doc_ids, session)
        stats.quarantined_by_defense = quarantined

        results = self.defense.enforce_relevance_gate(results)
        stats.after_relevance_gate = len(results)

        results, filtered = self.defense.enforce_classification(results, user_clearance)
        stats.filtered_by_classification = filtered

        return results, stats

    async def compare_paths(self, query: str) -> None:
        """Debug utility: prints side-by-side path comparison."""
        from app.database import AsyncSessionLocal
        from app.rag.embedder import EmbeddingProvider

        embedder = EmbeddingProvider()
        vector = await embedder.embed_query(query)
        sparse = self.qdrant._build_sparse_vector(query)

        async with AsyncSessionLocal() as session:
            pgvec_results = await self.pgvector.similarity_search(
                query_vector=vector, session=session, top_k=10
            )
            qdrant_results = await self.qdrant.hybrid_search(
                query_dense=vector, query_sparse=sparse,
                classification_filter=["public", "internal", "confidential"],
                top_k=10,
            )

        pgvec_ids = {r.chunk_id for r in pgvec_results}
        qdrant_ids = {r.chunk_id for r in qdrant_results}

        print(f"\nQuery: {query!r}")
        print(f"pgvector only: {len(pgvec_ids - qdrant_ids)}")
        print(f"qdrant only: {len(qdrant_ids - pgvec_ids)}")
        print(f"both: {len(pgvec_ids & qdrant_ids)}")

        from app.rag.fusion import reciprocal_rank_fusion
        fused = reciprocal_rank_fusion(pgvec_results, qdrant_results, [], k=60)
        print(f"\nTop 5 after RRF:")
        for r in fused[:5]:
            print(f"  [{r.rrf_score:.4f}] {r.title} chunk {r.chunk_index} | paths: {r.source_paths}")
