from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import CurrentUser, DbSession, require_permissions
from app.modules.organizations.models import Organization
from app.modules.organizations.schemas import OrganizationRead, OrganizationUpdate
from app.modules.organizations.service import OrganizationService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/organization", tags=["organization"])

Manager = Annotated[User, Depends(require_permissions(Perm.ORGANIZATION_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_organization_service(session: DbSession) -> OrganizationService:
    return OrganizationService(session)


Service = Annotated[OrganizationService, Depends(get_organization_service)]


@router.get("", response_model=OrganizationRead, summary="Datos del taller")
def get_organization(actor: CurrentUser, service: Service) -> Organization:
    return service.get(actor)


@router.patch("", response_model=OrganizationRead, summary="Editar los datos del taller")
def update_organization(
    body: OrganizationUpdate, actor: Manager, service: Service, context: Context
) -> Organization:
    return service.update(actor, body, context)
