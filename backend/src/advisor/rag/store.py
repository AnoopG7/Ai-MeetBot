from __future__ import annotations

import uuid
from typing import Any

from qdrant_client import QdrantClient, models

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    def __init__(self, url: str | None = None, collection: str | None = None) -> None:
        self.url = url or settings.qdrant_url
        self.collection_name = collection or settings.qdrant_collection
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self.url)
        return self._client

    def ensure_collection(
        self,
        dense_dim: int | None = None,
        on_disk: bool = False,
    ) -> None:
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists:
            info = self.client.get_collection(self.collection_name)
            logger.info(
                "collection already exists",
                collection=self.collection_name,
                points=info.points_count,
            )
            return

        vectors_config: dict[str, models.VectorParams] = {
            "dense": models.VectorParams(
                size=dense_dim or settings.embedding_dim,
                distance=models.Distance.COSINE,
                on_disk=on_disk,
            ),
        }

        sparse_config: dict[str, models.SparseVectorParams] = {
            "bm25": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            ),
        }

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_config,
        )

        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="source",
            field_type=models.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="doc_type",
            field_type=models.PayloadSchemaType.KEYWORD,
        )

        logger.info(
            "collection created",
            collection=self.collection_name,
            dense_dim=dense_dim or settings.embedding_dim,
            sparse="bm25",
        )

    def add_documents(
        self,
        texts: list[str],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict[int, float]],
        metadata: list[dict[str, Any]],
        batch_size: int = 64,
    ) -> list[str]:
        point_ids: list[str] = []
        for i in range(0, len(texts), batch_size):
            batch_end = min(i + batch_size, len(texts))
            batch_texts = texts[i:batch_end]
            batch_dense = dense_vectors[i:batch_end]
            batch_sparse = sparse_vectors[i:batch_end]
            batch_meta = metadata[i:batch_end]

            points = []
            for j in range(len(batch_texts)):
                point_id = uuid.uuid4()
                point_ids.append(str(point_id))

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector={
                            "dense": batch_dense[j],
                            "bm25": models.SparseVector(
                                indices=list(batch_sparse[j].keys()),
                                values=list(batch_sparse[j].values()),
                            ),
                        },
                        payload={
                            "text": batch_texts[j],
                            **batch_meta[j],
                        },
                    )
                )

            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

        logger.info("documents upserted", count=len(point_ids))
        return point_ids

    def search_dense(
        self,
        vector: list[float],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[models.ScoredPoint]:
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            using="dense",
            limit=top_k or settings.rag_top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return result.points

    def search_sparse(
        self,
        sparse_vector: dict[int, float],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[models.ScoredPoint]:
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=models.SparseVector(
                indices=list(sparse_vector.keys()),
                values=list(sparse_vector.values()),
            ),
            using="bm25",
            limit=top_k or settings.rag_top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return result.points

    def search_batch(
        self,
        dense_vector: list[float],
        sparse_vector: dict[int, float],
        top_k: int | None = None,
    ) -> list[list[models.ScoredPoint]]:
        k = top_k or settings.rag_top_k
        result = self.client.query_batch_points(
            collection_name=self.collection_name,
            requests=[
                models.QueryRequest(
                    query=dense_vector,
                    using="dense",
                    limit=k,
                    with_payload=True,
                ),
                models.QueryRequest(
                    query=models.SparseVector(
                        indices=list(sparse_vector.keys()),
                        values=list(sparse_vector.values()),
                    ),
                    using="bm25",
                    limit=k,
                    with_payload=True,
                ),
            ],
        )
        return [r.points for r in result]

    def delete_collection(self) -> None:
        self.client.delete_collection(self.collection_name)
        logger.info("collection deleted", collection=self.collection_name)

    def count_points(self) -> int:
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
