from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    team_id: int | None = None
