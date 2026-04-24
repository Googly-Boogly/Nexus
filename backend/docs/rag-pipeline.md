# RAG Pipeline

NEXUS uses a dual-database hybrid RAG pipeline that runs two independent retrieval paths concurrently, fuses their results via Reciprocal Rank Fusion, and reranks the top candidates with a cross-encoder.

## Components

```
rag/
├── chunker.py       TokenAwareChunker — splits text into ~512-token chunks
├── embedder.py      EmbeddingProvider — OpenAI text-embedding-3-small (1536 dims)
├── pgvector_store.py PGVectorStore — cosine similarity via HNSW index
├── qdrant_store.py  QdrantStore — dense + sparse (BM25) hybrid search
├── retriever.py     HybridRetriever — orchestrates both paths concurrently
├── fusion.py        reciprocal_rank_fusion — merges ranked lists
├── reranker.py      CrossEncoderReranker — ms-marco-MiniLM-L-6-v2
├── rag_defense.py   RAGDefenseLayer — injection detection, classification enforcement
└── pipeline.py      RAGPipeline — ingest and retrieve orchestrators
```

---

## Ingest Flow

```
raw text
  → TokenAwareChunker.chunk_document()
      RecursiveCharacterTextSplitter, cl100k_base tokenizer
      chunk_size=512 tokens, overlap=50 tokens
      separators: ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]
  → RAGDefenseLayer.check_chunks_at_ingest()   ← rejects poisoned content
  → EmbeddingProvider.embed_texts(chunks)      ← batch of up to 100, L2-normalized
  → KnowledgeDocument row inserted             ← pgvector via SQLAlchemy ORM
  → KnowledgeChunk rows inserted               ← VECTOR(1536) column
  → QdrantStore.upsert_points()                ← dense + sparse vectors
```

All chunks are written to **both** stores. The pgvector `embedding` column stores the same 1536-dim unit vector written to Qdrant's `dense` named vector.

### DEMO_MODE ingest
`EmbeddingProvider` returns deterministic hash-seeded unit vectors (no OpenAI call). Zero vectors are stored in pgvector; unit vectors go to Qdrant's in-memory mock.

---

## Retrieval Flow

```
query string
  → RAGDefenseLayer.sanitize_query()    ← length check, strip HTML/code, injection check
  → EmbeddingProvider.embed_query()     ← single-vector embed
  → QdrantStore._build_sparse_vector()  ← BM25 tokenization (synchronous)
  ↓                                           ↓
  PGVectorStore.similarity_search()      QdrantStore.hybrid_search()
  (HNSW cosine via .cosine_distance())   (dense search + sparse search via asyncio.gather)
  SET LOCAL hnsw.ef_search = 64
  ↓                                           ↓
  ←────── asyncio.gather ──────────────────────→
  ↓
  reciprocal_rank_fusion(pgvector, qdrant_dense, qdrant_sparse, k=60)
  ↓
  CrossEncoderReranker.rerank(query, fused, top_n=4)
  ↓
  RAGDefenseLayer.check_retrieved_chunks()     ← quarantine injected chunks
  RAGDefenseLayer.enforce_relevance_gate()     ← drop cross_score < 0.65
  RAGDefenseLayer.enforce_classification()     ← drop chunks above user clearance
  ↓
  RAGContext(formatted_block, sources, stats, was_retrieved)
```

### Agent Category Filtering

`RAGPipeline.retrieve_for_agent()` maps the calling agent type to a document category:

| Agent type | Category filter |
|---|---|
| `incident_response` | `runbook` |
| `compliance_scan` | `compliance` |
| `infrastructure_provisioning` | `infrastructure` |

---

## pgvector Store (`pgvector_store.py`)

Uses SQLAlchemy ORM only — zero raw f-string SQL.

**Similarity search** runs `SET LOCAL hnsw.ef_search = 64` before the query, then uses `.cosine_distance()` on the `VECTOR(1536)` mapped column. Results ordered by distance ASC; similarity score = `1.0 - distance`.

**Full-text search** uses PostgreSQL `plainto_tsquery` + `to_tsvector` + `ts_rank_cd` — ranked by relevance DESC.

**Metadata search** filters by category, classification, date range, and title substring (`ILIKE`).

**SQLite guard**: All methods return `[]` immediately when `"sqlite" in settings.DATABASE_URL` since pgvector operations are PostgreSQL-only.

---

## Qdrant Store (`qdrant_store.py`)

**Collection schema**:
```python
vectors_config = {
    "dense": VectorParams(size=1536, distance=Distance.COSINE)
}
sparse_vectors_config = {
    "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
}
```

**Hybrid search** fires `client.search()` for the `dense` named vector and `client.search()` with a `NamedSparseVector` for `sparse` — both concurrently via `asyncio.gather`. Results from both passes are concatenated and returned together.

**Sparse vector construction** (`_build_sparse_vector`): lowercases and strips punctuation from the text, removes stop words, hashes each token with `hash(token) % 30000` to produce an index, computes TF as the normalized term frequency, and returns a `SparseVector(indices, values)`.

**Fallback**: When `QDRANT_URL` is empty (tests, demo without Qdrant), all operations fall back to an in-memory `_mock_points` list.

---

## Reciprocal Rank Fusion (`fusion.py`)

Standard RRF with `k=60`:

```
score(chunk) = Σ  1 / (60 + rank_i)
               i ∈ {pgvector, qdrant_dense, qdrant_sparse}
```

Chunks appearing in multiple paths accumulate score from each. The `source_paths` list on each `FusedResult` records which paths returned that chunk.

---

## Cross-Encoder Reranker (`reranker.py`)

Singleton (`CrossEncoderReranker.get()`). Lazily loads `cross-encoder/ms-marco-MiniLM-L-6-v2` from `sentence_transformers`.

In `DEMO_MODE` or when the model fails to load: falls back to sorting by `rrf_score`.

Takes the fused candidates and returns up to `RAG_RERANK_TOP_N` (default 4) `RerankedResult` objects with a `cross_score` field added.

---

## RAG Defense Layer (`rag_defense.py`)

### At ingest
`check_chunks_at_ingest()` scans each chunk for 11 injection patterns (override instructions, system tags, Llama-style control tokens, etc.). Any match raises `PoisonedDocumentError` with the chunk index and pattern — the route handler returns HTTP 422.

### At retrieval
1. **`sanitize_query()`** — strips HTML/code blocks, checks the query against the same `INJECTION_PATTERNS` list used by `PromptDefenseLayer`. Raises `ValueError` on match (caught by `BaseAgent.run()` and returned as an error result).
2. **`check_retrieved_chunks()`** — re-scans each retrieved chunk. Quarantined chunks are dropped. If ≥2 chunks from the same document are quarantined, `KnowledgeDocument.poisoning_suspected` is set to `True`.
3. **`enforce_relevance_gate()`** — drops chunks with `cross_score < RAG_MIN_SCORE` (default 0.65).
4. **`enforce_classification()`** — drops chunks whose `data_classification` exceeds the user's clearance level.

### Context block format
`format_context_block()` produces a structured plain-text block prepended to the agent's system prompt:

```
==========================================================
RETRIEVED KNOWLEDGE — cite sources explicitly in response
Retrieved: 4 chunks from 2 documents
Paths: pgvector (10) + Qdrant (8 dense, 7 sparse) → fused → reranked
==========================================================
[SOURCE 1] Incident Response Runbook | runbook | relevance: 0.91
           Paths: pgvector, qdrant_dense | chunk 3
<chunk text>
...
==========================================================
END RETRIEVED KNOWLEDGE
```

---

## RetrievalStats

Every retrieval returns a `RetrievalStats` dataclass tracking counts at each pipeline stage:

| Field | Meaning |
|---|---|
| `pgvector_results` | Hits from pgvector before fusion |
| `qdrant_dense_results` | Hits from Qdrant dense search |
| `qdrant_sparse_results` | Hits from Qdrant sparse search |
| `after_fusion` | Unique chunks after RRF |
| `after_rerank` | Chunks after cross-encoder (top N) |
| `after_relevance_gate` | After dropping low-score chunks |
| `quarantined_by_defense` | Chunks dropped by injection detection |
| `filtered_by_classification` | Chunks dropped for clearance mismatch |
| `query_time_ms` | Wall-clock time for the full retrieval |
