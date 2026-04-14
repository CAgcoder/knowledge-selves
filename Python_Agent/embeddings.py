"""
embeddings.py — BGE-M3 自定义 ChromaDB EmbeddingFunction
实现 ChromaDB 的 EmbeddingFunction 接口，底层用 sentence-transformers 加载 BAAI/bge-m3。
"""

import logging
from typing import Union

import chromadb.api.types as chroma_types
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class BGEM3EmbeddingFunction(chroma_types.EmbeddingFunction[chroma_types.Documents]):
    """ChromaDB embedding function adapter for BAAI/bge-m3."""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        logger.info("加载 embedding 模型: %s (首次运行会自动下载)", model_name)
        self._model = SentenceTransformer(model_name)
        logger.info("Embedding 模型加载完成")

    def __call__(
        self, input: chroma_types.Documents
    ) -> chroma_types.Embeddings:
        embeddings = self._model.encode(
            input,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()
