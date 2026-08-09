from pydantic import BaseModel


class ArticleCreate(BaseModel):
    title: str
    content: str
    source: str | None = None


class ArticleOut(BaseModel):
    id: int
    title: str
    source: str | None
    num_chunks: int

    model_config = {"from_attributes": True}


class ArticleSearchResult(BaseModel):
    chunk_id: str
    text: str
    distance: float
    article_id: int
    title: str
    source: str
    chunk_index: int
