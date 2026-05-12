from __future__ import annotations

from typing import Any

import numpy as np

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class DenseEmbedding:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model: Any = None

    def _lazy_load(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding

            logger.info("loading dense embedding model", model=self.model_name)
            self._model = TextEmbedding(
                model_name=self.model_name,
                max_length=512,
                cache_dir=None,
            )
            logger.info(
                "dense embedding model loaded",
                model=self.model_name,
                dim=settings.embedding_dim,
            )
        return self._model

    def embed_passage(self, text: str) -> list[float]:
        model = self._lazy_load()
        vec = next(model.passage_embed(text))
        return vec.tolist()  # type: ignore[no-any-return]

    def embed_query(self, text: str) -> list[float]:
        model = self._lazy_load()
        vec = next(model.query_embed(text))
        return vec.tolist()  # type: ignore[no-any-return]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        model = self._lazy_load()
        return [v.tolist() for v in model.passage_embed(texts)]

    @property
    def dimension(self) -> int:
        return settings.embedding_dim


class SparseEmbedding:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or "prithivida/Splade_PP_en_v1"
        self._model: Any = None

    def _lazy_load(self) -> Any:
        if self._model is None:
            from fastembed import SparseTextEmbedding

            logger.info("loading sparse embedding model", model=self.model_name)
            self._model = SparseTextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, text: str) -> dict[int, float]:
        model = self._lazy_load()
        result = next(model.embed(text))
        indices = result.indices.tolist()
        values = result.values.tolist()
        if isinstance(indices, np.ndarray):
            indices = indices.tolist()
        if isinstance(values, np.ndarray):
            values = values.tolist()
        return dict(zip(indices, values, strict=True))

    def embed_batch(self, texts: list[str]) -> list[dict[int, float]]:
        model = self._lazy_load()
        results = []
        for result in model.embed(texts):
            indices = result.indices.tolist()
            values = result.values.tolist()
            if isinstance(indices, np.ndarray):
                indices = indices.tolist()
            if isinstance(values, np.ndarray):
                values = values.tolist()
            results.append(dict(zip(indices, values, strict=True)))
        return results
