"""Builds live context (roster + schedule) to ground /chat and /lineup
answers in real data instead of the model's general knowledge."""

import asyncio
from typing import Any

from app.models.team import Team
from app.services import espn, sleeper


async def build_roster_players_context(team: Team) -> list[dict[str, Any]]:
    """Merges each roster player's stored identity with live Sleeper data
    (injury status, current team). Uses the already-cached player map, so
    this doesn't cost extra API calls beyond the first."""
    players_map = await sleeper.get_all_players()
    context = []
    for player in team.players:
        live = players_map.get(player.sleeper_player_id) if player.sleeper_player_id else None
        context.append(
            {
                "player_id": player.id,
                "name": player.name,
                "position": player.position,
                "nfl_team": (live.get("team") if live else None) or player.nfl_team,
                "slot": player.slot,
                "injury_status": live.get("injury_status") if live else None,
                "injury_notes": live.get("injury_notes") if live else None,
            }
        )
    return context


async def build_schedule_context(week: int, season: int, season_type: int = 2) -> dict[str, Any]:
    """Per-team matchup info (opponent, home/away, kickoff, bye status) for a week."""
    schedule, bye_teams = await asyncio.gather(
        espn.get_week_schedule(week, season, season_type),
        espn.get_bye_teams(week, season, season_type),
    )
    matchups: dict[str, dict[str, Any]] = {}
    for game in schedule:
        home, away = game["home_team"], game["away_team"]
        if home:
            matchups[home] = {
                "opponent": away,
                "is_home": True,
                "kickoff_et": game["kickoff_et"],
                "status": game["status"],
            }
        if away:
            matchups[away] = {
                "opponent": home,
                "is_home": False,
                "kickoff_et": game["kickoff_et"],
                "status": game["status"],
            }
    return {"matchups": matchups, "bye_teams": bye_teams}
