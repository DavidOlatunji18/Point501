"""Thin async client around the public Sleeper API (https://docs.sleeper.com).

No API key is required. The one endpoint Sleeper asks integrators to be
careful with is the full player dump (/players/nfl) - it's a multi-megabyte
payload that only changes a few times a day, so it's cached in-process with
a TTL instead of being re-fetched on every request.
"""

import asyncio
import time
from typing import Any, Literal

import httpx

from app.core.config import get_settings


class SleeperNotFoundError(Exception):
    """Raised when Sleeper returns a 404 (e.g. unknown username/league)."""


class SleeperAPIError(Exception):
    """Raised for any other non-2xx response from Sleeper."""


_PLAYERS_CACHE_TTL_SECONDS = 24 * 60 * 60  # Sleeper: fetch players at most once/day
_players_cache: dict[str, Any] = {}
_players_cache_fetched_at: float = 0.0
_players_cache_lock = asyncio.Lock()

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Shared client so requests reuse one connection pool instead of paying
    a fresh TCP/TLS handshake per call. Opened on FastAPI startup, closed on
    shutdown (see app/main.py's lifespan)."""
    global _http_client
    if _http_client is None:
        settings = get_settings()
        _http_client = httpx.AsyncClient(base_url=settings.sleeper_api_base_url, timeout=15.0)
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
        raise SleeperAPIError(f"Failed to reach Sleeper API for {path}: {exc}") from exc
    if response.status_code == 404:
        raise SleeperNotFoundError(f"Sleeper resource not found: {path}")
    if response.status_code >= 400:
        raise SleeperAPIError(
            f"Sleeper API returned {response.status_code} for {path}: {response.text}"
        )
    return response.json()


async def _get_or_404(path: str, params: dict[str, Any] | None = None) -> Any:
    """Like _get, but also treats an HTTP 200 with a `null` body as not-found.

    Sleeper is inconsistent here: an unknown username returns 200 + `null`,
    while an unknown league_id returns a real 404. Single-resource lookups
    should use this so callers get one consistent NotFound behavior.
    """
    result = await _get(path, params=params)
    if result is None:
        raise SleeperNotFoundError(f"Sleeper resource not found: {path}")
    return result


async def get_nfl_state() -> dict[str, Any]:
    """Current NFL season/week, used to know which week to plan a lineup for."""
    return await _get("/state/nfl")


_SLEEPER_SEASON_TYPE_MAP = {"pre": 1, "regular": 2, "post": 3}


def season_type_from_sleeper(value: str | None) -> int:
    """Maps Sleeper's `season_type` string (from get_nfl_state) to ESPN's
    numeric convention (1=pre, 2=regular, 3=post). Defaults to regular
    season for unrecognized values (e.g. "off")."""
    return _SLEEPER_SEASON_TYPE_MAP.get(value or "", 2)


async def get_user(username_or_id: str) -> dict[str, Any]:
    """Resolve a Sleeper username (or user_id) to a user object with user_id."""
    return await _get_or_404(f"/user/{username_or_id}")


async def get_user_leagues(user_id: str, season: str | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    season = season or settings.nfl_season
    return await _get(f"/user/{user_id}/leagues/nfl/{season}")


async def get_league(league_id: str) -> dict[str, Any]:
    """League metadata, including `roster_positions` (starting lineup slots)."""
    return await _get_or_404(f"/league/{league_id}")


async def get_league_rosters(league_id: str) -> list[dict[str, Any]]:
    return await _get_or_404(f"/league/{league_id}/rosters")


async def get_league_users(league_id: str) -> list[dict[str, Any]]:
    return await _get_or_404(f"/league/{league_id}/users")


async def get_league_matchups(league_id: str, week: int) -> list[dict[str, Any]]:
    return await _get(f"/league/{league_id}/matchups/{week}")


async def get_trending_players(
    trend_type: Literal["add", "drop"] = "add",
    lookback_hours: int = 24,
    limit: int = 25,
) -> list[dict[str, Any]]:
    return await _get(
        f"/players/nfl/trending/{trend_type}",
        params={"lookback_hours": lookback_hours, "limit": limit},
    )


async def get_all_players(force_refresh: bool = False) -> dict[str, Any]:
    """Full player_id -> player object map (name, team, position, injury_status, etc).

    Cached in-process for _PLAYERS_CACHE_TTL_SECONDS since this payload is
    several MB and Sleeper asks that it not be polled more than once a day.
    """
    global _players_cache, _players_cache_fetched_at

    now = time.monotonic()
    is_stale = (now - _players_cache_fetched_at) > _PLAYERS_CACHE_TTL_SECONDS
    if _players_cache and not is_stale and not force_refresh:
        return _players_cache

    async with _players_cache_lock:
        # Re-check after acquiring the lock in case another request refreshed it.
        now = time.monotonic()
        is_stale = (now - _players_cache_fetched_at) > _PLAYERS_CACHE_TTL_SECONDS
        if _players_cache and not is_stale and not force_refresh:
            return _players_cache

        data = await _get("/players/nfl")
        _players_cache = data
        _players_cache_fetched_at = time.monotonic()
        return _players_cache


def display_name(player: dict[str, Any]) -> str | None:
    """Most player entries have `full_name`, but team defenses (e.g. player_id
    "SF") only set first_name/last_name ("San Francisco" / "49ers")."""
    full_name = player.get("full_name")
    if full_name:
        return full_name
    first_name, last_name = player.get("first_name"), player.get("last_name")
    if first_name or last_name:
        return f"{first_name or ''} {last_name or ''}".strip()
    return None


async def search_players(query: str, limit: int = 25) -> list[dict[str, Any]]:
    """Case-insensitive substring search over cached player display names."""
    players = await get_all_players()
    query_lower = query.lower()
    matches = []
    for player in players.values():
        name = display_name(player)
        if name and query_lower in name.lower():
            matches.append(player)
    matches.sort(key=lambda p: p["search_rank"] if p.get("search_rank") is not None else float("inf"))
    return matches[:limit]


async def search_players_by_last_name(
    last_name: str, first_initial: str | None = None, limit: int = 25
) -> list[dict[str, Any]]:
    """Matches players by exact last name, optionally narrowed by first-name
    initial - handles abbreviated names like "P. Mahomes" (common when
    copying a roster from ESPN or a similar site), which the substring
    search in search_players() won't match against a full display name."""
    players = await get_all_players()
    last_name_lower = last_name.lower()
    matches = []
    for player in players.values():
        player_last = (player.get("last_name") or "").lower()
        if player_last != last_name_lower:
            continue
        if first_initial:
            player_first = player.get("first_name") or ""
            if not player_first.lower().startswith(first_initial.lower()):
                continue
        matches.append(player)
    matches.sort(key=lambda p: p["search_rank"] if p.get("search_rank") is not None else float("inf"))
    return matches[:limit]


async def get_season_stats(
    player_id: str, season: int, season_type: Literal["regular", "post", "pre"] = "regular"
) -> dict[str, Any]:
    """Season-aggregate stats (points, per-position totals, position rank) for
    a player. Lives outside the /v1 API the rest of this module uses, so it's
    fetched by absolute URL rather than through the shared client's base_url.
    Returns {} if unavailable (e.g. a rookie/backup with no games played, or
    a team defense id, which this endpoint doesn't recognize) rather than
    raising - callers treat missing stats as "nothing to report", not an error.
    """
    try:
        response = await get_http_client().get(
            f"https://api.sleeper.app/stats/nfl/player/{player_id}",
            params={"season_type": season_type, "season": season},
        )
    except httpx.HTTPError:
        return {}
    if response.status_code != 200:
        return {}
    body = response.json()
    return (body or {}).get("stats") or {}


async def get_player(player_id: str) -> dict[str, Any]:
    players = await get_all_players()
    player = players.get(player_id)
    if player is None:
        raise SleeperNotFoundError(f"Unknown Sleeper player_id: {player_id}")
    return player
