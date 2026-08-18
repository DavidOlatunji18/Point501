"""Ingest fantasy news/analysis articles (paste or upload a text file) and
retrieve the most relevant chunks for a query - the retrieval half of RAG
that /chat will build on."""

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.article import Article
from app.schemas.article import ArticleCreate, ArticleOut, ArticleSearchResult
from app.services import articles as articles_service
from app.services import news_feed

router = APIRouter(prefix="/articles", tags=["articles"])


def _get_article_or_404(db: Session, article_id: int) -> Article:
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found")
    return article


@router.post("", response_model=ArticleOut, status_code=201)
def create_article(payload: ArticleCreate, db: Session = Depends(get_db)):
    try:
        return articles_service.ingest_article(
            db, title=payload.title, content=payload.content, source=payload.source
        )
    except articles_service.DuplicateArticleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload", response_model=ArticleOut, status_code=201)
async def upload_article(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    source: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    try:
        return articles_service.ingest_article(
            db, title=title or file.filename or "Untitled", content=content, source=source
        )
    except articles_service.DuplicateArticleError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/fetch-feeds")
async def fetch_feeds():
    """Manually triggers an RSS ingestion run right now, instead of waiting
    for the next scheduled one - useful for testing or an initial backfill."""
    return await asyncio.to_thread(news_feed.fetch_and_ingest_feeds)


@router.get("/search", response_model=list[ArticleSearchResult])
def search_articles(q: str = Query(min_length=2), limit: int = Query(default=5, ge=1, le=20)):
    return articles_service.search_articles(q, limit=limit)


@router.get("", response_model=list[ArticleOut])
def list_articles(db: Session = Depends(get_db)):
    return db.scalars(select(Article)).all()


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    return _get_article_or_404(db, article_id)


@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = _get_article_or_404(db, article_id)
    articles_service.delete_article(db, article)
