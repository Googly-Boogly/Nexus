I built a production-grade multi-agent AI platform from scratch — with a full security layer — and I'm looking for my next role in AI security or AI engineering.

Here's what NEXUS does and why it was a serious engineering challenge:

**The platform** routes incoming tasks to specialist AI agents (incident response, infrastructure provisioning, compliance scanning) that run an agentic loop against real tools, with live streaming output to a React dashboard.

**The part I'm most proud of — the security pipeline every request passes through before the LLM ever sees it:**

→ Static regex defense + LLM classifier (Haiku) to catch prompt injection and jailbreak attempts
→ OPA (Open Policy Agent) for role-based authorization with per-agent action enforcement
→ Data clearance levels (public / internal / confidential) gating access to each agent
→ PII redaction (SSN, credit cards, AWS keys, private keys) before input reaches the model
→ Tool result scanning to block indirect prompt injection from external data sources
→ Constitutional AI self-check on every output before it's returned to the user
→ Approval workflow for critical/high-priority tasks — P1/P2 tasks queue for admin review before execution
→ Immutable audit log capturing the full agent decision tree: every security gate, LLM iteration, tool call, and RAG retrieval — persisted independently so failures are always traceable

**The RAG pipeline is dual-path:**
pgvector HNSW cosine similarity runs in parallel with Qdrant hybrid dense+sparse search, fused via Reciprocal Rank Fusion, then re-ranked with a CrossEncoder — with a RAG defense layer to catch poisoned retrieval results before they reach the model.

**Stack:** FastAPI · Celery · Redis pub/sub · PostgreSQL (pgvector) · Qdrant · OPA · Anthropic + OpenAI with automatic failover · React 18 + TypeScript · Docker

This was a deep dive into what it actually takes to run AI agents safely in a production environment — not just prompting, but authorization, observability, data governance, and adversarial defense.

I'm actively looking for roles in **AI security** or **AI engineering** where I can work on problems like this.

If you're building something in this space, I'd love to connect.

#AIEngineering #AISecurity #LLM #MultiAgent #RAG #PromptInjection #OpenToWork
