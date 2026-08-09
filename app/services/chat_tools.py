"""Tool definitions and dispatcher for the /chat agentic loop.

Roster and RAG-article context are injected automatically (per the product
spec); these tools cover the dynamic lookups the model can't know it needs
in advance - a specific player not on the roster, a different week's
schedule/byes, box score stats, trending waiver adds, or a more targeted
article search than the automatic one.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable

from app.services import articles as articles_service
from app.services import espn, sleeper

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_players",
        "description": (
            "Search Sleeper's live NFL player database by name. Returns "
            "matching players with position, team, and current injury_status. "
            "Use this for any player not already included in the roster context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Player name or partial name"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_week_schedule",
        "description": "Get the NFL schedule (matchups, kickoff times in Eastern, scores) for a given week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "week": {"type": "integer"},
                "season": {"type": "integer"},
                "season_type": {
                    "type": "integer",
                    "description": "1=preseason, 2=regular season, 3=postseason",
                },
            },
            "required": ["week", "season"],
        },
    },
    {
        "name": "get_bye_teams",
        "description": "Get which NFL teams are on a bye in a given week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "week": {"type": "integer"},
                "season": {"type": "integer"},
                "season_type": {"type": "integer"},
            },
            "required": ["week", "season"],
        },
    },
    {
        "name": "get_game_boxscore",
        "description": (
            "Get per-player box score stats (passing/rushing/receiving/etc) for a "
            "played or live game. Requires an event_id from get_week_schedule."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"],
        },
    },
    {
        "name": "get_trending_players",
        "description": "Get players being added or dropped across Sleeper right now - useful for waiver-wire questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trend_type": {"type": "string", "enum": ["add", "drop"]},
            },
            "required": ["trend_type"],
        },
    },
    {
        "name": "search_articles",
        "description": (
            "Semantic search over ingested fantasy football news/analysis articles. "
            "Use this for a more targeted search than the articles already "
            "included in context, e.g. for a specific player or topic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "description": "Default 5, max 10"},
            },
            "required": ["query"],
        },
    },
]


async def _tool_search_players(tool_input: dict[str, Any]) -> Any:
    return await sleeper.search_players(tool_input["query"], limit=5)


async def _tool_get_week_schedule(tool_input: dict[str, Any]) -> Any:
    return await espn.get_week_schedule(
        tool_input["week"], tool_input["season"], tool_input.get("season_type", 2)
    )


async def _tool_get_bye_teams(tool_input: dict[str, Any]) -> Any:
    return await espn.get_bye_teams(
        tool_input["week"], tool_input["season"], tool_input.get("season_type", 2)
    )


async def _tool_get_game_boxscore(tool_input: dict[str, Any]) -> Any:
    return await espn.get_game_boxscore(tool_input["event_id"])


async def _tool_get_trending_players(tool_input: dict[str, Any]) -> Any:
    return await sleeper.get_trending_players(tool_input["trend_type"])


async def _tool_search_articles(tool_input: dict[str, Any]) -> Any:
    limit = min(tool_input.get("limit", 5), 10)
    return await asyncio.to_thread(articles_service.search_articles, tool_input["query"], limit)


_HANDLERS: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {
    "search_players": _tool_search_players,
    "get_week_schedule": _tool_get_week_schedule,
    "get_bye_teams": _tool_get_bye_teams,
    "get_game_boxscore": _tool_get_game_boxscore,
    "get_trending_players": _tool_get_trending_players,
    "search_articles": _tool_search_articles,
}

_KNOWN_ERRORS = (
    sleeper.SleeperAPIError,
    sleeper.SleeperNotFoundError,
    espn.EspnAPIError,
    espn.EspnNotFoundError,
)


async def dispatch(name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
    """Executes a tool call. Returns (content, is_error) for the tool_result block.

    tool_input comes from the model, not trusted app code, so a missing or
    malformed field is an expected failure mode here (none of these tool
    schemas set strict:True) - it should become a tool_result error the
    model can recover from, not a crashed request.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool '{name}'"}), True
    try:
        result = await handler(tool_input)
    except _KNOWN_ERRORS as exc:
        return json.dumps({"error": str(exc)}), True
    except (KeyError, TypeError, ValueError) as exc:
        return json.dumps({"error": f"Invalid arguments for tool '{name}': {exc}"}), True
    return json.dumps(result, default=str), False
