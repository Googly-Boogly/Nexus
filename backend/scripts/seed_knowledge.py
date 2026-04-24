#!/usr/bin/env python3
"""Ingest all sample_data/documents into the knowledge base."""
import asyncio
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.rag.pipeline import RAGPipeline

CATEGORY_MAP = {
    "runbooks": ("runbook", "internal"),
    "compliance": ("compliance", "confidential"),
    "infrastructure": ("infrastructure", "internal"),
    "general": ("general", "public"),
}

DOCS_ROOT = Path("/app/sample_data/documents")


async def get_admin_user_id(session):
    from sqlalchemy import select
    from app.models.user import User
    result = await session.execute(select(User).where(User.username == "admin"))
    user = result.scalar_one_or_none()
    if not user:
        from app.core.security import hash_password
        user = User(
            username="admin",
            email="admin@nexus.demo",
            hashed_password=hash_password("Admin123!"),
            role="admin",
            data_clearance="confidential",
        )
        session.add(user)
        await session.flush()
    return user.id


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    pipeline = RAGPipeline()

    total_docs = 0
    total_chunks = 0
    total_tokens = 0
    total_qdrant = 0
    total_pgvec = 0

    print("\n📚 Ingesting knowledge base documents...\n")
    print(f"{'Filename':<45} {'Chunks':>7} {'Tokens':>8} {'Status':>10}")
    print("─" * 75)

    async with factory() as session:
        admin_id = await get_admin_user_id(session)

        for subdir, (category, classification) in CATEGORY_MAP.items():
            doc_dir = DOCS_ROOT / subdir
            if not doc_dir.exists():
                print(f"  [WARNING] Directory not found: {doc_dir}")
                continue

            for md_file in sorted(doc_dir.glob("*.md")):
                title = md_file.stem.replace("_", " ").title()
                try:
                    text = md_file.read_text(encoding="utf-8")
                    result = await pipeline.ingest_document(
                        file_text=text,
                        title=title,
                        category=category,
                        classification=classification,
                        uploaded_by=admin_id,
                        session=session,
                    )
                    await session.commit()
                    print(f"  {md_file.name:<43} {result.chunk_count:>7} {result.token_count:>8}    ✓")
                    total_docs += 1
                    total_chunks += result.chunk_count
                    total_tokens += result.token_count
                    total_qdrant += result.qdrant_upserted
                    total_pgvec += result.pgvector_upserted
                except Exception as e:
                    print(f"  {md_file.name:<43} {'':>7} {'':>8}  ✗ {e}")

    await engine.dispose()

    print("─" * 75)
    print(f"\n✓ Summary:")
    print(f"  Documents:    {total_docs}")
    print(f"  Chunks:       {total_chunks}")
    print(f"  Tokens:       {total_tokens:,}")
    print(f"  Qdrant pts:   {total_qdrant}")
    print(f"  pgvector rows: {total_pgvec}\n")


if __name__ == "__main__":
    asyncio.run(seed())
