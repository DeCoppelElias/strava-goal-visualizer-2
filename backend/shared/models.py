import enum
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_tz = DateTime(timezone=True)
_now = lambda: datetime.now(UTC)  # noqa: E731


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    strava_athlete_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    display_name: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(_tz, default=_now)
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now, onupdate=_now)

    oauth_credentials: Mapped["OAuthCredentials"] = relationship(
        back_populates="user", uselist=False
    )
    activities: Mapped[list["Activity"]] = relationship(back_populates="user")
    sync_state: Mapped[Optional["SyncState"]] = relationship(back_populates="user", uselist=False)
    goal: Mapped[Optional["Goal"]] = relationship(back_populates="user", uselist=False)
    club_memberships: Mapped[list["ClubMembership"]] = relationship(back_populates="user")


class OAuthCredentials(Base):
    __tablename__ = "oauth_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime] = mapped_column(_tz)
    scope: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_tz, default=_now)
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="oauth_credentials")


class OAuthStateToken(Base):
    __tablename__ = "oauth_state_tokens"

    token: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(_tz, default=_now)
    expires_at: Mapped[datetime] = mapped_column(_tz)


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("user_id", "strava_activity_id"),
        Index("ix_activities_user_start_date", "user_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    strava_activity_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(Text)
    sport_type: Mapped[str] = mapped_column(Text)
    distance_meters: Mapped[Decimal] = mapped_column(Numeric)
    moving_time_seconds: Mapped[int] = mapped_column()
    start_date: Mapped[datetime] = mapped_column(_tz)
    created_at: Mapped[datetime] = mapped_column(_tz, default=_now)
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="activities")


class SyncState(Base):
    __tablename__ = "sync_state"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    last_sync_completed_at: Mapped[datetime] = mapped_column(_tz)

    user: Mapped["User"] = relationship(back_populates="sync_state")


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("yearly_running_goal_km > 0 AND yearly_running_goal_km <= 100000"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    yearly_running_goal_km: Mapped[Decimal] = mapped_column(Numeric, default=Decimal("365"))
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="goal")


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(_tz, default=_now)

    memberships: Mapped[list["ClubMembership"]] = relationship(back_populates="club")


class ClubMembership(Base):
    __tablename__ = "club_memberships"
    __table_args__ = (Index("ix_club_memberships_club_id", "club_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    club_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clubs.id"), primary_key=True)
    synced_at: Mapped[datetime] = mapped_column(_tz)

    user: Mapped["User"] = relationship(back_populates="club_memberships")
    club: Mapped["Club"] = relationship(back_populates="memberships")


class DeletionReason(enum.StrEnum):
    USER_INITIATED = "user_initiated"
    STRAVA_DEAUTH = "strava_deauth"


class DeletionEvent(Base):
    __tablename__ = "deletion_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text)
    deleted_at: Mapped[datetime] = mapped_column(_tz, default=_now)
