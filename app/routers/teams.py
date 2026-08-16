from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.team import RosterPlayer, Team
from app.schemas.team import (
    DEFAULT_LINEUP_SLOTS,
    ApplyLineupRequest,
    PlayerCreate,
    PlayerOut,
    PlayerUpdate,
    RosterPasteRequest,
    TeamCreate,
    TeamOut,
    TeamUpdate,
)
from app.services import roster_import
from app.services import sleeper
from app.services.roster_import import RosterImportError
from app.services.sleeper import SleeperNotFoundError

router = APIRouter(prefix="/teams", tags=["teams"])

MAX_TEAMS = 3


def _get_team_or_404(db: Session, team_id: int) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    return team


def _get_player_or_404(db: Session, team: Team, player_id: int) -> RosterPlayer:
    player = db.get(RosterPlayer, player_id)
    if player is None or player.team_id != team.id:
        raise HTTPException(
            status_code=404, detail=f"Player {player_id} not found on team {team.id}"
        )
    return player


def _as_roster_players(entries: list[roster_import.ParsedRosterEntry]) -> list[RosterPlayer]:
    return [
        RosterPlayer(
            name=e.name,
            position=e.position,
            nfl_team=e.nfl_team,
            sleeper_player_id=e.sleeper_player_id,
            slot=e.slot,
        )
        for e in entries
    ]


def _validate_slot(position: str | None, slot: str | None) -> None:
    """FLEX can only hold RB/WR/TE - reject an assignment that would put an
    ineligible position (e.g. QB, K, DST) there."""
    if slot == "FLEX" and position not in roster_import.FLEX_ELIGIBLE_POSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"{position or 'This position'} is not FLEX-eligible (FLEX only holds RB/WR/TE)",
        )


def _check_team_capacity(db: Session) -> None:
    existing_count = db.scalar(select(func.count()).select_from(Team))
    if existing_count >= MAX_TEAMS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_TEAMS} teams already saved; delete one before adding another",
        )


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.scalars(select(Team)).all()


@router.post("", response_model=TeamOut, status_code=201)
async def create_team(payload: TeamCreate, db: Session = Depends(get_db)):
    _check_team_capacity(db)  # fail fast before hitting the Sleeper API

    if payload.source == "sleeper":
        try:
            imported = await roster_import.import_sleeper_team(
                payload.sleeper_username, payload.sleeper_league_id
            )
        except SleeperNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except RosterImportError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        team = Team(
            name=payload.name or imported.team_name,
            source="sleeper",
            sleeper_league_id=payload.sleeper_league_id,
            sleeper_user_id=imported.sleeper_user_id,
            starting_lineup_slots=(
                payload.starting_lineup_slots
                if payload.starting_lineup_slots is not None
                else imported.starting_lineup_slots
            ),
            players=_as_roster_players(imported.players),
        )
    else:
        parsed = roster_import.parse_roster_text(payload.roster_text) if payload.roster_text else []
        resolved = await roster_import.resolve_entries(parsed) if parsed else []
        starting_lineup_slots = (
            payload.starting_lineup_slots
            if payload.starting_lineup_slots is not None
            else list(DEFAULT_LINEUP_SLOTS)
        )
        roster_import.assign_starting_slots(resolved, starting_lineup_slots)
        team = Team(
            name=payload.name,
            source="manual",
            starting_lineup_slots=starting_lineup_slots,
            players=_as_roster_players(resolved),
        )

    _check_team_capacity(db)  # re-check post-await to narrow the create-race window
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int, db: Session = Depends(get_db)):
    return _get_team_or_404(db, team_id)


@router.patch("/{team_id}", response_model=TeamOut)
def update_team(team_id: int, payload: TeamUpdate, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)
    if payload.name is not None:
        team.name = payload.name
    if payload.starting_lineup_slots is not None:
        team.starting_lineup_slots = payload.starting_lineup_slots
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: int, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)
    db.delete(team)
    db.commit()


@router.post("/{team_id}/sync", response_model=TeamOut)
async def sync_team_from_sleeper(team_id: int, db: Session = Depends(get_db)):
    """Re-pull a Sleeper-sourced team's roster (post-waiver/trade refresh)."""
    team = _get_team_or_404(db, team_id)
    if team.source != "sleeper":
        raise HTTPException(status_code=400, detail="Only Sleeper-sourced teams can be synced")

    try:
        imported = await roster_import.resync_sleeper_team(team.sleeper_user_id, team.sleeper_league_id)
    except SleeperNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RosterImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    team.players = _as_roster_players(imported.players)
    team.starting_lineup_slots = imported.starting_lineup_slots
    db.commit()
    db.refresh(team)
    return team


@router.post("/{team_id}/players", response_model=PlayerOut, status_code=201)
async def add_player(team_id: int, payload: PlayerCreate, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)

    if payload.sleeper_player_id:
        # Caller already knows the exact player (e.g. picked from an
        # autocomplete) - look them up directly instead of fuzzy-matching.
        try:
            live = await sleeper.get_player(payload.sleeper_player_id)
        except SleeperNotFoundError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown sleeper_player_id '{payload.sleeper_player_id}'",
            )
        position = roster_import.normalize_position(payload.position or live.get("position"))
        _validate_slot(position, payload.slot)
        player = RosterPlayer(
            team_id=team.id,
            name=payload.name,
            position=position,
            nfl_team=payload.nfl_team or live.get("team"),
            sleeper_player_id=payload.sleeper_player_id,
            slot=payload.slot,
        )
    else:
        resolved = await roster_import.resolve_entry(
            roster_import.ParsedRosterEntry(
                name=payload.name, position=payload.position, nfl_team=payload.nfl_team
            )
        )
        position = roster_import.normalize_position(payload.position) or resolved.position
        _validate_slot(position, payload.slot)
        player = RosterPlayer(
            team_id=team.id,
            name=payload.name,
            position=position,
            nfl_team=payload.nfl_team or resolved.nfl_team,
            sleeper_player_id=resolved.sleeper_player_id,
            slot=payload.slot,
        )

    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.patch("/{team_id}/players/{player_id}", response_model=PlayerOut)
async def update_player(
    team_id: int, player_id: int, payload: PlayerUpdate, db: Session = Depends(get_db)
):
    team = _get_team_or_404(db, team_id)
    player = _get_player_or_404(db, team, player_id)

    if payload.name is not None:
        player.name = payload.name
    if payload.position is not None:
        player.position = roster_import.normalize_position(payload.position)
    if payload.nfl_team is not None:
        player.nfl_team = payload.nfl_team
    if "slot" in payload.model_fields_set:
        _validate_slot(player.position, payload.slot)
        player.slot = payload.slot
    if "sleeper_player_id" in payload.model_fields_set:
        if payload.sleeper_player_id:
            try:
                await sleeper.get_player(payload.sleeper_player_id)
            except SleeperNotFoundError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown sleeper_player_id '{payload.sleeper_player_id}'",
                )
        player.sleeper_player_id = payload.sleeper_player_id

    db.commit()
    db.refresh(player)
    return player


@router.delete("/{team_id}/players/{player_id}", status_code=204)
def remove_player(team_id: int, player_id: int, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)
    player = _get_player_or_404(db, team, player_id)
    db.delete(player)
    db.commit()


@router.post("/{team_id}/roster/paste", response_model=TeamOut)
async def paste_roster(
    team_id: int,
    payload: RosterPasteRequest,
    replace: bool = Query(default=False, description="Clear existing players before adding"),
    db: Session = Depends(get_db),
):
    team = _get_team_or_404(db, team_id)
    parsed = roster_import.parse_roster_text(payload.roster_text)
    if not parsed:
        raise HTTPException(status_code=400, detail="Could not parse any players from roster_text")
    resolved = await roster_import.resolve_entries(parsed)

    if replace:
        open_slots = list(team.starting_lineup_slots)
        roster_import.assign_starting_slots(resolved, open_slots)
        team.players = _as_roster_players(resolved)
    else:
        open_slots = list(team.starting_lineup_slots)
        for existing in team.players:
            if existing.slot and existing.slot in open_slots:
                open_slots.remove(existing.slot)
        roster_import.assign_starting_slots(resolved, open_slots)
        team.players.extend(_as_roster_players(resolved))

    db.commit()
    db.refresh(team)
    return team


@router.post("/{team_id}/apply-lineup", response_model=TeamOut)
def apply_lineup(team_id: int, payload: ApplyLineupRequest, db: Session = Depends(get_db)):
    """Bulk-applies slot assignments in one request - e.g. one-click "Set
    Lineup" after reviewing an AI recommendation, instead of PATCHing each
    player individually."""
    team = _get_team_or_404(db, team_id)
    players_by_id = {p.id: p for p in team.players}

    for entry in payload.assignments:
        player = players_by_id.get(entry.player_id)
        if player is None:
            raise HTTPException(
                status_code=400, detail=f"Player {entry.player_id} not found on team {team_id}"
            )
        _validate_slot(player.position, entry.slot)

    for entry in payload.assignments:
        players_by_id[entry.player_id].slot = entry.slot

    db.commit()
    db.refresh(team)
    return team
