import asyncio
import hashlib
import math
import random

from app.config import settings


class EmbeddingProvider:
    """
    OpenAI text-embedding-3-small, 1536 dimensions.
    Batches to EMBEDDING_BATCH_SIZE per API call.
    Exponential backoff on RateLimitError.
    Falls back to deterministic demo vector when DEMO_MODE=true.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def _demo_vector(self, seed_text: str = "demo") -> list[float]:
        seed = int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        v = [rng.gauss(0, 1) for _ in range(settings.EMBEDDING_DIMENSIONS)]
        norm = math.sqrt(sum(x * x for x in v))
        if norm == 0:
            return [0.0] * settings.EMBEDDING_DIMENSIONS
        return [x / norm for x in v]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if settings.DEMO_MODE or not settings.OPENAI_API_KEY:
            return [self._demo_vector(t) for t in texts]

        client = self._get_client()
        results = []
        batch_size = settings.EMBEDDING_BATCH_SIZE

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for attempt in range(3):
                try:
                    response = await client.embeddings.create(
                        model=settings.EMBEDDING_MODEL,
                        input=batch,
                        dimensions=settings.EMBEDDING_DIMENSIONS,
                    )
                    batch_vectors = [item.embedding for item in response.data]
                    results.extend(batch_vectors)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 2:
                        await asyncio.sleep(2 ** attempt * 2)
                    else:
                        raise

        return results

    async def embed_query(self, query: str) -> list[float]:
        results = await self.embed_texts([query])
        return results[0]
