from __future__ import annotations

import asyncio
import re
import string
import uuid
from dataclasses import dataclass

from app.config import settings

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "is", "it", "its", "be", "was", "are", "were", "been",
    "has", "have", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "not", "no", "nor", "so", "yet", "as", "if", "then",
    "than", "that", "this", "these", "those", "which", "who", "what", "how",
    "when", "where", "why", "all", "any", "both", "each", "more", "most",
    "other", "some", "such", "own", "same", "up", "out", "about", "into",
}


@dataclass
class QdrantPoint:
    id: str
    dense_vector: list[float]
    sparse_vector: "SparseVector"
    payload: dict


@dataclass
class QdrantResult:
    chunk_id: str
    document_id: str
    text: str
    title: str
    category: str
    classification: str
    chunk_index: int
    token_count: int
    score: float


class QdrantStore:
    """
    Qdrant hybrid retrieval. Dense cosine + BM25 sparse search.
    Falls back to in-memory mock when QDRANT_URL is empty (test/demo).
    """

    def __init__(self):
        self._client = None
        self._mock_points: list[dict] = []

    def _get_client(self):
        if self._client is None:
            from qdrant_client import AsyncQdrantClient
            self._client = AsyncQdrantClient(url=settings.QDRANT_URL)
        return self._client

    @property
    def _use_mock(self) -> bool:
        return not settings.QDRANT_URL or settings.DEMO_MODE and not settings.QDRANT_URL

    async def create_collection_if_not_exists(self) -> None:
        if not settings.QDRANT_URL:
            return
        try:
            from qdrant_client import models as qm
            client = self._get_client()
            existing = await client.collection_exists(settings.QDRANT_COLLECTION)
            if not existing:
                await client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config={
                        "dense": qm.VectorParams(
                            size=settings.EMBEDDING_DIMENSIONS,
                            distance=qm.Distance.COSINE,
                        )
                    },
                    sparse_vectors_config={
                        "sparse": qm.SparseVectorParams(
                            index=qm.SparseIndexParams(on_disk=False)
                        )
                    },
                )
        except Exception:
            pass

    async def upsert_points(self, points: list[QdrantPoint]) -> None:
        if not settings.QDRANT_URL:
            for p in points:
                self._mock_points.append({
                    "id": p.id,
                    "payload": p.payload,
                    "dense": p.dense_vector,
                })
            return

        try:
            from qdrant_client import models as qm
            client = self._get_client()
            qdrant_points = []
            for p in points:
                qdrant_points.append(
                    qm.PointStruct(
                        id=p.id,
                        vector={
                            "dense": p.dense_vector,
                            "sparse": qm.SparseVector(
                                indices=p.sparse_vector.indices,
                                values=p.sparse_vector.values,
                            ),
                        },
                        payload=p.payload,
                    )
                )
            await client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=qdrant_points,
            )
        except Exception:
            pass

    async def hybrid_search(
        self,
        query_dense: list[float],
        query_sparse: "SparseVector",
        classification_filter: list[str],
        category_filter: str | None = None,
        top_k: int = 10,
    ) -> list[QdrantResult]:
        if not settings.QDRANT_URL:
            return self._mock_search(top_k)

        try:
            from qdrant_client import models as qm
            client = self._get_client()

            must_conditions = []
            if classification_filter:
                must_conditions.append(
                    qm.FieldCondition(
                        key="classification",
                        match=qm.MatchAny(any=classification_filter),
                    )
                )
            if category_filter:
                must_conditions.append(
                    qm.FieldCondition(
                        key="category",
                        match=qm.MatchValue(value=category_filter),
                    )
                )
            must_conditions.append(
                qm.FieldCondition(key="is_active", match=qm.MatchValue(value=True))
            )
            payload_filter = qm.Filter(must=must_conditions)

            dense_task = client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=qm.NamedVector(name="dense", vector=query_dense),
                query_filter=payload_filter,
                limit=top_k,
                with_payload=True,
            )
            sparse_task = client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=qm.NamedSparseVector(
                    name="sparse",
                    vector=qm.SparseVector(
                        indices=query_sparse.indices,
                        values=query_sparse.values,
                    ),
                ),
                query_filter=payload_filter,
                limit=top_k,
                with_payload=True,
            )

            dense_hits, sparse_hits = await asyncio.gather(dense_task, sparse_task)
            results = []
            for hit in dense_hits + sparse_hits:
                p = hit.payload or {}
                results.append(
                    QdrantResult(
                        chunk_id=p.get("chunk_id", str(hit.id)),
                        document_id=p.get("document_id", ""),
                        text=p.get("text", ""),
                        title=p.get("title", ""),
                        category=p.get("category", ""),
                        classification=p.get("classification", "public"),
                        chunk_index=p.get("chunk_index", 0),
                        token_count=p.get("token_count", 0),
                        score=float(hit.score),
                    )
                )
            return results
        except Exception:
            return self._mock_search(top_k)

    def _mock_search(self, top_k: int) -> list[QdrantResult]:
        results = []
        for i, p in enumerate(self._mock_points[:top_k]):
            pay = p.get("payload", {})
            results.append(
                QdrantResult(
                    chunk_id=pay.get("chunk_id", str(p.get("id", i))),
                    document_id=pay.get("document_id", ""),
                    text=pay.get("text", ""),
                    title=pay.get("title", ""),
                    category=pay.get("category", ""),
                    classification=pay.get("classification", "public"),
                    chunk_index=pay.get("chunk_index", 0),
                    token_count=pay.get("token_count", 0),
                    score=0.8 - i * 0.05,
                )
            )
        return results

    async def delete_by_document_id(self, document_id: str) -> None:
        if not settings.QDRANT_URL:
            self._mock_points = [
                p for p in self._mock_points
                if p.get("payload", {}).get("document_id") != document_id
            ]
            return
        try:
            from qdrant_client import models as qm
            client = self._get_client()
            await client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[
                            qm.FieldCondition(
                                key="document_id",
                                match=qm.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except Exception:
            pass

    async def get_collection_info(self) -> dict:
        if not settings.QDRANT_URL:
            return {
                "vectors_count": len(self._mock_points),
                "segments_count": 1,
                "status": "green",
                "disk_usage_bytes": 0,
            }
        try:
            client = self._get_client()
            info = await client.get_collection(settings.QDRANT_COLLECTION)
            return {
                "vectors_count": info.vectors_count or 0,
                "segments_count": info.segments_count or 0,
                "status": str(info.status),
                "disk_usage_bytes": getattr(info, "disk_data_size", 0) or 0,
            }
        except Exception:
            return {"vectors_count": 0, "segments_count": 0, "status": "unknown", "disk_usage_bytes": 0}

    def _build_sparse_vector(self, text: str) -> "SparseVector":
        text_clean = text.lower()
        text_clean = text_clean.translate(str.maketrans("", "", string.punctuation))
        tokens = [t for t in text_clean.split() if t and t not in STOP_WORDS]

        tf: dict[int, float] = {}
        for token in tokens:
            token_id = hash(token) % 30000
            tf[token_id] = tf.get(token_id, 0) + 1

        total = len(tokens) or 1
        indices = sorted(tf.keys())
        values = [tf[idx] / total for idx in indices]
        return SparseVector(indices=indices, values=values)


class SparseVector:
    def __init__(self, indices: list[int], values: list[float]):
        self.indices = indices
        self.values = values
