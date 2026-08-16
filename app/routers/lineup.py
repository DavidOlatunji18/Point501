"""Structured lineup recommendation for a team's roster + starting slots."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.team import Team
from app.schemas.lineup import LineupResponse
from app.services import lineup as lineup_service
from app.services import sleeper

router = APIRouter(prefix="/lineup", tags=["lineup"])


@router.get("", response_model=LineupResponse)
async def get_lineup(
    team_id: int = Query(...),
    week: int | None = Query(default=None, ge=1, le=22),
    season: int | None = Query(default=None, ge=2000),
    season_type: int | None = Query(
        default=None, ge=1, le=3, description="1=pre, 2=regular, 3=post; defaults to Sleeper's current season type"
    ),
    db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    if not team.players:
        raise HTTPException(status_code=400, detail=f"Team {team_id} has no players on its roster")

    week, season, season_type = await sleeper.resolve_current_week(week, season, season_type)

    try:
        return await lineup_service.recommend_lineup(team, week, season, season_type)
    except lineup_service.LineupGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
