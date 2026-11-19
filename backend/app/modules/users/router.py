import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import AppSettings, DbSession, require_permissions
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.users.schemas import (
    TemporaryPasswordSet,
    UserCreate,
    UserRead,
    UserRolesUpdate,
    UserUpdate,
)
from app.modules.users.service import UserService
from app.shared.context import RequestContext, get_request_context
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/users", tags=["users"])

Reader = Annotated[User, Depends(require_permissions(Perm.USERS_READ))]
Manager = Annotated[User, Depends(require_permissions(Perm.USERS_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_user_service(session: DbSession, settings: AppSettings) -> UserService:
    return UserService(session, settings)


Service = Annotated[UserService, Depends(get_user_service)]


@router.get("", response_model=Page[UserRead], summary="Listar usuarios")
def list_users(
    actor: Reader,
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(max_length=100, description="Nombre o correo")] = None,
    is_active: bool | None = None,
    role: Annotated[str | None, Query(max_length=32, description="Código de rol")] = None,
) -> Page[UserRead]:
    items, total = service.search(actor, params, search=q, is_active=is_active, role_code=role)
    return Page(
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario con contraseña temporal",
)
def create_user(body: UserCreate, actor: Manager, service: Service, context: Context) -> User:
    return service.create(actor, body, context)


@router.get("/{user_id}", response_model=UserRead, summary="Detalle de usuario")
def get_user(user_id: uuid.UUID, actor: Reader, service: Service) -> User:
    return service.get(actor, user_id)


@router.patch("/{user_id}", response_model=UserRead, summary="Editar, activar o desactivar")
def update_user(
    user_id: uuid.UUID, body: UserUpdate, actor: Manager, service: Service, context: Context
) -> User:
    return service.update(actor, user_id, body, context)


@router.put("/{user_id}/roles", response_model=UserRead, summary="Reemplazar roles del usuario")
def set_user_roles(
    user_id: uuid.UUID, body: UserRolesUpdate, actor: Manager, service: Service, context: Context
) -> User:
    return service.set_roles(actor, user_id, body.role_ids, context)


@router.post(
    "/{user_id}/temporary-password",
    response_model=UserRead,
    summary="Asignar contraseña temporal (cierra sus sesiones)",
)
def set_temporary_password(
    user_id: uuid.UUID,
    body: TemporaryPasswordSet,
    actor: Manager,
    service: Service,
    context: Context,
) -> User:
    return service.set_temporary_password(actor, user_id, body.temporary_password, context)
