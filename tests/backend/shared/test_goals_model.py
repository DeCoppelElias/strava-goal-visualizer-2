from decimal import Decimal

from backend.shared.models import Goal, User
from sqlalchemy import CheckConstraint
from sqlalchemy import inspect as sa_inspect


def test_goal_column_default_is_365():
    col_default = Goal.__table__.c.yearly_running_goal_km.default
    assert col_default is not None
    assert col_default.arg == Decimal("365")


def test_goal_user_id_is_primary_key():
    pk_cols = {c.key for c in Goal.__table__.primary_key.columns}
    assert pk_cols == {"user_id"}


def test_goal_has_check_constraint_on_yearly_running_goal_km():
    constraints = [c for c in Goal.__table__.constraints if isinstance(c, CheckConstraint)]
    assert len(constraints) == 1
    assert "yearly_running_goal_km" in str(constraints[0].sqltext)


def test_goal_updated_at_is_timezone_aware():
    assert sa_inspect(Goal).columns["updated_at"].type.timezone is True


def test_user_has_goal_relationship():
    assert hasattr(User, "goal")
