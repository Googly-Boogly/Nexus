from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.rag.fusion import FusedResult


@dataclass
class RerankedResult:
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


class CrossEncoderReranker:
    """
    Lazy-loaded cross-encoder/ms-marco-MiniLM-L-6-v2.
    In DEMO_MODE: skips model load, sorts by rrf_score instead.
    """

    _instance: CrossEncoderReranker | None = None
    _model = None

    @classmethod
    def get(cls) -> CrossEncoderReranker:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self) -> None:
        if self._model is None and not settings.DEMO_MODE:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(settings.RERANKER_MODEL)
            except Exception:
                self._model = None

    def rerank(
        self,
        query: str,
        candidates: list[FusedResult],
        top_n: int | None = None,
    ) -> list[RerankedResult]:
        if top_n is None:
            top_n = settings.RAG_RERANK_TOP_N

        if not candidates:
            return []

        self._load_model()

        if self._model is None or settings.DEMO_MODE:
            sorted_cands = sorted(candidates, key=lambda c: c.rrf_score, reverse=True)
            return [
                RerankedResult(
                    **{k: v for k, v in vars(c).items()},
                    cross_score=c.rrf_score,
                )
                for c in sorted_cands[:top_n]
            ]

        pairs = [(query, c.text) for c in candidates]
        scores = self._model.predict(pairs)

        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [
            RerankedResult(
                **{k: v for k, v in vars(c).items()},
                cross_score=float(score),
            )
            for c, score in ranked[:top_n]
        ]
