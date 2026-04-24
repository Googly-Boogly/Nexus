from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.rag.chunker import ChunkResult
from app.rag.retriever import RetrievalResult, RetrievalStats

CHUNK_INJECTION_PATTERNS = [
    r"(ignore|disregard|override)\s+(previous|above|all)\s+(instructions?|context|system)",
    r"(\\n|\\r|\n|\r)\s*(system|assistant)\s*:",
    r"<\s*(system|instruction|prompt)\s*>",
    r"\[\s*(INST|\/INST|SYS|\/SYS)\s*\]",
    r"you\s+are\s+now\s+",
    r"new\s+instructions?\s*:",
    r"---\s*(end|ignore)\s+(above|previous)\s*---",
    r"STOP[\.\s]+[Ii]gnore",
    r"<</SYS>>",
    r"\|{3,}",
    r"#\s*(system|SYSTEM)\s+prompt",
]

CLEARANCE_HIERARCHY = ["public", "internal", "confidential"]


class QueryTooLongError(Exception):
    pass


class PoisonedDocumentError(Exception):
    def __init__(self, chunk_index: int, pattern: str):
        self.chunk_index = chunk_index
        self.pattern = pattern
        super().__init__(f"Poisoned content at chunk {chunk_index}: {pattern}")


@dataclass
class IngestScanResult:
    clean: bool
    poisoned_chunk_index: int | None = None
    pattern_matched: str | None = None


class RAGDefenseLayer:

    def sanitize_query(self, query: str) -> str:
        if len(query) > settings.RAG_MAX_QUERY_LENGTH:
            raise QueryTooLongError(f"Query too long: {len(query)} > {settings.RAG_MAX_QUERY_LENGTH}")

        cleaned = re.sub(r"<[^>]+>", "", query)
        cleaned = re.sub(r"```[^`]*```", "", cleaned)

        from app.core.prompt_defense import INJECTION_PATTERNS
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                raise ValueError(f"Injection pattern detected in query: {pattern[:40]}")

        return cleaned.strip()

    def check_chunks_at_ingest(self, chunks: list[ChunkResult]) -> IngestScanResult:
        for chunk in chunks:
            chunk_idx = chunk.metadata.get("chunk_index", 0)
            for pattern in CHUNK_INJECTION_PATTERNS:
                if re.search(pattern, chunk.text, re.IGNORECASE):
                    raise PoisonedDocumentError(chunk_idx, pattern)
        return IngestScanResult(clean=True)

    async def check_retrieved_chunks(
        self,
        chunks: list[RetrievalResult],
        document_ids: list[str],
        session: AsyncSession,
    ) -> tuple[list[RetrievalResult], int]:
        clean = []
        quarantine_count = 0
        quarantined_by_doc: dict[str, int] = {}

        for chunk in chunks:
            poisoned = False
            for pattern in CHUNK_INJECTION_PATTERNS:
                if re.search(pattern, chunk.text, re.IGNORECASE):
                    poisoned = True
                    quarantine_count += 1
                    quarantined_by_doc[chunk.document_id] = (
                        quarantined_by_doc.get(chunk.document_id, 0) + 1
                    )
                    break
            if not poisoned:
                clean.append(chunk)

        poisoned_doc_ids = {
            doc_id for doc_id, count in quarantined_by_doc.items() if count >= 2
        }
        if poisoned_doc_ids:
            from app.models.knowledge import KnowledgeDocument
            from sqlalchemy import select
            import uuid
            for doc_id_str in poisoned_doc_ids:
                try:
                    doc_id = uuid.UUID(doc_id_str)
                    result = await session.execute(
                        select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
                    )
                    doc = result.scalar_one_or_none()
                    if doc:
                        doc.poisoning_suspected = True
                        await session.flush()
                except Exception:
                    pass

            clean = [c for c in clean if c.document_id not in poisoned_doc_ids]

        return clean, quarantine_count

    def enforce_relevance_gate(
        self,
        results: list[RetrievalResult],
        min_score: float | None = None,
    ) -> list[RetrievalResult]:
        if min_score is None:
            min_score = settings.RAG_MIN_SCORE
        return [r for r in results if r.cross_score >= min_score]

    def enforce_classification(
        self,
        results: list[RetrievalResult],
        user_clearance: str,
    ) -> tuple[list[RetrievalResult], int]:
        try:
            user_level = CLEARANCE_HIERARCHY.index(user_clearance)
        except ValueError:
            user_level = 0

        clean = []
        filtered = 0
        for r in results:
            try:
                doc_level = CLEARANCE_HIERARCHY.index(r.classification)
            except ValueError:
                doc_level = 0
            if doc_level <= user_level:
                clean.append(r)
            else:
                filtered += 1
        return clean, filtered

    def format_context_block(
        self,
        results: list[RetrievalResult],
        stats: RetrievalStats,
    ) -> str:
        if not results:
            return ""

        doc_ids = {r.document_id for r in results}
        lines = [
            "==========================================================",
            "RETRIEVED KNOWLEDGE — cite sources explicitly in response",
            f"Retrieved: {stats.after_relevance_gate} chunks from {len(doc_ids)} documents",
            f"Paths: pgvector ({stats.pgvector_results}) + Qdrant ({stats.qdrant_dense_results} dense, "
            f"{stats.qdrant_sparse_results} sparse) → fused → reranked",
            "==========================================================",
        ]

        for i, r in enumerate(results, start=1):
            paths_str = ", ".join(r.source_paths)
            lines.append(
                f"[SOURCE {i}] {r.title} | {r.category} | relevance: {r.cross_score:.2f}"
            )
            lines.append(
                f"           Paths: {paths_str} | chunk {r.chunk_index}"
            )
            lines.append(r.text)
            lines.append("")

        lines.append("==========================================================")
        lines.append("END RETRIEVED KNOWLEDGE")
        return "\n".join(lines)

    async def check_response_attribution(
        self,
        response: str,
        sources: list[RetrievalResult],
        warnings: list[str],
    ) -> list[str]:
        if not sources:
            return warnings

        response_lower = response.lower()
        any_cited = any(
            s.title.lower() in response_lower or s.title.split()[0].lower() in response_lower
            for s in sources
        )
        if not any_cited:
            warnings.append(
                "Response may contain uncited information not from knowledge base"
            )
        return warnings
