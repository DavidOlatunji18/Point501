"""Team/roster storage.

Deliberately stores only player *identity* (name, position, nfl_team,
sleeper_player_id) and lineup config - not injury status or stats, which go
stale. Those are looked up live from Sleeper (and later ESPN) at query time
using `sleeper_player_id`, keyed off app/services/sleeper.py.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(20))  # "manual" | "sleeper"
    sleeper_league_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sleeper_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    starting_lineup_slots: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    players: Mapped[list["RosterPlayer"]] = relationship(
        back_populates="team", cascade="all, delete-orphan", order_by="RosterPlayer.id"
    )


class RosterPlayer(Base):
    __tablename__ = "roster_players"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    name: Mapped[str] = mapped_column(String(120))
    position: Mapped[str | None] = mapped_column(String(10), nullable=True)
    nfl_team: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sleeper_player_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    slot: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    team: Mapped["Team"] = relationship(back_populates="players")
