from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import CurrentUser, DbSession, require_permissions
from app.modules.privacy.models import PrivacyPolicy
from app.modules.privacy.schemas import (
    CurrentPrivacyPolicy,
    PrivacyPolicyDraft,
    PrivacyPolicyPublish,
    PrivacyPolicyRead,
    PrivacyPolicyVersion,
)
from app.modules.privacy.service import PrivacyService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/privacy-policy", tags=["privacy"])

Manager = Annotated[User, Depends(require_permissions(Perm.ORGANIZATION_MANAGE))]
Reader = Annotated[User, Depends(require_permissions(Perm.CUSTOMERS_READ))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_privacy_service(session: DbSession) -> PrivacyService:
    return PrivacyService(session)


Service = Annotated[PrivacyService, Depends(get_privacy_service)]


@router.get(
    "",
    response_model=CurrentPrivacyPolicy,
    summary="Política vigente y textos de autorización para la recepción",
)
def get_current_policy(actor: CurrentUser, service: Service) -> CurrentPrivacyPolicy:
    return service.current_with_authorizations(actor)


@router.get(
    "/draft",
    response_model=PrivacyPolicyDraft,
    summary="Plantilla de la política con los datos del taller",
)
def get_policy_draft(actor: Manager, service: Service) -> PrivacyPolicyDraft:
    return service.draft(actor)


@router.get("/versions", response_model=list[PrivacyPolicyVersion], summary="Versiones publicadas")
def list_policy_versions(actor: Reader, service: Service) -> list[PrivacyPolicy]:
    return service.versions(actor.organization_id)


@router.get("/versions/{version}", response_model=PrivacyPolicyRead, summary="Texto de una versión")
def get_policy_version(version: int, actor: Reader, service: Service) -> PrivacyPolicy:
    return service.get_version(actor.organization_id, version)


@router.post(
    "",
    response_model=PrivacyPolicyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar una nueva versión de la política",
)
def publish_policy(
    body: PrivacyPolicyPublish, actor: Manager, service: Service, context: Context
) -> PrivacyPolicy:
    return service.publish(actor, body.content, context)
