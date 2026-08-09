"""Read-only endpoints over ESPN's unofficial API - schedule, byes, and
weekly box-score stats, the gap Sleeper's API leaves for /lineup and /chat."""

from fastapi import APIRouter, HTTPException, Query

from app.services import espn

router = APIRouter(prefix="/espn", tags=["espn"])


@router.get("/teams")
async def read_teams():
    return await espn.get_teams()


@router.get("/schedule")
async def read_week_schedule(
    week: int = Query(ge=1, le=22),
    season: int = Query(ge=2000),
    season_type: int = Query(default=2, ge=1, le=3, description="1=pre, 2=regular, 3=post"),
):
    return await espn.get_week_schedule(week, season, season_type)


@router.get("/schedule/byes")
async def read_bye_teams(
    week: int = Query(ge=1, le=22),
    season: int = Query(ge=2000),
    season_type: int = Query(default=2, ge=1, le=3, description="1=pre, 2=regular, 3=post"),
):
    return {
        "week": week,
        "season": season,
        "bye_teams": await espn.get_bye_teams(week, season, season_type),
    }


@router.get("/games/{event_id}/boxscore")
async def read_game_boxscore(event_id: str):
    try:
        return await espn.get_game_boxscore(event_id)
    except espn.EspnNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"No ESPN box score found for event_id '{event_id}'"
        )
