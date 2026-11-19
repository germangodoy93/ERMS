import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.roles.catalog import SYSTEM_ROLES, RoleCode
from app.modules.roles.models import Permission, Role
from app.modules.roles.schemas import PermissionRead, RoleRead
from app.modules.users.models import User
from app.shared.context import RequestContext


def _to_read(role: Role) -> RoleRead:
    return RoleRead(
        id=role.id,
        code=role.code,
        name=role.name,
        is_system=role.is_system,
        permissions=[p.code for p in role.permissions],
    )


class RoleService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    def list_roles(self, organization_id: uuid.UUID) -> list[RoleRead]:
        roles = self._session.scalars(
            select(Role).where(Role.organization_id == organization_id).order_by(Role.name)
        )
        return [_to_read(r) for r in roles]

    def list_permissions(self) -> list[PermissionRead]:
        return [
            PermissionRead(code=p.code, description=p.description)
            for p in self._session.scalars(select(Permission).order_by(Permission.code))
        ]

    def set_permissions(
        self, actor: User, role_id: uuid.UUID, codes: list[str], context: RequestContext
    ) -> RoleRead:
        role = self._session.scalar(
            select(Role).where(Role.id == role_id, Role.organization_id == actor.organization_id)
        )
        if role is None:
            raise NotFoundError("El rol no existe.")
        if role.code == RoleCode.ADMIN:
            raise BusinessRuleError(
                "El rol Administrador siempre tiene todos los permisos y no se puede modificar."
            )

        wanted = set(codes)
        permissions = list(
            self._session.scalars(select(Permission).where(Permission.code.in_(wanted)))
        )
        unknown = wanted - {p.code for p in permissions}
        if unknown:
            raise BusinessRuleError(f"Permisos desconocidos: {', '.join(sorted(unknown))}.")

        old = sorted(p.code for p in role.permissions)
        new = sorted(wanted)
        if old != new:
            role.permissions = permissions
            self._audit.record(
                "role.permissions_changed",
                entity_type="role",
                entity_id=role.id,
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                context=context,
                changes={"role": role.code, "permissions": [old, new]},
            )
        return _to_read(role)


def create_system_roles(session: Session, organization_id: uuid.UUID) -> dict[RoleCode, Role]:
    """Creates the four system roles for a new organization with their default permissions."""
    permissions = {p.code: p for p in session.scalars(select(Permission))}
    roles: dict[RoleCode, Role] = {}
    for code, (name, perms) in SYSTEM_ROLES.items():
        missing = {str(p) for p in perms} - permissions.keys()
        if missing:
            raise RuntimeError(f"Permission catalog not migrated: {sorted(missing)}")
        role = Role(
            organization_id=organization_id,
            code=code,
            name=name,
            is_system=True,
            permissions=[permissions[p] for p in sorted(perms)],
        )
        session.add(role)
        roles[code] = role
    session.flush()
    return roles
