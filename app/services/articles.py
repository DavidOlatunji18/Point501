"""Ingests fantasy news/analysis articles: chunk -> embed -> store in Chroma,
with lightweight metadata (title/source/hash) kept in SQLite for listing,
deletion, and duplicate detection."""

import hashlib

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.article import Article
from app.services import vector_store
from app.services.chunking import chunk_text


class DuplicateArticleError(Exception):
    """Raised when the exact same article content has already been ingested."""


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def ingest_article(db: Session, title: str, content: str, source: str | None = None) -> Article:
    content_hash = _hash_content(content)
    existing = db.query(Article).filter_by(content_hash=content_hash).first()
    if existing is not None:
        raise DuplicateArticleError(
            f"Article '{existing.title}' (id={existing.id}) already ingested"
        )

    chunks = chunk_text(content)
    if not chunks:
        raise ValueError("No content to ingest after chunking")

    article = Article(
        title=title, source=source, content_hash=content_hash, num_chunks=len(chunks)
    )
    db.add(article)
    db.flush()  # assigns article.id without committing yet
    article_id = article.id

    metadatas = [
        {
            "article_id": article_id,
            "title": title,
            "source": source or "",
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]
    vector_store.add_chunks(article_id, chunks, metadatas)

    try:
        db.commit()
    except IntegrityError:
        # Lost a race against a concurrent identical-content ingest: undo the
        # chunks we just wrote so they don't become orphaned in the vector store.
        db.rollback()
        vector_store.delete_article_chunks(article_id)
        winner = db.query(Article).filter_by(content_hash=content_hash).first()
        detail = f" (id={winner.id})" if winner else ""
        raise DuplicateArticleError(f"Article '{title}'{detail} already ingested") from None

    db.refresh(article)
    return article


def delete_article(db: Session, article: Article) -> None:
    vector_store.delete_article_chunks(article.id)
    db.delete(article)
    db.commit()


def search_articles(query: str, limit: int = 5) -> list[dict]:
    return vector_store.query(query, n_results=limit)
