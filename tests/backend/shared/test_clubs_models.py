from datetime import UTC, datetime

import sqlalchemy as sa
from backend.shared.models import Club, ClubMembership, User
from sqlalchemy import Index
from sqlalchemy import inspect as sa_inspect


def test_club_model_columns():
    club = Club(id=12345, name="Running Club")
    assert club.id == 12345
    assert club.name == "Running Club"


def test_club_id_is_primary_key():
    pk_cols = {c.key for c in Club.__table__.primary_key.columns}
    assert pk_cols == {"id"}


def test_club_id_is_biginteger():
    assert isinstance(Club.__table__.c.id.type, sa.BigInteger)


def test_club_updated_at_is_timezone_aware():
    assert sa_inspect(Club).columns["updated_at"].type.timezone is True


def test_club_has_memberships_relationship():
    assert hasattr(Club, "memberships")


def test_club_membership_model_columns():
    ts = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)
    membership = ClubMembership(user_id=1, club_id=12345, synced_at=ts)
    assert membership.user_id == 1
    assert membership.club_id == 12345
    assert membership.synced_at == ts


def test_club_membership_primary_key_is_composite():
    pk_cols = {c.key for c in ClubMembership.__table__.primary_key.columns}
    assert pk_cols == {"user_id", "club_id"}


def test_club_membership_club_id_is_biginteger():
    assert isinstance(ClubMembership.__table__.c.club_id.type, sa.BigInteger)


def test_club_membership_has_index_on_club_id():
    table_args = ClubMembership.__table_args__
    indexes = [a for a in table_args if isinstance(a, Index)]
    assert len(indexes) == 1
    col_names = {c.key for c in indexes[0].columns}
    assert col_names == {"club_id"}


def test_club_membership_synced_at_is_timezone_aware():
    assert sa_inspect(ClubMembership).columns["synced_at"].type.timezone is True


def test_club_membership_has_user_relationship():
    assert hasattr(ClubMembership, "user")


def test_club_membership_has_club_relationship():
    assert hasattr(ClubMembership, "club")


def test_user_has_club_memberships_relationship():
    assert hasattr(User, "club_memberships")
