"""Builds an optimal starting lineup recommendation for a team's roster +
starting lineup slots, for a given week - a structured counterpart to /chat
for this specific high-value use case. Forces the model to respond via a
single tool call so the result is guaranteed-parseable JSON rather than
freeform text we'd have to regex out an answer from."""

import asyncio
from typing import Any

from app.core.config import get_settings
from app.models.team import Team
from app.services import context, sleeper
from app.services.anthropic_client import get_client

MAX_TOKENS = 8192

# Universal across positions; the rest are position-specific.
_STAT_LINE_FIELDS: dict[str, list[tuple[str, str]]] = {
    "QB": [("pass_yd", "pass yd"), ("pass_td", "pass TD"), ("pass_int", "INT"), ("rush_yd", "rush yd")],
    "RB": [("rush_yd", "rush yd"), ("rush_td", "rush TD"), ("rec", "rec"), ("rec_yd", "rec yd")],
    "WR": [("rec", "rec"), ("rec_yd", "rec yd"), ("rec_td", "rec TD")],
    "TE": [("rec", "rec"), ("rec_yd", "rec yd"), ("rec_td", "rec TD")],
    "K": [("fgm", "FGM"), ("fga", "FGA"), ("xpm", "XPM")],
    "DST": [("def_td", "def TD"), ("pts_allow", "pts allowed")],
    "DEF": [("def_td", "def TD"), ("pts_allow", "pts allowed")],
}


def _format_stat_line(position: str | None, stats: dict[str, Any], season_label: int) -> str | None:
    """Condenses a Sleeper season-stats blob into one short line for prompt
    grounding, e.g. "2025: 17 gm, 1223 rush yd, 13 rush TD, 366.9 pts (PPR
    rank 3)". None if the player didn't actually play that season."""
    games_played = stats.get("gp")
    if not games_played:
        return None
    parts = [f"{int(games_played)} gm"]
    for field, label in _STAT_LINE_FIELDS.get((position or "").upper(), []):
        value = stats.get(field)
        if value:
            parts.append(f"{int(value)} {label}")
    points, rank = stats.get("pts_ppr"), stats.get("pos_rank_ppr")
    if points is not None:
        parts.append(f"{points:.1f} pts (PPR rank {rank})" if rank else f"{points:.1f} pts")
    return f"{season_label}: " + ", ".join(parts)


async def _fetch_stat_lines(
    roster_context: list[dict[str, Any]], season: int
) -> dict[int, str | None]:
    """One-line season-stat summary per roster player_id, keyed for the
    prompt. Falls back to the previous season when the target season has no
    games played yet (start of season, or before it's even begun)."""

    async def one(player: dict[str, Any]) -> tuple[int, str | None]:
        sleeper_id = player.get("sleeper_player_id")
        if not sleeper_id:
            return player["player_id"], None
        current, previous = await asyncio.gather(
            sleeper.get_season_stats(sleeper_id, season),
            sleeper.get_season_stats(sleeper_id, season - 1),
        )
        line = _format_stat_line(player["position"], current, season)
        if line is None:
            line = _format_stat_line(player["position"], previous, season - 1)
        return player["player_id"], line

    results = await asyncio.gather(*(one(p) for p in roster_context))
    return dict(results)


RECOMMEND_LINEUP_TOOL = {
    "name": "recommend_lineup",
    "description": "Submit the recommended starting lineup and bench for the week.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "slot": {
                            "type": "string",
                            "description": "Starting lineup slot, e.g. QB, RB, FLEX",
                        },
                        "player_id": {
                            "type": "integer",
                            "description": "The roster player's player_id",
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": ["slot", "player_id", "reasoning"],
                    "additionalProperties": False,
                },
            },
            "bench": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "player_id": {
                            "type": "integer",
                            "description": "player_id of a benched player",
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why this player is benched instead of starting",
                        },
                    },
                    "required": ["player_id", "reasoning"],
                    "additionalProperties": False,
                },
            },
            "summary": {
                "type": "string",
                "description": "Brief overall summary of the week's lineup strategy",
            },
        },
        "required": ["assignments", "bench", "summary"],
        "additionalProperties": False,
    },
}


class LineupGenerationError(Exception):
    """Raised when the model doesn't return a usable lineup (e.g. a refusal)."""


def _format_roster_for_prompt(
    roster_context: list[dict[str, Any]],
    schedule: dict[str, Any],
    stat_lines: dict[int, str | None],
) -> str:
    matchups = schedule["matchups"]
    bye_teams = set(schedule["bye_teams"])
    lines = []
    for player in roster_context:
        team_abbr = player["nfl_team"]
        if team_abbr in bye_teams:
            matchup = "BYE"
        else:
            m = matchups.get(team_abbr)
            matchup = (
                f"{'vs' if m['is_home'] else '@'} {m['opponent']} ({m['kickoff_et']})"
                if m
                else "no game found"
            )
        injury = f", injury: {player['injury_status']}" if player.get("injury_status") else ""
        stats = stat_lines.get(player["player_id"])
        stat_part = f", stats: {stats}" if stats else ", stats: none available"
        lines.append(
            f"- player_id={player['player_id']}: {player['name']} "
            f"({player['position']}, {team_abbr}) - {matchup}{injury}{stat_part}"
        )
    return "\n".join(lines)


async def recommend_lineup(
    team: Team, week: int, season: int, season_type: int = 2
) -> dict[str, Any]:
    settings = get_settings()
    client = get_client()

    roster_context, schedule = await asyncio.gather(
        context.build_roster_players_context(team),
        context.build_schedule_context(week, season, season_type),
    )
    stat_lines = await _fetch_stat_lines(roster_context, season)

    system_prompt = (
        "You are a fantasy football lineup optimizer. Given a roster, this "
        "week's matchups/byes/injuries, and each player's season stats, assign "
        "exactly one player to each starting lineup slot, maximizing expected "
        "points while accounting for byes, injuries, matchup quality, and "
        "statistical performance/volume (cite specific numbers from the stats "
        "given, don't just gesture at them vaguely). Every non-empty slot must "
        "be filled with a player from the roster; a player can only fill one "
        "slot. Any roster player not assigned to a slot goes on the bench - "
        "give each benched player their own specific reasoning too (why the "
        "starter(s) at their position are a better play this week, e.g. worse "
        "matchup, lower volume/target share, injury concern, buried on the "
        "depth chart), not a generic one-liner. Call the recommend_lineup "
        "tool with your answer - do not respond with plain text."
    )

    user_message = (
        f"Starting lineup slots to fill: {', '.join(team.starting_lineup_slots)}\n\n"
        f"Roster (week {week}, season {season}):\n"
        f"{_format_roster_for_prompt(roster_context, schedule, stat_lines)}"
    )

    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        tools=[RECOMMEND_LINEUP_TOOL],
        tool_choice={"type": "tool", "name": "recommend_lineup"},
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
    )

    if response.stop_reason == "refusal":
        raise LineupGenerationError("The model declined to generate a lineup for this request.")

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise LineupGenerationError("The model did not return a structured lineup.")

    result = tool_use.input
    players_by_id = {p["player_id"]: p for p in roster_context}

    seen_ids: set[int] = set()
    lineup = []
    for assignment in result["assignments"]:
        player_id = assignment["player_id"]
        if player_id in seen_ids:
            raise LineupGenerationError(
                f"Model assigned player_id {player_id} to more than one slot"
            )
        player = players_by_id.get(player_id)
        if player is None:
            raise LineupGenerationError(f"Model referenced unknown player_id {player_id}")
        seen_ids.add(player_id)
        lineup.append(
            {
                "slot": assignment["slot"],
                "player_id": player["player_id"],
                "name": player["name"],
                "position": player["position"],
                "nfl_team": player["nfl_team"],
                "sleeper_player_id": player["sleeper_player_id"],
                "reasoning": assignment["reasoning"],
            }
        )

    bench = []
    for bench_entry in result["bench"]:
        player_id = bench_entry["player_id"]
        if player_id in seen_ids:
            raise LineupGenerationError(
                f"Model assigned player_id {player_id} to both a slot and the bench"
            )
        player = players_by_id.get(player_id)
        if player is None:
            raise LineupGenerationError(f"Model referenced unknown bench player_id {player_id}")
        seen_ids.add(player_id)
        bench.append(
            {
                "player_id": player["player_id"],
                "name": player["name"],
                "position": player["position"],
                "nfl_team": player["nfl_team"],
                "sleeper_player_id": player["sleeper_player_id"],
                "reasoning": bench_entry["reasoning"],
            }
        )

    missing = set(players_by_id) - seen_ids
    if missing:
        missing_names = [players_by_id[pid]["name"] for pid in missing]
        raise LineupGenerationError(
            f"Model omitted {len(missing)} roster player(s) from both lineup and "
            f"bench: {', '.join(missing_names)}"
        )

    return {
        "team_id": team.id,
        "week": week,
        "season": season,
        "summary": result["summary"],
        "lineup": lineup,
        "bench": bench,
    }
