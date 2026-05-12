from __future__ import annotations

from typing import Any

from ..core.config import settings
from ..core.logging import get_logger
from .embedding import DenseEmbedding, SparseEmbedding
from .store import VectorStore

logger = get_logger(__name__)


def reciprocal_rank_fusion(
    dense_results: list[Any],
    sparse_results: list[Any],
    k: int = 60,
    top_n: int | None = None,
) -> list[tuple[Any, float]]:
    scores: dict[str, tuple[Any, float]] = {}
    n = top_n or settings.rag_top_k

    for rank, point in enumerate(dense_results):
        pid = str(point.id)
        if pid in scores:
            existing = scores[pid]
            scores[pid] = (point, existing[1] + 1.0 / (k + rank))
        else:
            scores[pid] = (point, 1.0 / (k + rank))

    for rank, point in enumerate(sparse_results):
        pid = str(point.id)
        if pid in scores:
            existing = scores[pid]
            scores[pid] = (point, existing[1] + 1.0 / (k + rank))
        else:
            scores[pid] = (point, 1.0 / (k + rank))

    sorted_points = sorted(scores.values(), key=lambda x: x[1], reverse=True)
    return sorted_points[:n]


def format_context(results: list[tuple[Any, float]]) -> str:
    parts: list[str] = []
    for i, (point, score) in enumerate(results, 1):
        text = point.payload.get("text", "")
        source = point.payload.get("source", "unknown")
        parts.append(f"[{i}] (source: {source}, relevance: {score:.3f})\n{text}")

    return "\n\n".join(parts)


class FinanceRetriever:
    def __init__(
        self,
        store: VectorStore | None = None,
        dense_emb: DenseEmbedding | None = None,
        sparse_emb: SparseEmbedding | None = None,
    ) -> None:
        self.store = store or VectorStore()
        self.dense_emb = dense_emb or DenseEmbedding()
        self.sparse_emb = sparse_emb or SparseEmbedding()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[tuple[Any, float]]:
        k = top_k or settings.rag_top_k

        logger.debug("retrieving for query", query=query[:80])

        try:
            dense_vec = self.dense_emb.embed_query(query)
            sparse_vec = self.sparse_emb.embed(query)

            batch_results = self.store.search_batch(
                dense_vector=dense_vec,
                sparse_vector=sparse_vec,
                top_k=k,
            )

            dense_results = batch_results[0] if len(batch_results) > 0 else []
            sparse_results = batch_results[1] if len(batch_results) > 1 else []

            fused = reciprocal_rank_fusion(dense_results, sparse_results, top_n=k)

            logger.debug(
                "retrieval complete",
                dense_hits=len(dense_results),
                sparse_hits=len(sparse_results),
                fused=fused[0][1] if fused else 0,
            )

            return fused
        except Exception:
            logger.exception("retrieval failed", query=query[:80])
            return []

    def retrieve_formatted(
        self,
        query: str,
        top_k: int | None = None,
    ) -> str:
        results = self.retrieve(query, top_k=top_k)

        if not results:
            logger.warning("no relevant documents found", query=query[:80])
            return ""

        context = format_context(results)

        logger.info(
            "retrieved context",
            query=query[:80],
            chunks=len(results),
            chars=len(context),
        )

        return context
