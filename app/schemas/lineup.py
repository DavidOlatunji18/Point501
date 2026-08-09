from pydantic import BaseModel


class LineupAssignment(BaseModel):
    slot: str
    player_id: int
    name: str
    position: str | None
    nfl_team: str | None
    reasoning: str


class BenchPlayer(BaseModel):
    player_id: int
    name: str
    position: str | None
    nfl_team: str | None


class LineupResponse(BaseModel):
    team_id: int
    week: int
    season: int
    summary: str
    lineup: list[LineupAssignment]
    bench: list[BenchPlayer]
