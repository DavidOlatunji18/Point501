from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    team_id: int | None = None


class ChatSource(BaseModel):
    title: str
    source: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
