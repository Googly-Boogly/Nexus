import uuid
from datetime import datetime
from pydantic import BaseModel, field_serializer


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    source_filename: str
    category: str
    data_classification: str
    chunk_count: int
    token_count: int
    embedding_model: str
    is_active: bool
    poisoning_suspected: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v: uuid.UUID) -> str:
        return str(v)


class ChunkPreview(BaseModel):
    chunk_index: int
    text_preview: str
    token_count: int


class DocumentDetail(DocumentOut):
    chunk_previews: list[ChunkPreview] = []


class SearchRequest(BaseModel):
    query: str
    category: str | None = None
    top_n: int = 10


class SearchResultOut(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    category: str
    classification: str
    chunk_index: int
    token_count: int
    text: str
    cross_score: float
    rrf_score: float
    pgvector_rank: int | None = None
    qdrant_dense_rank: int | None = None
    qdrant_sparse_rank: int | None = None
    source_paths: list[str]


class RetrievalStatsOut(BaseModel):
    pgvector_results: int
    qdrant_dense_results: int
    qdrant_sparse_results: int
    after_fusion: int
    after_rerank: int
    after_relevance_gate: int
    quarantined_by_defense: int
    filtered_by_classification: int
    query_time_ms: int


class SearchResponse(BaseModel):
    results: list[SearchResultOut]
    retrieval_stats: RetrievalStatsOut


class IngestResultOut(BaseModel):
    document_id: str
    chunk_count: int
    token_count: int
    qdrant_upserted: int
    pgvector_upserted: int
    warnings: list[str]


class KnowledgeStatsOut(BaseModel):
    total_documents: int
    total_chunks: int
    total_tokens: int
    by_category: dict
    by_classification: dict
    qdrant_vectors_count: int
    qdrant_memory_bytes: int
    recent_ingests: list[dict]
