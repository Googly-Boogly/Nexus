import { useState } from 'react'
import {
  Card, SectionHeader, Button, Input, Badge, Select, EmptyState, Spinner,
} from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { MOCK_DOCUMENTS, MOCK_STATS } from '../mocks/data'
import type { KnowledgeDocument, KnowledgeSearchResult, RagPathComparison } from '../types'
import { searchKnowledge, compareRagPaths } from '../api/client'

const CATEGORY_OPTIONS = [
  { value: 'all', label: 'All Categories' },
  { value: 'runbooks', label: 'Runbooks' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'infrastructure', label: 'Infrastructure' },
  { value: 'general', label: 'General' },
]

const MOCK_SEARCH_RESULTS: KnowledgeSearchResult[] = [
  {
    chunk_id: 'c1', document_id: 'd7', document_title: 'Escalation Matrix',
    category: 'general', score: 0.94, rrf_score: 0.031, rerank_score: 0.87,
    source_paths: ['pgvector', 'qdrant_dense'],
    text: 'P1: T+0 L1 acknowledges. T+5 min: if not acknowledged → PagerDuty auto-escalates to L2. T+15 min: L1 must identify root cause or escalate. T+30 min: L2 escalates to L3 if not contained.',
  },
  {
    chunk_id: 'c2', document_id: 'd8', document_title: 'On-Call Procedures',
    category: 'general', score: 0.88, rrf_score: 0.028, rerank_score: 0.79,
    source_paths: ['pgvector'],
    text: 'All on-call engineers must acknowledge PagerDuty page within 5 minutes. Begin investigation within 15 minutes. Post initial update in incident channel within 10 minutes of acknowledgement.',
  },
  {
    chunk_id: 'c3', document_id: 'd1', document_title: 'Incident Response Runbook',
    category: 'runbooks', score: 0.82, rrf_score: 0.024, rerank_score: 0.71,
    source_paths: ['qdrant_dense', 'qdrant_sparse'],
    text: 'Step 1: Acknowledge and assess scope. Determine P1/P2/P3 classification. For P1: immediately page secondary on-call, create Zoom bridge, post in #incidents. Customer-facing status update at T+2 hours.',
  },
]

const SOURCE_PATH_VARIANT = (p: string): 'info' | 'success' | 'warning' => {
  if (p === 'pgvector') return 'info'
  if (p === 'qdrant_dense') return 'success'
  return 'warning'
}

export default function KnowledgeBase() {
  const { isDemoMode } = useAuth()
  const [tab, setTab] = useState<'search' | 'documents' | 'compare'>('search')
  const [query, setQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<KnowledgeSearchResult[] | null>(null)
  const [compareResult, setCompareResult] = useState<RagPathComparison | null>(null)
  const [comparing, setComparing] = useState(false)

  const docs = categoryFilter === 'all'
    ? MOCK_DOCUMENTS
    : MOCK_DOCUMENTS.filter((d) => d.category === categoryFilter)

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    if (isDemoMode) {
      await new Promise((r) => setTimeout(r, 600))
      setResults(MOCK_SEARCH_RESULTS)
    } else {
      try {
        const res = await searchKnowledge({ query, top_k: 8 })
        setResults(res.data)
      } catch {
        setResults([])
      }
    }
    setSearching(false)
  }

  const handleCompare = async () => {
    if (!query.trim()) return
    setComparing(true)
    if (isDemoMode) {
      await new Promise((r) => setTimeout(r, 800))
      setCompareResult({
        query,
        pgvector_results: MOCK_SEARCH_RESULTS.filter((r) => r.source_paths.includes('pgvector')),
        qdrant_dense_results: MOCK_SEARCH_RESULTS.filter((r) => r.source_paths.includes('qdrant_dense')),
        qdrant_sparse_results: MOCK_SEARCH_RESULTS.filter((r) => r.source_paths.includes('qdrant_sparse')),
        fused_results: MOCK_SEARCH_RESULTS,
        stats: { pgvector_latency_ms: 12, qdrant_latency_ms: 18, rerank_latency_ms: 45, total_latency_ms: 75 },
      })
    } else {
      try {
        const res = await compareRagPaths(query)
        setCompareResult(res.data)
      } catch {
        setCompareResult(null)
      }
    }
    setComparing(false)
  }

  return (
    <div>
      <SectionHeader
        title="◉ KNOWLEDGE BASE"
        subtitle={`${MOCK_STATS.total_documents} documents · ${MOCK_STATS.total_chunks} chunks · pgvector + Qdrant hybrid RAG`}
      />

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        {Object.entries(MOCK_STATS.documents_by_category).map(([cat, count]) => (
          <Card key={cat} className="text-center">
            <div className="text-xl font-mono font-bold text-cyan">{count}</div>
            <div className="text-text-muted text-xs mt-1 capitalize">{cat}</div>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-border">
        {(['search', 'documents', 'compare'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-mono capitalize transition-colors
              ${tab === t ? 'text-cyan border-b-2 border-cyan' : 'text-text-secondary hover:text-text-primary'}`}
          >
            {t === 'compare' ? 'PATH COMPARE' : t.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Search tab */}
      {tab === 'search' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={query}
              onChange={setQuery}
              placeholder="e.g. How do I escalate a P1 incident?"
              className="flex-1"
            />
            <Button onClick={handleSearch} disabled={searching || !query.trim()}>
              {searching ? <Spinner size="sm" /> : 'SEARCH'}
            </Button>
          </div>

          {results === null && (
            <div className="text-text-muted text-xs font-mono py-8 text-center">
              Search the knowledge base using hybrid pgvector + Qdrant retrieval
            </div>
          )}

          {results !== null && results.length === 0 && <EmptyState message="No results found" />}

          {results !== null && results.length > 0 && (
            <div className="space-y-3">
              <p className="text-text-muted text-xs font-mono">{results.length} RESULTS</p>
              {results.map((r) => (
                <Card key={r.chunk_id}>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <span className="text-cyan text-sm font-mono">{r.document_title}</span>
                      <span className="text-text-muted text-xs ml-2">· {r.category}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-green text-xs font-mono">{(r.score * 100).toFixed(0)}%</span>
                      {r.rerank_score !== null && (
                        <span className="text-text-muted text-xs font-mono">
                          rerank: {r.rerank_score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-text-secondary text-sm leading-relaxed">{r.text}</p>
                  <div className="flex gap-1.5 mt-3">
                    {r.source_paths.map((p) => (
                      <Badge key={p} variant={SOURCE_PATH_VARIANT(p)}>
                        {p}
                      </Badge>
                    ))}
                    <span className="text-text-muted text-xs font-mono ml-auto">
                      rrf: {r.rrf_score.toFixed(4)}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Documents tab */}
      {tab === 'documents' && (
        <div className="space-y-4">
          <Select
            value={categoryFilter}
            onChange={setCategoryFilter}
            options={CATEGORY_OPTIONS}
            className="w-48"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {docs.map((doc: KnowledgeDocument) => (
              <Card key={doc.id} className="hover:border-cyan/30 transition-colors">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="text-text-primary text-sm font-medium">{doc.title}</h3>
                  <Badge variant="muted">{doc.category}</Badge>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs mt-3">
                  <div>
                    <span className="text-text-muted font-mono block">CHUNKS</span>
                    <span className="text-cyan font-mono">{doc.chunk_count}</span>
                  </div>
                  <div>
                    <span className="text-text-muted font-mono block">TOKENS</span>
                    <span className="text-text-secondary font-mono">{doc.token_count.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-text-muted font-mono block">CLEARANCE</span>
                    <Badge variant={
                      doc.clearance_level === 'public' ? 'muted' :
                      doc.clearance_level === 'internal' ? 'info' :
                      doc.clearance_level === 'confidential' ? 'warning' : 'danger'
                    }>
                      {doc.clearance_level}
                    </Badge>
                  </div>
                </div>
                <p className="text-text-muted text-xs font-mono mt-2">{doc.source_path}</p>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Compare tab */}
      {tab === 'compare' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={query}
              onChange={setQuery}
              placeholder="Query to compare across RAG paths..."
              className="flex-1"
            />
            <Button onClick={handleCompare} disabled={comparing || !query.trim()} variant="secondary">
              {comparing ? <Spinner size="sm" /> : 'COMPARE PATHS'}
            </Button>
          </div>

          {!compareResult && (
            <Card className="text-center py-10">
              <p className="text-text-muted text-xs font-mono">
                Compare pgvector (SQL cosine) vs Qdrant dense vs Qdrant sparse retrieval paths.
                Results are fused via Reciprocal Rank Fusion (k=60) then reranked.
              </p>
            </Card>
          )}

          {compareResult && (
            <div className="space-y-4">
              {/* Latency stats */}
              <Card>
                <h2 className="text-text-secondary text-xs font-mono mb-3">LATENCY BREAKDOWN</h2>
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: 'pgvector', ms: compareResult.stats.pgvector_latency_ms, color: 'text-cyan' },
                    { label: 'Qdrant', ms: compareResult.stats.qdrant_latency_ms, color: 'text-green' },
                    { label: 'Reranker', ms: compareResult.stats.rerank_latency_ms, color: 'text-amber' },
                    { label: 'Total', ms: compareResult.stats.total_latency_ms, color: 'text-text-primary' },
                  ].map((s) => (
                    <div key={s.label} className="text-center">
                      <div className={`text-xl font-mono font-bold ${s.color}`}>{s.ms}ms</div>
                      <div className="text-text-muted text-xs">{s.label}</div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Path results */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { label: 'pgvector (HNSW cosine)', results: compareResult.pgvector_results, color: 'text-cyan', badge: 'info' as const },
                  { label: 'Qdrant Dense', results: compareResult.qdrant_dense_results, color: 'text-green', badge: 'success' as const },
                  { label: 'Qdrant Sparse (BM25)', results: compareResult.qdrant_sparse_results, color: 'text-amber', badge: 'warning' as const },
                ].map((path) => (
                  <Card key={path.label}>
                    <h3 className={`text-xs font-mono mb-3 ${path.color}`}>{path.label}</h3>
                    <div className="space-y-2">
                      {path.results.length === 0 && (
                        <p className="text-text-muted text-xs font-mono">No results</p>
                      )}
                      {path.results.map((r, i) => (
                        <div key={r.chunk_id} className="flex items-start gap-2">
                          <span className="text-text-muted text-xs font-mono flex-shrink-0">#{i + 1}</span>
                          <div className="min-w-0">
                            <p className="text-text-primary text-xs truncate">{r.document_title}</p>
                            <p className={`text-xs font-mono ${path.color}`}>
                              {(r.score * 100).toFixed(0)}%
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>

              {/* Fused results */}
              <Card>
                <h2 className="text-text-secondary text-xs font-mono mb-3">
                  FUSED + RERANKED (RRF k=60)
                </h2>
                <div className="space-y-2">
                  {compareResult.fused_results.map((r, i) => (
                    <div key={r.chunk_id} className="flex items-center gap-3 py-1.5 border-b border-border/30">
                      <span className="text-text-muted font-mono text-sm w-6">#{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <span className="text-text-primary text-sm">{r.document_title}</span>
                        <p className="text-text-muted text-xs truncate">{r.text.slice(0, 80)}...</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {r.source_paths.map((p) => (
                          <Badge key={p} variant={SOURCE_PATH_VARIANT(p)}>{p.replace('_', ' ')}</Badge>
                        ))}
                        <span className="text-text-secondary text-xs font-mono">
                          rrf: {r.rrf_score.toFixed(4)}
                        </span>
                        {r.rerank_score !== null && (
                          <span className="text-green text-xs font-mono">
                            re: {r.rerank_score.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
