"""Single flexible /chat endpoint - natural-language Q&A grounded in roster,
live stats/schedule, and ingested articles. No separate endpoints per
question type (start/sit, waivers, trades, strategy) - the model decides
what data it needs via tool calls.

Streams the answer back as Server-Sent Events as it's generated, instead of
waiting for the full response - the model can take several seconds just to
write out the final answer, and that's dead air for the user otherwise."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.team import Team
from app.schemas.chat import ChatRequest
from app.services import chat as chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    team = None
    if payload.team_id is not None:
        # Eagerly load players here, while the request's db session is still
        # open - the streaming response below finishes generating (and
        # touches team.players) after this handler has already returned, by
        # which point the session dependency has closed and a lazy load
        # would raise DetachedInstanceError.
        team = db.get(Team, payload.team_id, options=[selectinload(Team.players)])
        if team is None:
            raise HTTPException(status_code=404, detail=f"Team {payload.team_id} not found")

    async def event_stream():
        async for event in chat_service.stream_answer(payload.message, team):
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
