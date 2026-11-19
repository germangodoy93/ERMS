import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import DbSession, require_permissions
from app.modules.roles.catalog import Perm
from app.modules.roles.schemas import PermissionRead, RolePermissionsUpdate, RoleRead
from app.modules.roles.service import RoleService
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context

router = APIRouter(tags=["roles"])

Reader = Annotated[User, Depends(require_permissions(Perm.USERS_READ))]
RoleManager = Annotated[User, Depends(require_permissions(Perm.ROLES_MANAGE))]


def get_role_service(session: DbSession) -> RoleService:
    return RoleService(session)


Service = Annotated[RoleService, Depends(get_role_service)]


@router.get("/roles", response_model=list[RoleRead], summary="Roles de la organización")
def list_roles(actor: Reader, service: Service) -> list[RoleRead]:
    return service.list_roles(actor.organization_id)


@router.get("/permissions", response_model=list[PermissionRead], summary="Catálogo de permisos")
def list_permissions(_: Reader, service: Service) -> list[PermissionRead]:
    return service.list_permissions()


@router.put(
    "/roles/{role_id}/permissions",
    response_model=RoleRead,
    summary="Reemplazar los permisos de un rol (no aplica al Administrador)",
)
def set_role_permissions(
    role_id: uuid.UUID,
    body: RolePermissionsUpdate,
    actor: RoleManager,
    service: Service,
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> RoleRead:
    return service.set_permissions(actor, role_id, body.permissions, context)
