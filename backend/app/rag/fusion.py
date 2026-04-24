from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FusedResult:
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
    source_paths: list[str] = field(default_factory=list)


def reciprocal_rank_fusion(
    pgvector_results: list,
    qdrant_dense_results: list,
    qdrant_sparse_results: list,
    k: int = 60,
) -> list[FusedResult]:
    """
    RRF formula: score(d) = Σ 1/(k + rank_i(d)) across all paths.
    k=60 is the established standard.
    """
    scores: dict[str, dict] = {}

    def add_results(results: list, path_name: str, rank_field: str) -> None:
        for rank, result in enumerate(results, start=1):
            cid = str(result.chunk_id)
            if cid not in scores:
                scores[cid] = {
                    "chunk_id": cid,
                    "document_id": str(result.document_id),
                    "text": result.text,
                    "title": result.title,
                    "category": result.category,
                    "classification": result.classification,
                    "chunk_index": result.chunk_index,
                    "token_count": result.token_count,
                    "rrf_score": 0.0,
                    "pgvector_rank": None,
                    "qdrant_dense_rank": None,
                    "qdrant_sparse_rank": None,
                    "source_paths": [],
                }
            scores[cid]["rrf_score"] += 1.0 / (k + rank)
            if scores[cid][rank_field] is None:
                scores[cid][rank_field] = rank
            if path_name not in scores[cid]["source_paths"]:
                scores[cid]["source_paths"].append(path_name)

    add_results(pgvector_results, "pgvector", "pgvector_rank")
    add_results(qdrant_dense_results, "qdrant_dense", "qdrant_dense_rank")
    add_results(qdrant_sparse_results, "qdrant_sparse", "qdrant_sparse_rank")

    fused = [FusedResult(**v) for v in scores.values()]
    return sorted(fused, key=lambda r: r.rrf_score, reverse=True)
