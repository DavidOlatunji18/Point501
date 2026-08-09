"""Chroma-backed vector store for ingested fantasy news/analysis articles.

Embeddings come from a local sentence-transformers model (no external API
key or per-call cost). Swappable later - everything outside this module
talks to it only through add_chunks/delete_article_chunks/query.
"""

from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import get_settings

_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_COLLECTION_NAME = "articles"

_client: chromadb.ClientAPI | None = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=_EMBEDDING_MODEL_NAME
        )
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME, embedding_function=embedding_fn
        )
    return _collection


def add_chunks(article_id: int, chunks: list[str], metadatas: list[dict[str, Any]]) -> None:
    collection = _get_collection()
    ids = [f"article-{article_id}-chunk-{i}" for i in range(len(chunks))]
    collection.add(ids=ids, documents=chunks, metadatas=metadatas)


def delete_article_chunks(article_id: int) -> None:
    collection = _get_collection()
    collection.delete(where={"article_id": article_id})


def query(query_text: str, n_results: int = 5) -> list[dict[str, Any]]:
    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []

    result = collection.query(query_texts=[query_text], n_results=min(n_results, count))
    ids = result["ids"][0]
    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    return [
        {"chunk_id": ids[i], "text": documents[i], "distance": distances[i], **metadatas[i]}
        for i in range(len(ids))
    ]
