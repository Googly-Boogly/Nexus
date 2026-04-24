import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user, require_admin
from app.config import settings
from app.core.audit import EventType, log_event
from app.core.security import accessible_levels
from app.database import get_db
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.rag.rag_defense import PoisonedDocumentError
from app.schemas.knowledge import (
    DocumentDetail,
    DocumentOut,
    IngestResultOut,
    KnowledgeStatsOut,
    SearchRequest,
    SearchResponse,
    SearchResultOut,
    RetrievalStatsOut,
    ChunkPreview,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

pipeline = RAGPipeline()

VALID_CATEGORIES = {"runbook", "compliance", "infrastructure", "general"}
VALID_CLASSIFICATIONS = {"public", "internal", "confidential"}


@router.post("/ingest", response_model=IngestResultOut)
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form(...),
    classification: str = Form(...),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Invalid category. Must be one of: {VALID_CATEGORIES}")
    if classification not in VALID_CLASSIFICATIONS:
        raise HTTPException(status_code=422, detail=f"Invalid classification: {VALID_CLASSIFICATIONS}")

    content = await file.read()
    file_text = content.decode("utf-8", errors="replace")

    try:
        result = await pipeline.ingest_document(
            file_text=file_text,
            title=title,
            category=category,
            classification=classification,
            uploaded_by=admin.id,
            session=session,
        )
    except PoisonedDocumentError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Poisoned document rejected at chunk {e.chunk_index}: {e.pattern}",
        )

    await log_event(
        session, EventType.KNOWLEDGE_INGESTED, user_id=admin.id,
        resource_id=result.document_id,
        details={"title": title, "chunks": result.chunk_count, "tokens": result.token_count},
    )
    return result


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    title_contains: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    from app.rag.pgvector_store import PGVectorStore
    store = PGVectorStore()
    levels = accessible_levels(user.data_clearance)
    docs = await store.metadata_search(
        session=session,
        category=category,
        classification_levels=levels,
        title_contains=title_contains,
        top_k=limit,
    )
    return docs


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
async def get_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    from app.core.security import clearance_level
    result = await session.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(doc_id))
    )
    doc = result.scalar_one_or_none()
    if not doc or not doc.is_active:
        raise HTTPException(status_code=404, detail="Document not found")
    if clearance_level(user.data_clearance) < clearance_level(doc.data_classification):
        raise HTTPException(status_code=403, detail="Insufficient clearance")

    chunks_result = await session.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == doc.id)
        .order_by(KnowledgeChunk.chunk_index)
        .limit(5)
    )
    chunks = list(chunks_result.scalars().all())
    previews = [
        ChunkPreview(
            chunk_index=c.chunk_index,
            text_preview=c.text[:300],
            token_count=c.token_count,
        )
        for c in chunks
    ]

    detail = DocumentDetail.model_validate(doc)
    detail.chunk_previews = previews
    return detail


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(doc_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.is_active = False
    await pipeline.qdrant.delete_by_document_id(doc_id)

    await log_event(session, EventType.KNOWLEDGE_DELETED, user_id=admin.id,
                    resource_id=doc_id, details={"title": doc.title})
    await session.commit()
    return {"status": "deleted", "document_id": doc_id}


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    body: SearchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if settings.DEMO_MODE:
        empty_stats = RetrievalStatsOut(
            pgvector_results=0, qdrant_dense_results=0, qdrant_sparse_results=0,
            after_fusion=0, after_rerank=0, after_relevance_gate=0,
            quarantined_by_defense=0, filtered_by_classification=0, query_time_ms=1,
        )
        return SearchResponse(results=[], retrieval_stats=empty_stats)

    results, stats = await pipeline.search(
        query=body.query,
        user_clearance=user.data_clearance,
        category=body.category,
        session=session,
        top_n=body.top_n,
    )

    out_results = [
        SearchResultOut(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            title=r.title,
            category=r.category,
            classification=r.classification,
            chunk_index=r.chunk_index,
            token_count=r.token_count,
            text=r.text,
            cross_score=r.cross_score,
            rrf_score=r.rrf_score,
            pgvector_rank=r.pgvector_rank,
            qdrant_dense_rank=r.qdrant_dense_rank,
            qdrant_sparse_rank=r.qdrant_sparse_rank,
            source_paths=r.source_paths,
        )
        for r in results
    ]

    return SearchResponse(
        results=out_results,
        retrieval_stats=RetrievalStatsOut(**vars(stats)),
    )


@router.get("/stats", response_model=KnowledgeStatsOut)
async def knowledge_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    total_docs = (await session.execute(
        select(func.count()).where(KnowledgeDocument.is_active == True)  # noqa: E712
    )).scalar() or 0

    total_chunks = (await session.execute(
        select(func.count(KnowledgeChunk.id))
        .join(KnowledgeDocument)
        .where(KnowledgeDocument.is_active == True)  # noqa: E712
    )).scalar() or 0

    total_tokens = (await session.execute(
        select(func.sum(KnowledgeDocument.token_count))
        .where(KnowledgeDocument.is_active == True)  # noqa: E712
    )).scalar() or 0

    by_cat_rows = (await session.execute(
        select(KnowledgeDocument.category, func.count())
        .where(KnowledgeDocument.is_active == True)  # noqa: E712
        .group_by(KnowledgeDocument.category)
    )).all()
    by_category = {row[0]: row[1] for row in by_cat_rows}

    by_class_rows = (await session.execute(
        select(KnowledgeDocument.data_classification, func.count())
        .where(KnowledgeDocument.is_active == True)  # noqa: E712
        .group_by(KnowledgeDocument.data_classification)
    )).all()
    by_classification = {row[0]: row[1] for row in by_class_rows}

    qdrant_info = {} if settings.DEMO_MODE else await pipeline.qdrant.get_collection_info()

    return KnowledgeStatsOut(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_tokens=total_tokens,
        by_category=by_category,
        by_classification=by_classification,
        qdrant_vectors_count=qdrant_info.get("vectors_count", 0),
        qdrant_memory_bytes=qdrant_info.get("disk_usage_bytes", 0),
        recent_ingests=[],
    )


@router.get("/compare-paths")
async def compare_paths(
    query: str,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    if settings.DEMO_MODE:
        return {
            "query": query, "pgvector_only": [], "qdrant_only": [],
            "both": [], "fused_top5": [], "demo_mode": True,
        }

    from app.rag.embedder import EmbeddingProvider

    embedder = EmbeddingProvider()
    vector = await embedder.embed_query(query)
    sparse = pipeline.qdrant._build_sparse_vector(query)

    levels = ["public", "internal", "confidential"]

    pgvec_results = await pipeline.pgvector.similarity_search(
        query_vector=vector, session=session, classification_levels=levels, top_k=10
    )
    qdrant_results = await pipeline.qdrant.hybrid_search(
        query_dense=vector, query_sparse=sparse,
        classification_filter=levels, top_k=10,
    )

    pgvec_ids = {r.chunk_id: r for r in pgvec_results}
    qdrant_ids = {r.chunk_id: r for r in qdrant_results}

    from app.rag.fusion import reciprocal_rank_fusion
    fused = reciprocal_rank_fusion(pgvec_results, qdrant_results, [])

    return {
        "query": query,
        "pgvector_only": [
            {"chunk_id": cid, "title": r.title, "score": r.similarity_score}
            for cid, r in pgvec_ids.items() if cid not in qdrant_ids
        ],
        "qdrant_only": [
            {"chunk_id": cid, "title": r.title, "score": r.score}
            for cid, r in qdrant_ids.items() if cid not in pgvec_ids
        ],
        "both": [
            {"chunk_id": cid, "title": r.title}
            for cid in set(pgvec_ids) & set(qdrant_ids)
            for r in [pgvec_ids[cid]]
        ],
        "fused_top5": [
            {
                "chunk_id": r.chunk_id,
                "title": r.title,
                "rrf_score": r.rrf_score,
                "source_paths": r.source_paths,
            }
            for r in fused[:5]
        ],
    }
