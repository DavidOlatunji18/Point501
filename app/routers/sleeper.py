"""Read-only endpoints over the Sleeper API.

These exist to (a) let the roster-import flow (next phase) auto-pull a
user's leagues/rosters by username, and (b) give the /chat and /lineup
endpoints (later) a way to look up live player stats/injury status.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.services import sleeper

router = APIRouter(prefix="/sleeper", tags=["sleeper"])


@router.get("/state")
async def read_nfl_state():
    """Current NFL season/week - use this to know which week to plan for."""
    return await sleeper.get_nfl_state()


@router.get("/users/{username}")
async def read_user(username: str):
    try:
        return await sleeper.get_user(username)
    except sleeper.SleeperNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sleeper user '{username}' not found")


@router.get("/users/{user_id}/leagues")
async def read_user_leagues(user_id: str, season: str | None = Query(default=None)):
    try:
        return await sleeper.get_user_leagues(user_id, season=season)
    except sleeper.SleeperNotFoundError:
        raise HTTPException(status_code=404, detail=f"No leagues found for user_id '{user_id}'")


@router.get("/leagues/{league_id}")
async def read_league(league_id: str):
    try:
        return await sleeper.get_league(league_id)
    except sleeper.SleeperNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sleeper league '{league_id}' not found")


@router.get("/leagues/{league_id}/rosters")
async def read_league_rosters(league_id: str):
    try:
        return await sleeper.get_league_rosters(league_id)
    except sleeper.SleeperNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sleeper league '{league_id}' not found")


@router.get("/leagues/{league_id}/users")
async def read_league_users(league_id: str):
    try:
        return await sleeper.get_league_users(league_id)
    except sleeper.SleeperNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sleeper league '{league_id}' not found")


@router.get("/leagues/{league_id}/matchups/{week}")
async def read_league_matchups(league_id: str, week: int):
    try:
        return await sleeper.get_league_matchups(league_id, week)
    except sleeper.SleeperNotFoundError:
        raise HTTPException(status_code=404, detail=f"Sleeper league '{league_id}' not found")


@router.get("/players/search")
async def search_players(q: str = Query(min_length=2), limit: int = Query(default=25, ge=1, le=100)):
    """Substring search over player names, e.g. for a roster-entry autocomplete."""
    return await sleeper.search_players(q, limit=limit)


@router.get("/players/trending/{trend_type}")
async def read_trending_players(
    trend_type: Literal["add", "drop"],
    lookback_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=25, ge=1, le=100),
):
    return await sleeper.get_trending_players(trend_type, lookback_hours=lookback_hours, limit=limit)


@router.get("/players/{player_id}")
async def read_player(player_id: str):
    """Single player lookup - includes position, team, and injury_status."""
    try:
        return await sleeper.get_player(player_id)
    except sleeper.SleeperNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown Sleeper player_id '{player_id}'")
