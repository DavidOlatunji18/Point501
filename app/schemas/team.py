from typing import Literal

from pydantic import BaseModel, model_validator

DEFAULT_LINEUP_SLOTS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "DST", "K"]


class PlayerCreate(BaseModel):
    name: str
    position: str | None = None
    nfl_team: str | None = None
    slot: str | None = None
    # When provided (e.g. from an autocomplete selection), the player is
    # looked up exactly by this ID instead of fuzzy-matched from `name`.
    sleeper_player_id: str | None = None


class PlayerUpdate(BaseModel):
    name: str | None = None
    position: str | None = None
    nfl_team: str | None = None
    slot: str | None = None
    # Only touched when the key is present in the request body at all (see
    # `model_fields_set` in the router) - lets a client explicitly re-link
    # to a different player (a string ID) or unlink (null), while a request
    # that omits this key entirely leaves the existing link untouched.
    sleeper_player_id: str | None = None


class PlayerOut(BaseModel):
    id: int
    name: str
    position: str | None
    nfl_team: str | None
    sleeper_player_id: str | None
    slot: str | None

    model_config = {"from_attributes": True}


class TeamCreate(BaseModel):
    source: Literal["manual", "sleeper"]
    name: str | None = None
    starting_lineup_slots: list[str] | None = None
    roster_text: str | None = None
    sleeper_username: str | None = None
    sleeper_league_id: str | None = None

    @model_validator(mode="after")
    def check_required_fields_for_source(self) -> "TeamCreate":
        if self.source == "manual":
            if not self.name:
                raise ValueError("`name` is required when source='manual'")
        else:
            if not self.sleeper_username or not self.sleeper_league_id:
                raise ValueError(
                    "`sleeper_username` and `sleeper_league_id` are required when source='sleeper'"
                )
        return self


class TeamUpdate(BaseModel):
    name: str | None = None
    starting_lineup_slots: list[str] | None = None


class TeamOut(BaseModel):
    id: int
    name: str
    source: str
    sleeper_league_id: str | None
    sleeper_user_id: str | None
    starting_lineup_slots: list[str]
    players: list[PlayerOut]

    model_config = {"from_attributes": True}


class RosterPasteRequest(BaseModel):
    roster_text: str


class LineupAssignmentApply(BaseModel):
    player_id: int
    slot: str | None = None


class ApplyLineupRequest(BaseModel):
    """Bulk-applies a full set of slot assignments (e.g. from an AI lineup
    recommendation) in one request instead of one PATCH per player."""

    assignments: list[LineupAssignmentApply]
