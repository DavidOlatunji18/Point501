"""Single flexible /chat endpoint - natural-language Q&A grounded in roster,
live stats/schedule, and ingested articles. No separate endpoints per
question type (start/sit, waivers, trades, strategy) - the model decides
what data it needs via tool calls."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.team import Team
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat as chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    team = None
    if payload.team_id is not None:
        team = db.get(Team, payload.team_id)
        if team is None:
            raise HTTPException(status_code=404, detail=f"Team {payload.team_id} not found")

    return await chat_service.answer_question(payload.message, team)
