from dataclasses import dataclass

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


@dataclass
class ChunkResult:
    text: str
    token_count: int
    start_char: int
    end_char: int
    metadata: dict


class TokenAwareChunker:
    """
    RecursiveCharacterTextSplitter with tiktoken length function.
    chunk_overlap = 50 tokens (hard spec).
    Separator hierarchy ensures semantic coherence: paragraph > sentence > clause > word > char.
    """

    def __init__(self):
        self.enc = tiktoken.get_encoding("cl100k_base")
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE_TOKENS,
            chunk_overlap=50,
            length_function=lambda t: len(self.enc.encode(t)),
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            keep_separator=True,
            add_start_index=True,
        )

    def chunk_document(self, text: str, metadata: dict | None = None) -> list[ChunkResult]:
        docs = self.splitter.create_documents([text], metadatas=[metadata or {}])
        results = []
        for i, doc in enumerate(docs):
            start = doc.metadata.get("start_index", 0)
            end = start + len(doc.page_content)
            results.append(
                ChunkResult(
                    text=doc.page_content,
                    token_count=len(self.enc.encode(doc.page_content)),
                    start_char=start,
                    end_char=end,
                    metadata={**doc.metadata, "chunk_index": i},
                )
            )
        return results
