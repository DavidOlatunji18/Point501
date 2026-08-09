"""Thin async client around ESPN's unofficial public NFL API.

Undocumented and can shift without notice - kept isolated behind typed
exceptions and a dedicated service module (mirroring app/services/sleeper.py)
so breakage here stays contained instead of rippling into /chat or /lineup.
Fills the schedule + weekly box-score gap Sleeper's API doesn't cover.
"""

import asyncio
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

import httpx

ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"

# ESPN and Sleeper agree on team abbreviations except Washington.
ESPN_TO_SLEEPER_TEAM_ABBR = {"WSH": "WAS"}

# ESPN's kickoff timestamps are UTC, which rolls an evening ET game onto the
# next calendar date (e.g. an 8:20pm ET Wednesday game reads as ...T00:20Z,
# i.e. after midnight Thursday UTC). Always convert to Eastern before display
# so game day/time isn't misreported.
_EASTERN_TZ = ZoneInfo("America/New_York")


def _to_eastern_iso(utc_timestamp: str) -> str:
    """ESPN timestamps look like "2026-09-10T00:20Z"."""
    dt_utc = datetime.fromisoformat(utc_timestamp.replace("Z", "+00:00"))
    return dt_utc.astimezone(_EASTERN_TZ).isoformat()

SeasonType = Literal[1, 2, 3]  # 1=preseason, 2=regular season, 3=postseason


class EspnNotFoundError(Exception):
    """Raised when ESPN returns a 404 (e.g. unknown event id)."""


class EspnAPIError(Exception):
    """Raised for any other non-2xx response, or a network-level failure."""


_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(base_url=ESPN_BASE_URL, timeout=15.0)
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        response = await get_http_client().get(path, params=params)
    except httpx.HTTPError as exc:
        raise EspnAPIError(f"Failed to reach ESPN API for {path}: {exc}") from exc
    if response.status_code == 404:
        raise EspnNotFoundError(f"ESPN resource not found: {path}")
    if response.status_code >= 400:
        raise EspnAPIError(
            f"ESPN API returned {response.status_code} for {path}: {response.text}"
        )
    return response.json()


def to_sleeper_abbr(espn_abbr: str) -> str:
    return ESPN_TO_SLEEPER_TEAM_ABBR.get(espn_abbr, espn_abbr)


async def get_teams() -> list[dict[str, Any]]:
    """All 32 NFL teams (id, abbreviation, displayName, etc)."""
    data = await _get("/teams")
    return [entry["team"] for entry in data["sports"][0]["leagues"][0]["teams"]]


async def get_scoreboard(
    week: int, season: int, season_type: SeasonType = 2
) -> dict[str, Any]:
    """Raw ESPN scoreboard for a week: games, scores, status, kickoff times.

    `season` is passed as ESPN's `dates` param, which (despite the name)
    takes a bare year here - that's what actually selects the season;
    a `year` param is silently ignored by ESPN's API.
    """
    return await _get(
        "/scoreboard",
        params={"week": week, "seasontype": season_type, "dates": season},
    )


async def get_week_schedule(
    week: int, season: int, season_type: SeasonType = 2
) -> list[dict[str, Any]]:
    """Compact per-game schedule: teams (Sleeper-style abbrs), score, status, kickoff.

    `kickoff_et` is Eastern time (what fans/broadcasts mean by "game day");
    `kickoff_utc` is kept alongside for exact chronological sorting.
    """
    scoreboard = await get_scoreboard(week, season, season_type)
    games = []
    for event in scoreboard.get("events", []):
        competition = event["competitions"][0]
        competitors = {c["homeAway"]: c for c in competition["competitors"]}
        home, away = competitors.get("home"), competitors.get("away")
        games.append(
            {
                "event_id": event["id"],
                "kickoff_et": _to_eastern_iso(event["date"]),
                "kickoff_utc": event["date"],
                "status": competition["status"]["type"]["name"],
                "home_team": to_sleeper_abbr(home["team"]["abbreviation"]) if home else None,
                "home_score": home.get("score") if home else None,
                "away_team": to_sleeper_abbr(away["team"]["abbreviation"]) if away else None,
                "away_score": away.get("score") if away else None,
            }
        )
    return games


async def get_bye_teams(week: int, season: int, season_type: SeasonType = 2) -> list[str]:
    """Teams (Sleeper-style abbrs) with no game in the given week."""
    teams, schedule = await asyncio.gather(
        get_teams(), get_week_schedule(week, season, season_type)
    )
    all_teams = {to_sleeper_abbr(t["abbreviation"]) for t in teams}
    playing = set()
    for game in schedule:
        if game["home_team"]:
            playing.add(game["home_team"])
        if game["away_team"]:
            playing.add(game["away_team"])
    return sorted(all_teams - playing)


async def get_game_boxscore(event_id: str) -> dict[str, Any]:
    """Raw ESPN box score (per-player stats by category) for a played/live game."""
    data = await _get("/summary", params={"event": event_id})
    boxscore = data.get("boxscore")
    if not boxscore:
        raise EspnNotFoundError(f"No boxscore available for event_id '{event_id}'")
    return boxscore
