"""Turns pasted roster text or a Sleeper username/league into roster entries.

Two entry points:
- parse_roster_text + resolve_entries: free-text paste -> best-effort match
  against Sleeper's player database (for sleeper_player_id/position/team).
- import_sleeper_team: username + league_id -> exact roster pulled straight
  from Sleeper (no fuzzy matching needed, since Sleeper already tells us
  which player_ids are on the roster).
"""

import asyncio
import re
from dataclasses import dataclass

from app.services import sleeper

NFL_TEAM_ABBREVIATIONS = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN",
    "DET", "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA",
    "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB",
    "TEN", "WAS",
}

_POSITION_TOKENS = {"QB", "RB", "WR", "TE", "K", "DST", "DEF"}
_POSITION_ALIASES = {"DEF": "DST"}
# Lineup-slot labels, not real positions - people often paste these
# alongside a player's actual position (e.g. "FLEX Christian McCaffrey").
_SLOT_ONLY_TOKENS = {"FLEX"}
# Bench markers some sources (e.g. ESPN's "BE") export alongside a player -
# not a starting slot at all, so these never become entry.slot; they're only
# used to recognize where one bench player ends and the next begins.
_BENCH_MARKER_TOKENS = {"BE", "BN"}

_LEADING_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
_TOKEN_SPLIT_RE = re.compile(r"[\s,()/]+")
# Matches "P. Mahomes"-style abbreviated names (common when a roster is
# copied from ESPN or similar sites that don't spell out first names).
_INITIAL_LASTNAME_RE = re.compile(r"^([A-Za-z])\.\s*(.+)$")

# Roster slots that represent bench/reserve, not an active starting lineup slot.
NON_STARTING_SLOTS = {"BN", "IR", "TAXI"}

# Positions that can fill a FLEX slot.
FLEX_ELIGIBLE_POSITIONS = {"RB", "WR", "TE"}


def normalize_position(position: str | None) -> str | None:
    """Canonicalizes position aliases (Sleeper's own player data uses "DEF"
    for defenses; this app stores "DST" everywhere for consistency with
    lineup slot labels). Callers that accept a position directly from a
    user (not just parsed text) should route it through this too."""
    if position is None:
        return None
    upper = position.upper()
    return _POSITION_ALIASES.get(upper, upper)


class RosterImportError(Exception):
    """Raised when a Sleeper roster/team lookup can't be resolved to a roster."""


@dataclass
class ParsedRosterEntry:
    name: str
    position: str | None = None
    nfl_team: str | None = None
    slot: str | None = None
    sleeper_player_id: str | None = None
    # Explicitly marked bench in the pasted text (e.g. a "BE"/"BN" token) -
    # kept separate from `slot` (which only ever holds a real starting slot)
    # so assign_starting_slots knows never to auto-promote this entry, even
    # if its position would otherwise fit an open slot.
    bench: bool = False


@dataclass
class SleeperRosterImport:
    team_name: str
    starting_lineup_slots: list[str]
    sleeper_user_id: str
    players: list[ParsedRosterEntry]


_MARKER_TOKENS = _POSITION_TOKENS | _SLOT_ONLY_TOKENS | _BENCH_MARKER_TOKENS


def _parse_line_tokens(tokens: list[str]) -> list[ParsedRosterEntry]:
    """Parses the tokens of a single line, which may actually contain more
    than one player pasted back-to-back without line breaks (e.g. "QB L.
    Jackson RB D. Swift WR A. Brown", or "K A. Borregales BE P. Mahomes BE
    J. Dart"). A position/slot/bench marker is treated as the start of a new
    player once the entry in progress already has a name - but a *repeated*
    marker with nothing new after it but team info (e.g. "WR Justin
    Jefferson, WR, MIN") is a harmless redundant mention, not a new player.
    """
    entries: list[ParsedRosterEntry] = []
    position: str | None = None
    nfl_team: str | None = None
    slot: str | None = None
    bench = False
    name_tokens: list[str] = []

    def flush() -> None:
        nonlocal position, nfl_team, slot, bench, name_tokens
        tokens_for_name = name_tokens
        if not tokens_for_name and nfl_team:
            # A bare defense line like "SF DST" consumes both tokens as
            # team + position, leaving nothing for the name - fall back to
            # the team code itself so the entry isn't silently dropped.
            tokens_for_name = [nfl_team]
        name = " ".join(tokens_for_name).strip(" -,")
        if name:
            entries.append(
                ParsedRosterEntry(
                    name=name, position=position, nfl_team=nfl_team, slot=slot, bench=bench
                )
            )
        position, nfl_team, slot, bench, name_tokens = None, None, None, False, []

    def starts_new_player(next_index: int) -> bool:
        """True if a real name token (not just a team abbreviation) appears
        before the next marker or the end of the line - distinguishes "a new
        player follows" from a marker just trailing the current one."""
        for t in tokens[next_index:]:
            u = t.upper()
            if u in _MARKER_TOKENS:
                return False
            if u in NFL_TEAM_ABBREVIATIONS:
                continue
            return True
        return False

    for i, token in enumerate(tokens):
        upper = token.upper()
        if upper in _MARKER_TOKENS:
            # Any marker (position, FLEX, or bench) while the entry in
            # progress already has *some* marker set and a name - if real
            # content follows, this is a new player, not more of this one.
            entry_in_progress = position is not None or slot is not None or bench
            if entry_in_progress and name_tokens and starts_new_player(i + 1):
                flush()
            if upper in _BENCH_MARKER_TOKENS:
                bench = True
            elif upper in _SLOT_ONLY_TOKENS:
                slot = upper
            else:
                position = _POSITION_ALIASES.get(upper, upper)
            continue
        if upper in NFL_TEAM_ABBREVIATIONS:
            if nfl_team is None:
                nfl_team = upper
            continue
        name_tokens.append(token)

    flush()
    return entries


def parse_roster_text(text: str) -> list[ParsedRosterEntry]:
    """Best-effort parse of a pasted roster.

    Handles lines like "QB Patrick Mahomes", "Patrick Mahomes - QB - KC",
    "Patrick Mahomes, QB, KC", "FLEX Christian McCaffrey", a bare team
    defense ("SF DST"), a bare "Patrick Mahomes", or multiple players
    pasted on one line without breaks between them. Position/team/slot
    tokens are recognized anywhere in the line; whatever's left is the name.
    """
    entries = []
    for raw_line in text.splitlines():
        line = _LEADING_MARKER_RE.sub("", raw_line).strip(" -")
        if not line:
            continue
        tokens = [t for t in _TOKEN_SPLIT_RE.split(line) if t]
        entries.extend(_parse_line_tokens(tokens))

    return entries


def assign_starting_slots(
    entries: list[ParsedRosterEntry], open_slots: list[str]
) -> None:
    """Matches parsed roster entries against a team's open starting-lineup
    slots, in pasted order, so a roster paste that already specifies
    positions matching the lineup shape is recognized as the starting lineup
    rather than landing entirely on the bench. Mutates entries in place;
    entries beyond what `open_slots` can hold are left with slot=None (bench).
    """
    remaining_slots = list(open_slots)
    unassigned = list(entries)

    # Pass 1: exact position matches, skipping entries already explicitly
    # slotted or explicitly benched (e.g. a "BE" marker in the paste).
    for entry in entries:
        if entry.slot or entry.bench:
            continue
        if entry.position and entry.position in remaining_slots:
            remaining_slots.remove(entry.position)
            entry.slot = entry.position
            unassigned.remove(entry)

    # Pass 2: explicit FLEX tags consume a FLEX slot if still open.
    for entry in entries:
        if entry.slot == "FLEX":
            if "FLEX" in remaining_slots:
                remaining_slots.remove("FLEX")
            else:
                entry.slot = None
            if entry in unassigned:
                unassigned.remove(entry)

    # Pass 3: leftover FLEX-eligible entries fill remaining FLEX slots, in
    # order - skipping explicitly benched entries, which should never be
    # auto-promoted into a starting slot regardless of position.
    for entry in list(unassigned):
        if entry.bench:
            continue
        if "FLEX" not in remaining_slots:
            break
        if entry.position in FLEX_ELIGIBLE_POSITIONS:
            remaining_slots.remove("FLEX")
            entry.slot = "FLEX"
            unassigned.remove(entry)
    # Anything still in `unassigned` keeps slot=None (bench) - already the default.


async def resolve_entry(entry: ParsedRosterEntry) -> ParsedRosterEntry:
    """Fill in sleeper_player_id/position/team by matching against Sleeper's
    player database. Falls back to the entry as-typed if nothing matches."""
    position = normalize_position(entry.position)

    if position == "DST":
        team_code = entry.nfl_team or (
            entry.name.upper() if entry.name.upper() in NFL_TEAM_ABBREVIATIONS else None
        )
        if team_code:
            try:
                player = await sleeper.get_player(team_code)
            except sleeper.SleeperNotFoundError:
                pass
            else:
                return ParsedRosterEntry(
                    name=sleeper.display_name(player) or entry.name,
                    position=position,
                    nfl_team=player.get("team") or team_code,
                    slot=entry.slot,
                    sleeper_player_id=player.get("player_id"),
                    bench=entry.bench,
                )

    # Try the "P. Mahomes" abbreviated-name pattern first, when it applies -
    # it's more precise than the substring search below, which can produce
    # false positives on abbreviated queries (e.g. "J. Jefferson" substring-
    # matches "A.J. Jefferson", since "a.j. jefferson" literally contains
    # "j. jefferson"). A real period-containing full name like "T.J. Watt"
    # won't match any last_name in Sleeper's data via this path, so it falls
    # through to the substring search below, which handles it correctly.
    matches: list[dict] = []
    abbreviated = _INITIAL_LASTNAME_RE.match(entry.name)
    if abbreviated:
        initial, last_name = abbreviated.groups()
        matches = await sleeper.search_players_by_last_name(
            last_name, first_initial=initial, limit=5
        )

    if not matches:
        matches = await sleeper.search_players(entry.name, limit=5)

    if not matches:
        return ParsedRosterEntry(
            name=entry.name,
            position=position,
            nfl_team=entry.nfl_team,
            slot=entry.slot,
            sleeper_player_id=entry.sleeper_player_id,
            bench=entry.bench,
        )

    if position:
        narrowed = [m for m in matches if m.get("position") == position]
        if narrowed:
            matches = narrowed

    best = matches[0]
    return ParsedRosterEntry(
        name=sleeper.display_name(best) or entry.name,
        position=position or normalize_position(best.get("position")),
        nfl_team=entry.nfl_team or best.get("team"),
        slot=entry.slot,
        sleeper_player_id=best.get("player_id"),
        bench=entry.bench,
    )


async def resolve_entries(entries: list[ParsedRosterEntry]) -> list[ParsedRosterEntry]:
    return list(await asyncio.gather(*(resolve_entry(e) for e in entries)))


async def _import_sleeper_team_for_user_id(user_id: str, league_id: str) -> SleeperRosterImport:
    league, rosters, players_map, league_users = await asyncio.gather(
        sleeper.get_league(league_id),
        sleeper.get_league_rosters(league_id),
        sleeper.get_all_players(),
        sleeper.get_league_users(league_id),
    )

    roster = next((r for r in rosters if r.get("owner_id") == user_id), None)
    if roster is None:
        raise RosterImportError(
            f"No roster found for user_id '{user_id}' in league '{league_id}'"
        )

    starting_slots = [
        slot for slot in league.get("roster_positions", []) if slot not in NON_STARTING_SLOTS
    ]
    # Sleeper's `starters` list is positionally aligned with the non-bench
    # entries of `roster_positions`, so zipping the two tells us exactly
    # which slot each starter occupies.
    slot_by_player_id = dict(zip(roster.get("starters") or [], starting_slots))

    player_ids = roster.get("players") or []
    players = []
    for player_id in player_ids:
        player = players_map.get(player_id)
        if player is None:
            continue
        players.append(
            ParsedRosterEntry(
                name=sleeper.display_name(player) or player_id,
                position=player.get("position"),
                nfl_team=player.get("team"),
                slot=slot_by_player_id.get(player_id),
                sleeper_player_id=player_id,
            )
        )

    league_user = next((u for u in league_users if u.get("user_id") == user_id), None)
    team_name = None
    if league_user:
        team_name = (league_user.get("metadata") or {}).get("team_name")
    team_name = team_name or (league_user or {}).get("display_name") or user_id

    return SleeperRosterImport(
        team_name=team_name,
        starting_lineup_slots=starting_slots,
        sleeper_user_id=user_id,
        players=players,
    )


async def import_sleeper_team(username: str, league_id: str) -> SleeperRosterImport:
    """Resolve a username -> league roster owned by that user."""
    user = await sleeper.get_user(username)
    return await _import_sleeper_team_for_user_id(user["user_id"], league_id)


async def resync_sleeper_team(user_id: str, league_id: str) -> SleeperRosterImport:
    """Re-pull the latest roster for an already-known Sleeper user_id."""
    return await _import_sleeper_team_for_user_id(user_id, league_id)
