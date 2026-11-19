import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.roles.catalog import RoleCode
from app.modules.roles.models import Role, user_roles
from app.modules.users.models import User
from app.shared.pagination import PageParams


def escape_like(value: str) -> str:
    """Treat %, _ and \\ in user input literally inside LIKE patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class UserRepository:
    """All queries are scoped to an organization except the global email lookup used to log in."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        return self._session.scalar(select(User).where(User.email == email.lower()))

    def get_by_email_for_update(self, email: str) -> User | None:
        return self._session.scalar(
            select(User).where(User.email == email.lower()).with_for_update()
        )

    def get(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        return self._session.scalar(
            select(User).where(User.id == user_id, User.organization_id == organization_id)
        )

    def email_exists(self, email: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        query = select(User.id).where(User.email == email.lower())
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        return self._session.scalar(query) is not None

    def search(
        self,
        organization_id: uuid.UUID,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        role_code: str | None = None,
    ) -> tuple[list[User], int]:
        query: Select[User] = select(User).where(User.organization_id == organization_id)
        if search and search.strip():
            pattern = f"%{escape_like(search.strip())}%"
            query = query.where(
                or_(
                    User.full_name.ilike(pattern, escape="\\"),
                    User.email.ilike(pattern, escape="\\"),
                )
            )
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if role_code:
            query = query.where(
                User.id.in_(
                    select(user_roles.c.user_id)
                    .join(Role, Role.id == user_roles.c.role_id)
                    .where(Role.code == role_code, Role.organization_id == organization_id)
                )
            )

        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self._session.scalars(
            query.order_by(User.full_name, User.id).offset(params.offset).limit(params.size)
        ).all()
        return [*items], total

    def count_active_admins(self, organization_id: uuid.UUID) -> int:
        return (
            self._session.scalar(
                select(func.count(func.distinct(User.id)))
                .join(user_roles, user_roles.c.user_id == User.id)
                .join(Role, Role.id == user_roles.c.role_id)
                .where(
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                    Role.code == RoleCode.ADMIN,
                )
            )
            or 0
        )

    def add(self, user: User) -> None:
        self._session.add(user)
        self._session.flush()
