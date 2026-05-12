from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.config import settings
from ..core.logging import get_logger
from .embedding import DenseEmbedding, SparseEmbedding
from .store import VectorStore

logger = get_logger(__name__)


@dataclass
class Document:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_hash: str = ""


def load_text_file(path: Path, source: str | None = None) -> list[Document]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    doc_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    return [
        Document(
            text=text,
            metadata={
                "source": source or path.name,
                "file_path": str(path),
                "doc_type": path.suffix.lstrip("."),
            },
            doc_hash=doc_hash,
        )
    ]


def load_directory(dir_path: Path, pattern: str = "*.md") -> list[Document]:
    docs: list[Document] = []
    if not dir_path.exists():
        logger.warning("knowledge directory not found", path=str(dir_path))
        return docs

    for path in sorted(dir_path.glob(pattern)):
        try:
            file_docs = load_text_file(path)
            docs.extend(file_docs)
            chars = len(file_docs[0].text) if file_docs else 0
            logger.debug("loaded file", path=str(path), chars=chars)
        except Exception:
            logger.exception("failed to load file", path=str(path))

    logger.info("loaded documents", count=len(docs), directory=str(dir_path))
    return docs


def chunk_document(
    doc: Document,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Document]:
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap
    text = doc.text

    if len(text) <= size:
        return [doc]

    chunks: list[Document] = []
    start = 0
    index = 0

    while start < len(text):
        end = start + size
        if end >= len(text):
            chunk_text = text[start:]
        else:
            last_space = text.rfind(" ", start, end)
            if last_space > start + size // 2:
                end = last_space
            chunk_text = text[start:end]

        if not chunk_text.strip():
            break

        meta = dict(doc.metadata)
        meta["chunk_index"] = index
        meta["chunk_total"] = -1

        chunks.append(
            Document(
                text=chunk_text.strip(),
                metadata=meta,
                doc_hash=doc.doc_hash,
            )
        )

        start = end - overlap
        index += 1

    for c in chunks:
        c.metadata["chunk_total"] = len(chunks)

    return chunks


def process_documents(
    docs: list[Document],
    store: VectorStore,
    dense_emb: DenseEmbedding | None = None,
    sparse_emb: SparseEmbedding | None = None,
) -> int:
    if dense_emb is None:
        dense_emb = DenseEmbedding()
    if sparse_emb is None:
        sparse_emb = SparseEmbedding()

    store.ensure_collection()

    all_chunks: list[Document] = []
    for doc in docs:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning("no chunks to process")
        return 0

    texts = [c.text for c in all_chunks]
    meta_list = [c.metadata for c in all_chunks]

    logger.info("generating embeddings", chunks=len(texts))
    dense_vectors = dense_emb.embed_passages(texts)
    sparse_vectors = sparse_emb.embed_batch(texts)

    store.add_documents(
        texts=texts,
        dense_vectors=dense_vectors,
        sparse_vectors=sparse_vectors,
        metadata=meta_list,
    )

    logger.info("ingestion complete", points=len(texts))
    return len(texts)
